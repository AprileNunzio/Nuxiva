mod code;
mod cognition;
mod dispatch;
mod projects;

use std::collections::BTreeMap;
use std::time::{SystemTime, UNIX_EPOCH};

use agency_domain::{ProjectId, TaskId, TaskStatus};
use agency_ledger::{LedgerKey, LedgerStore};
use agency_scheduler::capacity;
use agency_scheduler::{HostProfile, ModelProfile, Settings};
use serde_json::{Value, json};

use crate::config::Config;
use crate::error::AgencyError;
use crate::files;
use crate::foresight::{Foresight, Outcome};
use crate::protocol::Request;
use crate::state::{EngineSettings, ProjectState};
use crate::workspace;

pub use dispatch::TaskUpdateArgs;

const SETTINGS_FILE: &str = "settings.json";

#[derive(Debug)]
pub struct Engine {
    pub(crate) config: Config,
    pub(crate) host: HostProfile,
    pub(crate) settings: EngineSettings,
    pub(crate) projects: BTreeMap<ProjectId, ProjectState>,
    pub(crate) ledger: LedgerStore,
    pub(crate) foresight: Foresight,
}

pub(crate) fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| u64::try_from(d.as_millis()).unwrap_or(u64::MAX))
}

pub(crate) fn project_id(raw: &str) -> Result<ProjectId, AgencyError> {
    Ok(ProjectId::new(raw)?)
}

impl Engine {
    pub fn open(config: Config, host: HostProfile) -> Result<Self, AgencyError> {
        files::private_dir(&config.state_dir)?;
        files::private_dir(&config.projects_dir())?;
        let key = LedgerKey::from_bytes(files::load_key(&config.path("ledger.key"))?);
        let ledger = LedgerStore::open(&config.path("ledger.jsonl"), key)?;
        let settings = match files::read(&config.path(SETTINGS_FILE))? {
            Some(bytes) => serde_json::from_slice::<EngineSettings>(&bytes)?,
            None => EngineSettings::default(),
        };
        settings.scheduler.validate()?;
        let foresight = Foresight::open(config.path("foresight"))?;
        let mut engine = Self {
            config,
            host,
            settings,
            projects: BTreeMap::new(),
            ledger,
            foresight,
        };
        engine.load_projects()?;
        Ok(engine)
    }

    fn load_projects(&mut self) -> Result<(), AgencyError> {
        let mut recovered = Vec::new();
        for entry in std::fs::read_dir(self.config.projects_dir())? {
            let path = entry?.path();
            if path.extension().and_then(|e| e.to_str()) != Some("json") {
                continue;
            }
            let Some(bytes) = files::read(&path)? else {
                continue;
            };
            let mut state = ProjectState::decode(&bytes)?;
            let running: Vec<TaskId> = state
                .graph
                .tasks()
                .filter(|t| t.status() == TaskStatus::Running)
                .map(|t| t.id().clone())
                .collect();
            for id in &running {
                state.graph.update(id, agency_domain::Task::interrupt)?;
            }
            if !running.is_empty() {
                recovered.push(state.project.id().clone());
            }
            self.projects.insert(state.project.id().clone(), state);
        }
        for id in recovered {
            self.persist(&id)?;
            self.event("engine.recovered", json!({ "project": id }))?;
        }
        Ok(())
    }

    pub(crate) fn event(&mut self, kind: &str, payload: Value) -> Result<(), AgencyError> {
        self.ledger.append(kind, payload, now_ms())?;
        Ok(())
    }

    pub(crate) fn persist(&self, id: &ProjectId) -> Result<(), AgencyError> {
        let state = self.projects.get(id).ok_or(AgencyError::NotFound)?;
        let path = self.config.projects_dir().join(format!("{id}.json"));
        files::write_atomic(&path, &state.encode()?)
    }

    pub(crate) fn commit_state(
        &mut self,
        id: &ProjectId,
        state: ProjectState,
    ) -> Result<(), AgencyError> {
        let path = self.config.projects_dir().join(format!("{id}.json"));
        files::write_atomic(&path, &state.encode()?)?;
        self.projects.insert(id.clone(), state);
        Ok(())
    }

    pub(crate) fn state_mut(&mut self, id: &ProjectId) -> Result<&mut ProjectState, AgencyError> {
        self.projects.get_mut(id).ok_or(AgencyError::NotFound)
    }

    pub(crate) fn project_root(&self, id: &ProjectId) -> Result<std::path::PathBuf, AgencyError> {
        let state = self.projects.get(id).ok_or(AgencyError::NotFound)?;
        workspace::locate(&self.config.workspace_root, state.project.workspace())
    }

    fn capacity_value(&self) -> Value {
        json!({
            "host": self.host,
            "capacity": capacity(&self.host, &self.settings.model, &self.settings.scheduler),
            "running": self.running_total(),
        })
    }

    fn running_total(&self) -> usize {
        self.projects
            .values()
            .map(|s| {
                s.graph
                    .tasks()
                    .filter(|t| t.status() == TaskStatus::Running)
                    .count()
            })
            .sum()
    }

    #[allow(clippy::too_many_lines)]
    pub fn handle(&mut self, request: Request) -> Result<Value, AgencyError> {
        match request {
            Request::Ping {} => {
                Ok(json!({ "pong": true, "ledger_head": self.ledger.chain().head() }))
            }
            Request::Capacity {} => Ok(self.capacity_value()),
            Request::SettingsGet {} => Ok(json!(self.settings)),
            Request::SettingsSet { scheduler, model } => self.set_settings(scheduler, model),
            Request::ProjectCreate {
                id,
                title,
                goal,
                workspace,
                budget,
            } => self.create(&id, &title, &goal, &workspace, budget),
            Request::ProjectList {} => Ok(json!(
                self.projects
                    .values()
                    .map(ProjectState::summary)
                    .collect::<Vec<_>>()
            )),
            Request::ProjectGet { id } => {
                let id = project_id(&id)?;
                Ok(self
                    .projects
                    .get(&id)
                    .ok_or(AgencyError::NotFound)?
                    .detail())
            }
            Request::ProjectPlan {
                id,
                tasks,
                decisions,
                questions,
            } => self.plan_project(&id, &tasks, &decisions, &questions),
            Request::ProjectAnswer {
                id,
                question,
                option,
                answer,
            } => self.answer_project_question(&id, &question, option.as_deref(), answer.as_deref()),
            Request::ProjectControl { id, action } => self.control(&project_id(&id)?, action),
            Request::ProjectRename { id, title } => self.rename(&project_id(&id)?, &title),
            Request::ProjectArchive { id, archived } => self.archive(&project_id(&id)?, archived),
            Request::ProjectAssign { id, agents } => self.assign(&project_id(&id)?, &agents),
            Request::ProjectDelete { id, confirm } => self.delete(&project_id(&id)?, &confirm),
            Request::AssignmentRevoke { project, task } => {
                let id = project_id(&project)?;
                let task = TaskId::new(&task)?;
                self.revoke_assignment(&id, &task)
            }
            Request::TaskUpdate {
                project,
                task,
                action,
                feedback,
                checkpoint,
                worker,
                generation,
                tokens,
                seconds,
                proofs,
            } => {
                let id = project_id(&project)?;
                let task = TaskId::new(&task)?;
                self.update_task(
                    &id,
                    &task,
                    TaskUpdateArgs {
                        action,
                        feedback: feedback.as_deref(),
                        checkpoint: checkpoint.as_deref(),
                        worker: worker.as_deref(),
                        generation,
                        tokens,
                        seconds,
                        proofs: &proofs,
                    },
                )
            }
            Request::Dispatch {} => self.dispatch(),
            Request::CodeFiles {
                project,
                worker,
                generation,
            } => self.code_files(&project, worker.as_deref(), generation),
            Request::CodeSearch {
                project,
                query,
                limit,
                worker,
                generation,
            } => self.code_search(&project, &query, limit, worker.as_deref(), generation),
            Request::CodeOutline {
                project,
                path,
                worker,
                generation,
            } => self.code_outline(&project, &path, worker.as_deref(), generation),
            Request::CodeSymbols {
                project,
                query,
                limit,
                worker,
                generation,
            } => self.code_symbols(&project, &query, limit, worker.as_deref(), generation),
            Request::CodeViewRange {
                project,
                path,
                start_line,
                end_line,
                worker,
                generation,
            } => self.code_view_range(
                &project,
                &path,
                start_line,
                end_line,
                worker.as_deref(),
                generation,
            ),
            Request::CodePatch {
                project,
                path,
                chunks,
                worker,
                generation,
            } => self.code_patch(&project, &path, &chunks, worker.as_deref(), generation),
            Request::ThoughtEvaluate { candidates } => Self::thought_evaluate(&candidates),
            Request::SocraticInterrogate {
                goal,
                known_decisions,
            } => Self::socratic_interrogate(&goal, &known_decisions),
            Request::SpecialistRecruit { goal, architecture } => {
                Self::specialist_recruit(&goal, &architecture)
            }
            Request::TaskExpand {
                project,
                task,
                subtasks,
            } => self.task_expand(&project, &task, &subtasks),
            Request::ForgeInspect { name, code } => Ok(Self::forge_inspect(&name, &code)),
            request @ (Request::ForesightList {}
            | Request::ForesightReport { .. }
            | Request::ForesightAgent { .. }
            | Request::ForesightEnsemble { .. }) => self.foresight_read(request),
            other => self.foresight_change(other),
        }
    }

    fn set_settings(
        &mut self,
        scheduler: Settings,
        model: ModelProfile,
    ) -> Result<Value, AgencyError> {
        let next = EngineSettings {
            scheduler: scheduler.validate()?,
            model,
        };
        files::write_atomic(
            &self.config.path(SETTINGS_FILE),
            &serde_json::to_vec(&next)?,
        )?;
        self.settings = next;
        self.event("settings.updated", json!(next))?;
        Ok(self.capacity_value())
    }

    fn foresight_read(&mut self, request: Request) -> Result<Value, AgencyError> {
        match request {
            Request::ForesightList {} => Ok(self.foresight.list()),
            Request::ForesightReport { id } => self.foresight.report(&project_id(&id)?),
            Request::ForesightAgent { id, agent } => {
                self.foresight.agent(&project_id(&id)?, &agent)
            }
            Request::ForesightEnsemble { id, runs } => {
                let id = project_id(&id)?;
                let scenario = self.foresight.scenario(&id)?;
                let result = agency_foresight::ensemble(&scenario, runs)?;
                self.foresight_record(&id, result)
            }
            _ => Err(AgencyError::BadRequest("unsupported operation".to_owned())),
        }
    }

    fn settle_outcome(&mut self, outcome: Outcome) -> Result<Value, AgencyError> {
        let (data, event) = outcome;
        if let Some((kind, payload)) = event {
            self.event(kind, payload)?;
        }
        Ok(data)
    }

    fn foresight_change(&mut self, request: Request) -> Result<Value, AgencyError> {
        let now = now_ms();
        let outcome = match request {
            Request::ForesightCreate { id, scenario } => {
                self.foresight.create(&project_id(&id)?, scenario, now)?
            }
            Request::ForesightRun { id, rounds } => {
                self.foresight.run(&project_id(&id)?, rounds, now)?
            }
            Request::ForesightInject { id, event } => {
                self.foresight.inject(&project_id(&id)?, event, now)?
            }
            Request::ForesightDelete { id } => self.foresight.delete(&project_id(&id)?)?,
            _ => return Err(AgencyError::BadRequest("unsupported operation".to_owned())),
        };
        self.settle_outcome(outcome)
    }

    pub fn foresight_scenario(
        &self,
        id: &str,
    ) -> Result<(ProjectId, agency_foresight::ScenarioSpec), AgencyError> {
        let id = project_id(id)?;
        let scenario = self.foresight.scenario(&id)?;
        Ok((id, scenario))
    }

    pub fn foresight_record(
        &mut self,
        id: &ProjectId,
        result: agency_foresight::Ensemble,
    ) -> Result<Value, AgencyError> {
        let outcome = self.foresight.record(id, result, now_ms())?;
        self.settle_outcome(outcome)
    }
}
