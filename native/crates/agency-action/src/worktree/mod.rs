use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::ActionError;
use crate::patch::{ReplacementChunk, apply_surgical_patches};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StagedEdit {
    pub worker: String,
    pub path: String,
    pub chunks: Vec<ReplacementChunk>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MergeReport {
    pub merged_files: BTreeMap<String, String>,
    pub applied_edits: usize,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkspaceCoordinator {
    base_files: BTreeMap<String, String>,
    staged: Vec<StagedEdit>,
}

impl WorkspaceCoordinator {
    #[must_use]
    pub fn new(base_files: BTreeMap<String, String>) -> Self {
        Self {
            base_files,
            staged: Vec::new(),
        }
    }

    pub fn stage_edit(&mut self, edit: StagedEdit) -> Result<(), ActionError> {
        let trimmed = edit.path.trim();
        if trimmed.is_empty()
            || trimmed.contains("..")
            || trimmed.starts_with('/')
            || trimmed.starts_with('\\')
        {
            return Err(ActionError::InvalidPath(edit.path));
        }
        if edit.chunks.is_empty() {
            return Err(ActionError::EmptyChunks);
        }
        self.staged.push(edit);
        Ok(())
    }

    pub fn merge_all(&self) -> Result<MergeReport, ActionError> {
        let mut by_path: BTreeMap<String, Vec<&StagedEdit>> = BTreeMap::new();
        for edit in &self.staged {
            by_path.entry(edit.path.clone()).or_default().push(edit);
        }

        let mut merged_files = self.base_files.clone();
        let mut applied_edits: usize = 0;

        for (path, edits) in by_path {
            let base = merged_files.get(&path).cloned().unwrap_or_default();
            let mut combined_chunks: Vec<(String, ReplacementChunk)> = Vec::new();
            for edit in edits {
                for chunk in &edit.chunks {
                    combined_chunks.push((edit.worker.clone(), chunk.clone()));
                }
            }
            combined_chunks.sort_by_key(|(_, c)| (c.start_line, c.end_line));

            for pair in combined_chunks.windows(2) {
                if let [(w1, c1), (w2, c2)] = pair {
                    if c1.end_line >= c2.start_line {
                        return Err(ActionError::MergeConflict {
                            path,
                            first_worker: w1.clone(),
                            second_worker: w2.clone(),
                        });
                    }
                }
            }

            let ordered_chunks: Vec<ReplacementChunk> =
                combined_chunks.into_iter().map(|(_, c)| c).collect();
            let outcome = apply_surgical_patches(&base, &ordered_chunks)?;
            applied_edits = applied_edits.saturating_add(outcome.replacements_applied);
            merged_files.insert(path, outcome.updated_content);
        }

        Ok(MergeReport {
            merged_files,
            applied_edits,
        })
    }
}
