use std::collections::BTreeMap;

use agency_domain::{Budget, Project, ProjectId, ProjectStatus, TaskId, TaskSpec, WorkspacePath};
use agency_planner::TaskGraph;
use serde_json::{Value, json};

use crate::engine::{Engine, now_ms, project_id};
use crate::error::AgencyError;
use crate::protocol::{BudgetInput, Control};
use crate::state::ProjectState;
use crate::workspace;

const MAX_PROJECTS: usize = 256;

impl Engine {
    pub(crate) fn create(
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
            leases: BTreeMap::new(),
        };
        let detail = state.detail();
        self.projects.insert(id.clone(), state);
        self.persist(&id)?;
        self.event("project.created", json!({ "project": id }))?;
        Ok(detail)
    }

    pub(crate) fn control(
        &mut self,
        id: &ProjectId,
        action: Control,
    ) -> Result<Value, AgencyError> {
        let mut state = self.state_mut(id)?.clone();
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
                if state.project.status() == ProjectStatus::Cancelled {
                    return Ok(state.detail());
                }
                state.project.transition(ProjectStatus::Cancelled)?;
                let open: Vec<TaskId> = state
                    .graph
                    .tasks()
                    .filter(|t| !t.status().is_terminal())
                    .map(|t| t.id().clone())
                    .collect();
                for task in &open {
                    state.graph.update(task, agency_domain::Task::cancel)?;
                }
            }
        }
        let status = state.project.status();
        let detail = state.detail();
        self.commit_state(id, state)?;
        self.event("project.status", json!({ "project": id, "status": status }))?;
        Ok(detail)
    }

    pub(crate) fn plan_project(
        &mut self,
        id: &str,
        tasks: &[TaskSpec],
        decisions: &[crate::protocol::DecisionSpec],
        questions: &[crate::protocol::QuestionSpec],
    ) -> Result<Value, AgencyError> {
        let id = project_id(id)?;
        let state = self.state_mut(&id)?;
        if state.project.status().is_terminal() {
            return Err(AgencyError::BadRequest("project is closed".to_owned()));
        }
        for d in decisions {
            let status = match d.status.as_deref() {
                Some("accepted") => agency_domain::DecisionStatus::Accepted,
                Some("rejected") => agency_domain::DecisionStatus::Rejected,
                _ => agency_domain::DecisionStatus::Proposed,
            };
            let decision = agency_domain::Decision::new(&d.id, &d.title, &d.rationale, status)?;
            state.project.add_decision(decision);
        }
        for q in questions {
            let options = q
                .options
                .iter()
                .map(|opt| {
                    agency_domain::QuestionOption::new(
                        &opt.id,
                        &opt.label,
                        opt.description.as_deref(),
                    )
                })
                .collect::<Result<Vec<_>, _>>()?;
            let question = agency_domain::Question::new(&q.id, &q.prompt, options)?;
            state.project.add_question(question);
        }
        state.graph.extend(tasks)?;
        if state.project.has_unanswered_questions() {
            if state.project.status() == ProjectStatus::Planning {
                state.project.transition(ProjectStatus::WaitingUser)?;
            }
        } else if state.project.status() == ProjectStatus::Planning && !state.graph.is_empty() {
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

    pub(crate) fn answer_project_question(
        &mut self,
        id: &str,
        question: &str,
        option: Option<&str>,
        answer: Option<&str>,
    ) -> Result<Value, AgencyError> {
        let id = project_id(id)?;
        let state = self.state_mut(&id)?;
        state.project.answer_question(question, option, answer)?;
        if !state.project.has_unanswered_questions()
            && state.project.status() == ProjectStatus::WaitingUser
        {
            let next = if state.graph.is_empty() {
                ProjectStatus::Planning
            } else {
                ProjectStatus::Running
            };
            state.project.transition(next)?;
        }
        let detail = state.detail();
        self.persist(&id)?;
        self.event(
            "project.question_answered",
            json!({ "project": id, "question": question }),
        )?;
        Ok(detail)
    }
}

pub(crate) fn settle(state: &mut ProjectState) -> Result<(), AgencyError> {
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
