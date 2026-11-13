use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::error::{McpError, McpResult};
use crate::settings::Settings;
use crate::shape::{depth, node_count};
use crate::text::sanitize_text;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Implementation {
    pub name: String,
    #[serde(default)]
    pub version: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub title: Option<String>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ListChanged {
    #[serde(default)]
    pub list_changed: bool,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ResourceCaps {
    #[serde(default)]
    pub subscribe: bool,
    #[serde(default)]
    pub list_changed: bool,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ServerCapabilities {
    #[serde(default)]
    pub tools: Option<ListChanged>,
    #[serde(default)]
    pub resources: Option<ResourceCaps>,
    #[serde(default)]
    pub prompts: Option<ListChanged>,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct InitializeResult {
    pub protocol_version: String,
    #[serde(default)]
    pub capabilities: ServerCapabilities,
    pub server_info: Implementation,
    #[serde(default)]
    pub instructions: Option<String>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ToolAnnotations {
    #[serde(
        default,
        rename = "readOnlyHint",
        skip_serializing_if = "Option::is_none"
    )]
    pub read_only: Option<bool>,
    #[serde(
        default,
        rename = "destructiveHint",
        skip_serializing_if = "Option::is_none"
    )]
    pub destructive: Option<bool>,
    #[serde(
        default,
        rename = "idempotentHint",
        skip_serializing_if = "Option::is_none"
    )]
    pub idempotent: Option<bool>,
    #[serde(
        default,
        rename = "openWorldHint",
        skip_serializing_if = "Option::is_none"
    )]
    pub open_world: Option<bool>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ToolSpec {
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub title: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    pub input_schema: Value,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub output_schema: Option<Value>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub annotations: Option<ToolAnnotations>,
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Content {
    Text {
        text: String,
    },
    Image {
        data: String,
        #[serde(rename = "mimeType")]
        mime_type: String,
    },
    Audio {
        data: String,
        #[serde(rename = "mimeType")]
        mime_type: String,
    },
    ResourceLink {
        uri: String,
        #[serde(default)]
        name: String,
    },
    Resource {
        resource: Value,
    },
    #[serde(other)]
    Unknown,
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CallToolResult {
    #[serde(default)]
    pub content: Vec<Content>,
    #[serde(default)]
    pub structured_content: Option<Value>,
    #[serde(default)]
    pub is_error: bool,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct ToolsPage {
    #[serde(default)]
    tools: Vec<Value>,
    #[serde(default)]
    next_cursor: Option<String>,
}

fn valid_tool_name(name: &str, max_len: usize) -> bool {
    !name.is_empty()
        && name.len() <= max_len
        && name
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '_' | '.' | '-'))
}

fn check_schema(schema: &Value, settings: &Settings) -> McpResult<()> {
    let Value::Object(map) = schema else {
        return Err(McpError::InvalidTool);
    };
    if map.get("type").and_then(Value::as_str) != Some("object") {
        return Err(McpError::InvalidTool);
    }
    let bytes = serde_json::to_vec(schema).map_err(|_| McpError::Serialize)?;
    if bytes.len() > settings.max_schema_bytes {
        return Err(McpError::TooLarge);
    }
    if depth(schema) > settings.max_schema_depth || node_count(schema) > settings.max_schema_nodes {
        return Err(McpError::TooDeep);
    }
    Ok(())
}

pub fn parse_tool(value: Value, settings: &Settings) -> McpResult<ToolSpec> {
    let mut spec: ToolSpec = serde_json::from_value(value).map_err(|_| McpError::InvalidTool)?;
    if !valid_tool_name(&spec.name, settings.max_name_len) {
        return Err(McpError::InvalidTool);
    }
    check_schema(&spec.input_schema, settings)?;
    if let Some(output) = &spec.output_schema {
        check_schema(output, settings)?;
    }
    spec.description = spec
        .description
        .map(|d| sanitize_text(&d, settings.max_description_chars));
    spec.title = spec
        .title
        .map(|t| sanitize_text(&t, settings.max_description_chars));
    Ok(spec)
}

pub fn parse_tools_page(
    result: Value,
    settings: &Settings,
) -> McpResult<(Vec<McpResult<ToolSpec>>, Option<String>)> {
    let page: ToolsPage = serde_json::from_value(result).map_err(|_| McpError::InvalidMessage)?;
    if page.tools.len() > settings.max_tools_per_server {
        return Err(McpError::TooLarge);
    }
    let cursor = page
        .next_cursor
        .filter(|c| !c.is_empty() && c.len() <= settings.max_name_len.saturating_mul(8));
    let tools = page
        .tools
        .into_iter()
        .map(|tool| parse_tool(tool, settings))
        .collect();
    Ok((tools, cursor))
}

pub fn parse_initialize_result(result: Value) -> McpResult<InitializeResult> {
    serde_json::from_value(result).map_err(|_| McpError::InvalidMessage)
}

pub fn parse_call_result(result: Value) -> McpResult<CallToolResult> {
    serde_json::from_value(result).map_err(|_| McpError::InvalidMessage)
}
