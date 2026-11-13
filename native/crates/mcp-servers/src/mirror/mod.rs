use std::collections::HashMap;
use std::sync::Arc;

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value, json};

use nuxiva_mcp_core::{Implementation, McpError, McpResult, ToolOutput, ToolServer};

pub const MAX_TOOLS: usize = 4_096;
pub const MAX_NAME: usize = 64;
pub const MAX_DESCRIPTION: usize = 1_024;
pub const CONTEXT_KEY: &str = "_context";
pub const MAX_CONTEXT: usize = 64;

pub trait Dispatch: std::fmt::Debug + Send + Sync + 'static {
    fn call(
        &self,
        server: &str,
        tool: &str,
        arguments: &Map<String, Value>,
        context: Option<&str>,
    ) -> ToolOutput;
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct MirrorTool {
    pub name: String,
    pub description: String,
    pub input_schema: Value,
    pub read_only: bool,
    pub destructive: bool,
    pub open_world: bool,
}

impl Default for MirrorTool {
    fn default() -> Self {
        Self {
            name: String::new(),
            description: String::new(),
            input_schema: json!({"type": "object", "properties": {}}),
            read_only: false,
            destructive: false,
            open_world: false,
        }
    }
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct MirrorConfig {
    pub tools: Vec<MirrorTool>,
}

fn valid_name(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= MAX_NAME
        && name
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-'))
}

impl MirrorConfig {
    pub fn validate(&self) -> McpResult<()> {
        let mut seen = std::collections::HashSet::new();
        let sound = !self.tools.is_empty()
            && self.tools.len() <= MAX_TOOLS
            && self.tools.iter().all(|t| {
                valid_name(&t.name)
                    && seen.insert(t.name.as_str())
                    && t.description.len() <= MAX_DESCRIPTION
                    && t.input_schema.get("type").and_then(Value::as_str) == Some("object")
                    && t.input_schema
                        .get("properties")
                        .and_then(Value::as_object)
                        .is_none_or(|p| !p.contains_key(CONTEXT_KEY))
                    && !(t.read_only && t.destructive)
            });
        if sound {
            Ok(())
        } else {
            Err(McpError::InvalidSettings)
        }
    }
}

pub struct MirrorServer {
    name: String,
    tools: Vec<MirrorTool>,
    index: HashMap<String, usize>,
    dispatch: Arc<dyn Dispatch>,
}

impl std::fmt::Debug for MirrorServer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MirrorServer")
            .field("name", &self.name)
            .finish_non_exhaustive()
    }
}

impl MirrorServer {
    pub fn new(name: &str, config: &MirrorConfig, dispatch: Arc<dyn Dispatch>) -> McpResult<Self> {
        config.validate()?;
        let index = config
            .tools
            .iter()
            .enumerate()
            .map(|(i, t)| (t.name.clone(), i))
            .collect();
        Ok(Self {
            name: name.to_owned(),
            tools: config.tools.clone(),
            index,
            dispatch,
        })
    }
}

impl ToolServer for MirrorServer {
    fn info(&self) -> Implementation {
        Implementation {
            name: self.name.clone(),
            version: env!("CARGO_PKG_VERSION").to_owned(),
            title: None,
        }
    }

    fn tools(&self) -> Vec<Value> {
        self.tools
            .iter()
            .map(|t| {
                let mut schema = t.input_schema.clone();
                if let Some(object) = schema.as_object_mut() {
                    let properties = object
                        .entry("properties")
                        .or_insert_with(|| Value::Object(Map::new()));
                    if let Some(properties) = properties.as_object_mut() {
                        properties.insert(
                            CONTEXT_KEY.to_owned(),
                            json!({"type": "string", "maxLength": MAX_CONTEXT}),
                        );
                    }
                }
                json!({
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": schema,
                    "annotations": {
                        "readOnlyHint": t.read_only,
                        "destructiveHint": t.destructive,
                        "openWorldHint": t.open_world,
                        "idempotentHint": t.read_only,
                    },
                })
            })
            .collect()
    }

    fn call(&self, name: &str, arguments: &Map<String, Value>) -> ToolOutput {
        if !self.index.contains_key(name) {
            return ToolOutput::fail("strumento sconosciuto");
        }
        let mut clean = arguments.clone();
        let context = match clean.remove(CONTEXT_KEY) {
            Some(Value::String(token)) => Some(token),
            Some(_) => return ToolOutput::fail("contesto non valido"),
            None => None,
        };
        self.dispatch
            .call(&self.name, name, &clean, context.as_deref())
    }
}
