use agency_domain::ProjectId;
use serde_json::{Value, json};

use crate::engine::Engine;
use crate::error::AgencyError;

const MAX_QUERY: usize = 200;
const MAX_HITS: usize = 200;

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
}
