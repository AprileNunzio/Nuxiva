use agency_domain::{TaskId, TaskSpec, TaskStatus};
use agency_planner::TaskGraph;
use serde::{Deserialize, Serialize};

use crate::error::ThoughtError;

pub const MAX_SUBTASKS_PER_EXPANSION: usize = 16;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SubTaskBlueprint {
    pub suffix: String,
    pub title: String,
    pub role: String,
    #[serde(default)]
    pub depends_on_suffixes: Vec<String>,
    #[serde(default)]
    pub acceptance: Vec<String>,
    pub estimate_seconds: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExpansionResult {
    pub parent_task: String,
    pub added_tasks: Vec<String>,
    pub critical_path_seconds: u64,
}

pub fn expand_task_node(
    graph: &mut TaskGraph,
    parent_id_str: &str,
    subtasks: &[SubTaskBlueprint],
) -> Result<ExpansionResult, ThoughtError> {
    if subtasks.is_empty() {
        return Err(ThoughtError::Decomposition(
            "subtasks list cannot be empty".to_owned(),
        ));
    }
    if subtasks.len() > MAX_SUBTASKS_PER_EXPANSION {
        return Err(ThoughtError::Decomposition(format!(
            "cannot expand into more than {MAX_SUBTASKS_PER_EXPANSION} subtasks at once"
        )));
    }

    let parent_id = TaskId::new(parent_id_str)?;
    let parent = graph
        .get(&parent_id)
        .ok_or_else(|| ThoughtError::Decomposition(format!("parent task '{parent_id}' not found")))?
        .clone();

    if parent.status().is_terminal() {
        return Err(ThoughtError::Decomposition(format!(
            "cannot expand terminal task '{parent_id}'"
        )));
    }
    if parent.status() == TaskStatus::Running {
        return Err(ThoughtError::Decomposition(format!(
            "interrupt running task '{parent_id}' before expanding it"
        )));
    }

    let parent_deps: Vec<String> = parent
        .depends_on()
        .iter()
        .map(|d| d.as_str().to_owned())
        .collect();

    let count_u64 = u64::try_from(subtasks.len()).unwrap_or(1).max(1);
    let split_tokens = parent.budget().map(|b| {
        b.max_tokens()
            .checked_div(count_u64)
            .unwrap_or(1_000)
            .max(500)
    });
    let split_seconds = parent.budget().map(|b| {
        b.max_seconds()
            .checked_div(count_u64)
            .unwrap_or(120)
            .max(60)
    });

    let mut specs = Vec::with_capacity(subtasks.len());
    let mut added_ids = Vec::with_capacity(subtasks.len());

    for sub in subtasks {
        let full_id = format!("{}_{}", parent_id.as_str(), sub.suffix.trim());
        TaskId::new(&full_id)?;
        added_ids.push(full_id);
    }

    for (idx, sub) in subtasks.iter().enumerate() {
        let Some(full_id) = added_ids.get(idx).cloned() else {
            return Err(ThoughtError::Decomposition("missing subtask id".to_owned()));
        };
        let mut deps = if sub.depends_on_suffixes.is_empty() {
            parent_deps.clone()
        } else {
            let mut local_deps = Vec::new();
            for dep_suffix in &sub.depends_on_suffixes {
                let candidate = format!("{}_{}", parent_id.as_str(), dep_suffix.trim());
                if !added_ids.contains(&candidate) {
                    return Err(ThoughtError::Decomposition(format!(
                        "unknown subtask dependency suffix '{dep_suffix}'"
                    )));
                }
                local_deps.push(candidate);
            }
            local_deps
        };
        deps.sort();
        deps.dedup();

        let role = if sub.role.trim().is_empty() {
            parent.role().as_str().to_owned()
        } else {
            sub.role.trim().to_owned()
        };

        specs.push(TaskSpec {
            id: full_id,
            title: sub.title.clone(),
            role,
            depends_on: deps,
            acceptance: sub.acceptance.clone(),
            estimate_seconds: sub.estimate_seconds.max(30),
            max_attempts: parent.max_attempts(),
            budget_tokens: split_tokens,
            budget_seconds: split_seconds,
        });
    }

    graph.extend(&specs)?;

    Ok(ExpansionResult {
        parent_task: parent_id.as_str().to_owned(),
        added_tasks: added_ids,
        critical_path_seconds: graph.critical_path_seconds(),
    })
}
