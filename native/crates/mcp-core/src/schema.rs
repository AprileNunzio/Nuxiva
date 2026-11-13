use std::sync::Arc;

use jsonschema::Validator;
use serde_json::{Map, Value};

use crate::error::{McpError, McpResult};

#[derive(Clone)]
pub struct CompiledSchema(Arc<Validator>);

impl std::fmt::Debug for CompiledSchema {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("CompiledSchema")
    }
}

impl CompiledSchema {
    pub fn compile(schema: &Value) -> McpResult<Self> {
        jsonschema::validator_for(schema)
            .map(|validator| Self(Arc::new(validator)))
            .map_err(|_| McpError::InvalidTool)
    }

    #[must_use]
    pub fn accepts(&self, instance: &Value) -> bool {
        self.0.is_valid(instance)
    }

    pub fn check_arguments(&self, arguments: &Map<String, Value>) -> McpResult<()> {
        let instance = Value::Object(arguments.clone());
        if self.accepts(&instance) {
            Ok(())
        } else {
            Err(McpError::InvalidArguments)
        }
    }

    pub fn check_output(&self, structured: &Value) -> McpResult<()> {
        if self.accepts(structured) {
            Ok(())
        } else {
            Err(McpError::InvalidOutput)
        }
    }
}
