use std::collections::BTreeMap;
use std::time::{SystemTime, UNIX_EPOCH};

use agency_domain::{Budget, Project, ProjectId, ProjectStatus, TaskId, TaskStatus, WorkspacePath};
use agency_ledger::{LedgerKey, LedgerStore};
use agency_planner::TaskGraph;
use agency_scheduler::{HostProfile, capacity};
use serde_json::{Value, json};

use crate::config::Config;
use crate::error::AgencyError;
use crate::files;
use crate::protocol::{BudgetInput, Control, Request, TaskAction};
use crate::state::{EngineSettings, ProjectState};
use crate::workspace;

const MAX_PROJECTS: usize = 256;
const SETTINGS_FILE: &str = "settings.json";
const MAX_QUERY: usize = 200;
const MAX_HITS: usize = 200;

#[derive(Debug)]
pub struct Engine {
    config: Config,
    host: HostProfile,
    settings: EngineSettings,
    projects: BTreeMap<ProjectId, ProjectState>,
    ledger: LedgerStore,
}

fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| u64::try_from(d.as_millis()).unwrap_or(u64::MAX))
}

fn project_id(raw: &str) -> Result<ProjectId, AgencyError> {
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
        let mut engine = Self {
            config,
            host,
            settings,
            projects: BTreeMap::new(),
            ledger,
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

    fn event(&mut self, kind: &str, payload: Value) -> Result<(), AgencyError> {
        self.ledger.append(kind, payload, now_ms())?;
        Ok(())
    }

    fn persist(&self, id: &ProjectId) -> Result<(), AgencyError> {
        let state = self.projects.get(id).ok_or(AgencyError::NotFound)?;
        let path = self.config.projects_dir().join(format!("{id}.json"));
        files::write_atomic(&path, &state.encode()?)
    }

    fn state_mut(&mut self, id: &ProjectId) -> Result<&mut ProjectState, AgencyError> {
        self.projects.get_mut(id).ok_or(AgencyError::NotFound)
    }

    fn project_root(&self, id: &ProjectId) -> Result<std::path::PathBuf, AgencyError> {
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

    pub fn handle(&mut self, request: Request) -> Result<Value, AgencyError> {
        match request {
            Request::Ping {} => {
                Ok(json!({ "pong": true, "ledger_head": self.ledger.chain().head() }))
            }
            Request::Capacity {} => Ok(self.capacity_value()),
            Request::SettingsGet {} => Ok(json!(self.settings)),
            Request::SettingsSet { scheduler, model } => {
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
            Request::ProjectPlan { id, tasks } => {
                let id = project_id(&id)?;
                let state = self.state_mut(&id)?;
                if state.project.status().is_terminal() {
                    return Err(AgencyError::BadRequest("project is closed".to_owned()));
                }
                state.graph.extend(&tasks)?;
                if state.project.status() == ProjectStatus::Planning && !state.graph.is_empty() {
                    state.project.transition(ProjectStatus::Running)?;
                }
                let detail = state.detail();
                self.persist(&id)?;
                self.event(
                    "project.planned",
                    json!({ "project": id, "added": tasks.len() }),
                )?;
                Ok(detail)
            }
            Request::ProjectControl { id, action } => self.control(&project_id(&id)?, action),
            Request::TaskUpdate {
                project,
                task,
                action,
                feedback,
                tokens,
                seconds,
            } => {
                let id = project_id(&project)?;
                let task = TaskId::new(&task)?;
                self.update_task(&id, &task, action, feedback.as_deref(), tokens, seconds)
            }
            Request::Dispatch {} => self.dispatch(),
            Request::CodeFiles { project } => {
                let root = self.project_root(&project_id(&project)?)?;
                let files = agency_codeindex::scan(&root, agency_codeindex::Limits::default())
                    .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
                Ok(json!({ "files": files }))
            }
            Request::CodeSearch {
                project,
                query,
                limit,
            } => {
                if query.chars().count() > MAX_QUERY {
                    return Err(AgencyError::BadRequest("query too long".to_owned()));
                }
                let root = self.project_root(&project_id(&project)?)?;
                let limit = limit.unwrap_or(40).clamp(1, MAX_HITS);
                let hits = agency_codeindex::search(&root, &query, limit)
                    .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
                Ok(json!({ "hits": hits }))
            }
        }
    }

    fn create(
        &mut self,
        id: &str,
        title: &str,
        goal: &str,
        workspace: &str,
        budget: BudgetInput,
    ) -> Result<Value, AgencyError> {
        let id = project_id(id)?;
        if self.projects.contains_key(&id) {
            return Err(AgencyError::Exists);
        }
        if self.projects.len() >= MAX_PROJECTS {
            return Err(AgencyError::TooMany);
        }
        let workspace = WorkspacePath::new(workspace)?;
        let budget = Budget::new(budget.tokens, budget.seconds, budget.parallel)?;
        let project = Project::new(id.clone(), title, goal, workspace, budget, now_ms())?;
        workspace::prepare(&self.config.workspace_root, project.workspace())?;
        let state = ProjectState {
            project,
            graph: TaskGraph::new(),
        };
        let detail = state.detail();
        self.projects.insert(id.clone(), state);
        self.persist(&id)?;
        self.event("project.created", json!({ "project": id }))?;
        Ok(detail)
    }

    fn control(&mut self, id: &ProjectId, action: Control) -> Result<Value, AgencyError> {
        let state = self.state_mut(id)?;
        match action {
            Control::Pause => state.project.transition(ProjectStatus::Paused)?,
            Control::Resume => {
                let next = if state.graph.is_empty() {
                    ProjectStatus::Planning
                } else {
                    ProjectStatus::Running
                };
                state.project.transition(next)?;
            }
            Control::Cancel => {
                let open: Vec<TaskId> = state
                    .graph
                    .tasks()
                    .filter(|t| !t.status().is_terminal())
                    .map(|t| t.id().clone())
                    .collect();
                for task in &open {
                    state.graph.update(task, agency_domain::Task::cancel)?;
                }
                state.project.transition(ProjectStatus::Cancelled)?;
            }
        }
        let status = state.project.status();
        let detail = state.detail();
        self.persist(id)?;
        self.event("project.status", json!({ "project": id, "status": status }))?;
        Ok(detail)
    }

    fn update_task(
        &mut self,
        id: &ProjectId,
        task: &TaskId,
        action: TaskAction,
        feedback: Option<&str>,
        tokens: u64,
        seconds: u64,
    ) -> Result<Value, AgencyError> {
        let state = self.state_mut(id)?;
        state
            .graph
            .update(task, |t| t.record_usage(tokens, seconds))?;
        state.project.record_usage(tokens, seconds)?;
        let outcome = state.graph.update(task, |t| match action {
            TaskAction::Submit => t.submit(),
            TaskAction::Approve => t.approve(),
            TaskAction::Rework => t.rework(feedback.unwrap_or("rework requested")),
            TaskAction::Fail => t.fail(),
            TaskAction::Cancel => t.cancel(),
            TaskAction::Interrupt => t.interrupt(),
        });
        let exhausted = matches!(
            outcome,
            Err(agency_planner::PlanError::Domain(
                agency_domain::DomainError::AttemptsExhausted
            ))
        );
        if !exhausted {
            outcome?;
        }
        let before = state.project.status();
        settle(state)?;
        let after = state.project.status();
        let detail = state.detail();
        self.persist(id)?;
        self.event(
            action.event(),
            json!({ "project": id, "task": task, "tokens": tokens, "seconds": seconds }),
        )?;
        if before != after {
            self.event("project.status", json!({ "project": id, "status": after }))?;
        }
        Ok(detail)
    }

    fn dispatch(&mut self) -> Result<Value, AgencyError> {
        let limit = usize::from(
            capacity(&self.host, &self.settings.model, &self.settings.scheduler).parallel_agents,
        );
        let mut room = limit.saturating_sub(self.running_total());
        let mut started = Vec::new();
        let ids: Vec<ProjectId> = self.projects.keys().cloned().collect();
        for id in ids {
            if room == 0 {
                break;
            }
            let state = self.state_mut(&id)?;
            if state.project.status() != ProjectStatus::Running || !state.project.within_budget() {
                continue;
            }
            let per_project = usize::from(state.project.budget().max_parallel());
            let picks: Vec<TaskId> = state
                .graph
                .dispatchable(per_project)
                .into_iter()
                .take(room)
                .cloned()
                .collect();
            for task in &picks {
                state.graph.update(task, agency_domain::Task::start)?;
                started.push(json!({ "project": id, "task": task }));
            }
            room = room.saturating_sub(picks.len());
            if !picks.is_empty() {
                self.persist(&id)?;
                self.event("task.started", json!({ "project": id, "tasks": picks }))?;
            }
        }
        Ok(json!({ "started": started, "capacity": limit }))
    }
}

fn settle(state: &mut ProjectState) -> Result<(), AgencyError> {
    if state.project.status() != ProjectStatus::Running {
        return Ok(());
    }
    if !state.project.within_budget() {
        state.project.transition(ProjectStatus::Paused)?;
        return Ok(());
    }
    if state.graph.is_empty() || !state.graph.is_finished() {
        return Ok(());
    }
    let progress = state.graph.progress();
    let next = if progress.failed == 0 && progress.blocked == 0 {
        ProjectStatus::Completed
    } else {
        ProjectStatus::WaitingUser
    };
    state.project.transition(next)?;
    Ok(())
}
