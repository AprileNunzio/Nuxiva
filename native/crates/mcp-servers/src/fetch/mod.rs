mod config;
mod net;
pub(crate) mod plain;

use serde_json::{Map, Value, json};
use tokio::runtime::Handle;

use nuxiva_mcp_core::{Implementation, McpError, McpResult, ToolOutput, ToolServer};

pub use config::FetchConfig;

#[derive(Debug)]
pub struct FetchServer {
    config: FetchConfig,
    name: String,
}

impl FetchServer {
    pub fn new(name: &str, config: &FetchConfig) -> McpResult<Self> {
        config.validate()?;
        Ok(Self {
            config: config.clone(),
            name: name.to_owned(),
        })
    }
}

impl ToolServer for FetchServer {
    fn info(&self) -> Implementation {
        Implementation {
            name: self.name.clone(),
            version: env!("CARGO_PKG_VERSION").to_owned(),
            title: None,
        }
    }

    fn tools(&self) -> Vec<Value> {
        vec![json!({
            "name": "http_get",
            "description": "scarica il testo di una pagina web o di un'API pubblica",
            "inputSchema": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "indirizzo http(s)"}},
                "required": ["url"],
                "additionalProperties": false,
            },
            "annotations": {"readOnlyHint": true, "destructiveHint": false, "openWorldHint": true, "idempotentHint": true},
        })]
    }

    fn call(&self, name: &str, arguments: &Map<String, Value>) -> ToolOutput {
        if name != "http_get" {
            return ToolOutput::fail("strumento sconosciuto");
        }
        let Some(url) = arguments.get("url").and_then(Value::as_str) else {
            return ToolOutput::fail("indirizzo non valido");
        };
        let Ok(handle) = Handle::try_current() else {
            return ToolOutput::fail(McpError::Closed.code());
        };
        match handle.block_on(net::get(&self.config, url)) {
            Ok(page) => {
                let html = String::from_utf8_lossy(&page.body);
                let text = plain::plain(&html, self.config.text_limit);
                ToolOutput::ok(format!("HTTP {}\n{text}", page.status))
            }
            Err(message) => ToolOutput::fail(message),
        }
    }
}
