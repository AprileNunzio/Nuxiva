use serde::{Deserialize, Serialize};

use super::error::BenchError;

const MAX_FILES: usize = 10_000_000;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BenchConfig {
    pub files: usize,
    pub files_per_dir: usize,
    pub seed: u64,
    pub max_memory_bytes: usize,
    pub search_queries: Vec<String>,
    pub search_limit: usize,
    pub search_rounds: usize,
    pub updated_files: usize,
    pub added_files: usize,
    pub removed_files: usize,
}

impl BenchConfig {
    pub fn from_json(raw: &str) -> Result<Self, BenchError> {
        let config: Self = serde_json::from_str(raw)?;
        config.validate()?;
        Ok(config)
    }

    pub fn validate(&self) -> Result<(), BenchError> {
        if self.files == 0 || self.files > MAX_FILES {
            return Err(BenchError::Config("files out of range"));
        }
        if self.files_per_dir == 0 {
            return Err(BenchError::Config("files_per_dir must be positive"));
        }
        if self.search_queries.is_empty() || self.search_queries.iter().any(String::is_empty) {
            return Err(BenchError::Config("search_queries must be non-empty"));
        }
        if self.search_limit == 0 || self.search_rounds == 0 {
            return Err(BenchError::Config(
                "search limit and rounds must be positive",
            ));
        }
        if self.updated_files.saturating_add(self.removed_files) > self.files {
            return Err(BenchError::Config("mutations exceed corpus size"));
        }
        if self.files.saturating_add(self.added_files) > MAX_FILES {
            return Err(BenchError::Config("added files exceed limit"));
        }
        if self.max_memory_bytes == 0 {
            return Err(BenchError::Config("max_memory_bytes must be positive"));
        }
        Ok(())
    }

    #[must_use]
    pub fn total_capacity(&self) -> usize {
        self.files.saturating_add(self.added_files)
    }
}
