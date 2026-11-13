use serde::{Deserialize, Serialize};

use crate::error::{GraphError, GraphResult};

pub const CEIL_FILES: usize = 500_000;
pub const CEIL_FILE_BYTES: usize = 8 * 1024 * 1024;
pub const CEIL_ITEMS: usize = 4_096;
pub const CEIL_PATH: usize = 1_024;
pub const CEIL_NAME: usize = 256;
pub const CEIL_RESULTS: usize = 4_096;
pub const CEIL_DEPTH: usize = 32;
pub const CEIL_VISITED: usize = 5_000_000;
pub const CEIL_PACK: usize = 200_000;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct GraphSettings {
    pub max_files: usize,
    pub max_file_bytes: usize,
    pub max_symbols_per_file: usize,
    pub max_imports_per_file: usize,
    pub max_path_chars: usize,
    pub max_name_chars: usize,
    pub max_results: usize,
    pub max_depth: usize,
    pub max_visited: usize,
    pub max_pack_chars: usize,
}

impl Default for GraphSettings {
    fn default() -> Self {
        Self {
            max_files: 100_000,
            max_file_bytes: 1024 * 1024,
            max_symbols_per_file: 512,
            max_imports_per_file: 256,
            max_path_chars: 512,
            max_name_chars: 120,
            max_results: 200,
            max_depth: 6,
            max_visited: 50_000,
            max_pack_chars: 24_000,
        }
    }
}

fn within(value: usize, ceiling: usize) -> bool {
    (1..=ceiling).contains(&value)
}

impl GraphSettings {
    pub fn validate(&self) -> GraphResult<()> {
        let ok = within(self.max_files, CEIL_FILES)
            && within(self.max_file_bytes, CEIL_FILE_BYTES)
            && within(self.max_symbols_per_file, CEIL_ITEMS)
            && within(self.max_imports_per_file, CEIL_ITEMS)
            && within(self.max_path_chars, CEIL_PATH)
            && within(self.max_name_chars, CEIL_NAME)
            && within(self.max_results, CEIL_RESULTS)
            && within(self.max_depth, CEIL_DEPTH)
            && within(self.max_visited, CEIL_VISITED)
            && within(self.max_pack_chars, CEIL_PACK);
        if ok {
            Ok(())
        } else {
            Err(GraphError::Settings)
        }
    }

    pub fn from_json(raw: &str) -> GraphResult<Self> {
        if raw.len() > 64 * 1024 {
            return Err(GraphError::TooLarge);
        }
        let parsed: Self = serde_json::from_str(raw).map_err(|_| GraphError::Settings)?;
        parsed.validate()?;
        Ok(parsed)
    }
}
