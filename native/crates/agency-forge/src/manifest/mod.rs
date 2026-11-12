use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::ast_guard::{inspect_tool_source, validate_tool_name};
use crate::error::ForgeError;

pub const MIN_TESTS: usize = 2;
pub const MAX_TESTS: usize = 8;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ToolStatus {
    Proposed,
    Active,
    Quarantined,
    Revoked,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ToolTestCase {
    pub args: BTreeMap<String, Value>,
    pub expect: Value,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ForgedToolSpec {
    pub name: String,
    pub description: String,
    pub args_schema: BTreeMap<String, String>,
    pub code: String,
    pub tests: Vec<ToolTestCase>,
    pub project_id: String,
    pub task_id: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ForgedToolRecord {
    pub name: String,
    pub call_name: String,
    pub version: u32,
    pub description: String,
    pub args_schema: BTreeMap<String, String>,
    pub code: String,
    pub tests: Vec<ToolTestCase>,
    pub status: ToolStatus,
    pub approved: bool,
    pub project_id: String,
    pub task_id: String,
    pub invocations: u64,
    pub failures: u64,
    pub last_error: Option<String>,
}

impl ForgedToolRecord {
    pub fn from_spec(spec: ForgedToolSpec, version: u32) -> Result<Self, ForgeError> {
        let clean_name = validate_tool_name(&spec.name)?;
        let _verdict = inspect_tool_source(&spec.code)?;
        if !(MIN_TESTS..=MAX_TESTS).contains(&spec.tests.len()) {
            return Err(ForgeError::InvalidTests(format!(
                "between {MIN_TESTS} and {MAX_TESTS} deterministic test cases are required"
            )));
        }
        let call_name = format!("x_{clean_name}");
        Ok(Self {
            name: clean_name,
            call_name,
            version: version.max(1),
            description: spec.description.trim().chars().take(300).collect(),
            args_schema: spec.args_schema,
            code: spec.code,
            tests: spec.tests,
            status: ToolStatus::Proposed,
            approved: false,
            project_id: spec.project_id,
            task_id: spec.task_id,
            invocations: 0,
            failures: 0,
            last_error: None,
        })
    }

    #[must_use]
    pub fn is_callable(&self) -> bool {
        self.approved && self.status == ToolStatus::Active
    }
}
