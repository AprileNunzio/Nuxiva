use std::collections::BTreeSet;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ActionKind {
    ReadFile,
    ViewOutline,
    SearchCode,
    SurgicalPatch,
    WriteFile,
    RunCheck,
    ForgeTool,
}

impl ActionKind {
    #[must_use]
    pub fn is_read_only(self) -> bool {
        matches!(self, Self::ReadFile | Self::ViewOutline | Self::SearchCode)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ActionItem {
    pub id: String,
    pub kind: ActionKind,
    pub target_path: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionWave {
    pub wave_index: usize,
    pub parallel_ids: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BatchPlan {
    pub waves: Vec<ExecutionWave>,
    pub total_actions: usize,
}

#[must_use]
pub fn plan_parallel_batch(actions: &[ActionItem]) -> BatchPlan {
    let mut waves: Vec<ExecutionWave> = Vec::new();
    let mut read_ids = Vec::new();
    let mut mutating: Vec<&ActionItem> = Vec::new();

    for item in actions {
        if item.kind.is_read_only() {
            read_ids.push(item.id.clone());
        } else {
            mutating.push(item);
        }
    }

    if !read_ids.is_empty() {
        waves.push(ExecutionWave {
            wave_index: waves.len(),
            parallel_ids: read_ids,
        });
    }

    let mut remaining = mutating;
    while !remaining.is_empty() {
        let mut wave_ids = Vec::new();
        let mut locked_paths = BTreeSet::new();
        let mut has_global_barrier = false;
        let mut deferred = Vec::new();

        for item in remaining {
            if item.kind == ActionKind::RunCheck {
                if wave_ids.is_empty() {
                    wave_ids.push(item.id.clone());
                    has_global_barrier = true;
                } else {
                    deferred.push(item);
                }
                continue;
            }
            if has_global_barrier {
                deferred.push(item);
                continue;
            }
            if let Some(path) = &item.target_path {
                if locked_paths.contains(path) {
                    deferred.push(item);
                } else {
                    locked_paths.insert(path.clone());
                    wave_ids.push(item.id.clone());
                }
            } else {
                wave_ids.push(item.id.clone());
            }
        }

        waves.push(ExecutionWave {
            wave_index: waves.len(),
            parallel_ids: wave_ids,
        });
        remaining = deferred;
    }

    BatchPlan {
        waves,
        total_actions: actions.len(),
    }
}
