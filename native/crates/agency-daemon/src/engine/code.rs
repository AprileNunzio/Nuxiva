use std::fs;
use std::path::{Path, PathBuf};

use agency_action::{ReplacementChunk, apply_surgical_patches, view_line_range};
use agency_domain::ProjectId;
use serde_json::{Value, json};

use crate::engine::Engine;
use crate::error::AgencyError;
use crate::files;

const MAX_QUERY: usize = 200;
const MAX_HITS: usize = 200;
const MAX_FILE_BYTES: u64 = 1024 * 1024;

fn safe_relative_file(root: &Path, relative_path: &str) -> Result<PathBuf, AgencyError> {
    let trimmed = relative_path.trim();
    if trimmed.is_empty()
        || trimmed.contains("..")
        || trimmed.starts_with('/')
        || trimmed.starts_with('\\')
    {
        return Err(AgencyError::Escape);
    }
    for part in trimmed.split('/') {
        if part.is_empty() || part == "." || part == ".." || part.starts_with('.') {
            return Err(AgencyError::Escape);
        }
    }
    let full = root.join(trimmed);
    if let Ok(meta) = fs::symlink_metadata(&full) {
        if meta.file_type().is_symlink() || !meta.is_file() {
            return Err(AgencyError::Escape);
        }
        if meta.len() > MAX_FILE_BYTES {
            return Err(AgencyError::BadRequest(
                "file exceeds size limit".to_owned(),
            ));
        }
    }
    Ok(full)
}

impl Engine {
    pub(crate) fn code_files(
        &self,
        project: &str,
        worker: Option<&str>,
        generation: Option<u64>,
    ) -> Result<Value, AgencyError> {
        let id = ProjectId::new(project)?;
        self.validate_worker(&id, worker, generation)?;
        let root = self.project_root(&id)?;
        let files = agency_codeindex::scan(&root, agency_codeindex::Limits::default())
            .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
        Ok(json!({ "files": files }))
    }

    pub(crate) fn code_search(
        &self,
        project: &str,
        query: &str,
        limit: Option<usize>,
        worker: Option<&str>,
        generation: Option<u64>,
    ) -> Result<Value, AgencyError> {
        let id = ProjectId::new(project)?;
        self.validate_worker(&id, worker, generation)?;
        if query.chars().count() > MAX_QUERY {
            return Err(AgencyError::BadRequest("query too long".to_owned()));
        }
        let root = self.project_root(&id)?;
        let limit = limit.unwrap_or(40).clamp(1, MAX_HITS);
        let hits = agency_codeindex::search(&root, query, limit)
            .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
        Ok(json!({ "hits": hits }))
    }

    pub(crate) fn code_outline(
        &self,
        project: &str,
        path: &str,
        worker: Option<&str>,
        generation: Option<u64>,
    ) -> Result<Value, AgencyError> {
        let id = ProjectId::new(project)?;
        self.validate_worker(&id, worker, generation)?;
        let root = self.project_root(&id)?;
        let _full = safe_relative_file(&root, path)?;
        let outline = agency_codeindex::outline_file(&root, path.trim())
            .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
        Ok(serde_json::to_value(outline)?)
    }

    pub(crate) fn code_symbols(
        &self,
        project: &str,
        query: &str,
        limit: Option<usize>,
        worker: Option<&str>,
        generation: Option<u64>,
    ) -> Result<Value, AgencyError> {
        let id = ProjectId::new(project)?;
        self.validate_worker(&id, worker, generation)?;
        if query.chars().count() > MAX_QUERY {
            return Err(AgencyError::BadRequest("query too long".to_owned()));
        }
        let root = self.project_root(&id)?;
        let limit = limit.unwrap_or(40).clamp(1, MAX_HITS);
        let symbols = agency_codeindex::search_symbols(&root, query, limit)
            .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
        Ok(json!({ "symbols": symbols }))
    }

    pub(crate) fn code_view_range(
        &self,
        project: &str,
        path: &str,
        start_line: usize,
        end_line: usize,
        worker: Option<&str>,
        generation: Option<u64>,
    ) -> Result<Value, AgencyError> {
        let id = ProjectId::new(project)?;
        self.validate_worker(&id, worker, generation)?;
        let root = self.project_root(&id)?;
        let full = safe_relative_file(&root, path)?;
        let content = fs::read_to_string(&full)
            .map_err(|e| AgencyError::BadRequest(format!("cannot read file: {e}")))?;
        let view = view_line_range(&content, start_line, end_line)
            .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
        Ok(serde_json::to_value(view)?)
    }

    pub(crate) fn code_patch(
        &mut self,
        project: &str,
        path: &str,
        chunks: &[ReplacementChunk],
        worker: Option<&str>,
        generation: Option<u64>,
    ) -> Result<Value, AgencyError> {
        let id = ProjectId::new(project)?;
        self.validate_worker(&id, worker, generation)?;
        let root = self.project_root(&id)?;
        let full = safe_relative_file(&root, path)?;
        let content = fs::read_to_string(&full)
            .map_err(|e| AgencyError::BadRequest(format!("cannot read file: {e}")))?;
        let outcome = apply_surgical_patches(&content, chunks)
            .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
        files::write_atomic(&full, outcome.updated_content.as_bytes())?;
        self.event(
            "code.patched",
            json!({
                "project": id,
                "path": path.trim(),
                "replacements": outcome.replacements_applied,
                "new_lines": outcome.new_lines,
            }),
        )?;
        Ok(json!({
            "path": path.trim(),
            "replacements_applied": outcome.replacements_applied,
            "previous_lines": outcome.previous_lines,
            "new_lines": outcome.new_lines,
        }))
    }
}
