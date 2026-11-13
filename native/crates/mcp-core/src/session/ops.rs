use std::collections::HashSet;

use serde_json::{Map, Value};

use super::core::Session;
use crate::error::{McpError, McpResult};
use crate::protocol::{
    CallToolResult, Id, Implementation, InitializeResult, Message, ToolSpec, VersionProfile,
    initialized_notification, negotiate, parse_call_result, parse_initialize_result,
    parse_tools_page, supported_versions,
};
use crate::settings::Settings;
use crate::transport::Link;

#[derive(Debug, Clone, Default)]
pub struct ToolListing {
    pub tools: Vec<ToolSpec>,
    pub rejected: usize,
}

impl Session {
    pub async fn connect(
        link: Link,
        settings: Settings,
        client: &Implementation,
    ) -> McpResult<(Self, InitializeResult, &'static VersionProfile)> {
        settings.validate()?;
        let session = Self::open(link, settings);
        let preferred = supported_versions()
            .first()
            .copied()
            .ok_or(McpError::UnsupportedVersion)?;
        let init = crate::protocol::initialize_request(Id::Number(0), preferred, client);
        let Message::Request(request) = init else {
            return Err(McpError::InvalidMessage);
        };
        let value = session.call("initialize", request.params).await?;
        let result = parse_initialize_result(value)?;
        let profile = negotiate(&result.protocol_version).ok_or(McpError::UnsupportedVersion)?;
        session.notify(initialized_notification()).await?;
        Ok((session, result, profile))
    }

    pub async fn list_tools(&self) -> McpResult<ToolListing> {
        let mut listing = ToolListing::default();
        let mut seen: HashSet<String> = HashSet::new();
        let mut cursor: Option<String> = None;
        for _ in 0..self.settings.max_pages {
            let mut params = Map::new();
            if let Some(c) = &cursor {
                params.insert("cursor".into(), Value::String(c.clone()));
            }
            let value = self
                .call(
                    "tools/list",
                    if params.is_empty() {
                        None
                    } else {
                        Some(params)
                    },
                )
                .await?;
            let (tools, next) = parse_tools_page(value, &self.settings)?;
            for tool in tools {
                match tool {
                    Ok(spec) if listing.tools.len() < self.settings.max_tools_per_server => {
                        listing.tools.push(spec);
                    }
                    _ => listing.rejected = listing.rejected.saturating_add(1),
                }
            }
            match next {
                Some(c) if seen.insert(c.clone()) => cursor = Some(c),
                Some(_) => return Err(McpError::InvalidMessage),
                None => return Ok(listing),
            }
        }
        Err(McpError::TooLarge)
    }

    pub async fn call_tool(
        &self,
        name: &str,
        arguments: Map<String, Value>,
    ) -> McpResult<CallToolResult> {
        let mut params = Map::new();
        params.insert("name".into(), Value::String(name.to_owned()));
        params.insert("arguments".into(), Value::Object(arguments));
        parse_call_result(self.call("tools/call", Some(params)).await?)
    }
}
