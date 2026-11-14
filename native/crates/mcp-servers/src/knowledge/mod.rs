mod spec;

use std::sync::Arc;

use nuxiva_knowledge_core::Service;
use nuxiva_mcp_core::{Implementation, ToolOutput, ToolServer};
use serde_json::{Map, Value, json};

pub type Identity = Arc<dyn Fn() -> Option<String> + Send + Sync>;

pub struct KnowledgeServer {
    name: String,
    service: Arc<Service>,
    identity: Identity,
}

impl std::fmt::Debug for KnowledgeServer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("KnowledgeServer")
            .field("name", &self.name)
            .finish_non_exhaustive()
    }
}

fn pick(args: &Map<String, Value>, allowed: &[&str]) -> Value {
    Value::Object(
        args.iter()
            .filter(|(k, _)| allowed.contains(&k.as_str()))
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect(),
    )
}

impl KnowledgeServer {
    #[must_use]
    pub fn new(name: &str, service: Arc<Service>, identity: Identity) -> Self {
        Self {
            name: name.to_owned(),
            service,
            identity,
        }
    }

    fn request(name: &str, who: &str, args: &Map<String, Value>) -> Option<Value> {
        let value = match name {
            "knowledge_search" => json!({
                "op": "search",
                "as": who,
                "query": pick(args, &["text", "kinds", "limit", "depth", "household", "min_confidence"]),
            }),
            "knowledge_neighbors" => {
                let node = match (args.get("kind"), args.get("label")) {
                    (Some(kind), Some(label)) => json!({"kind": kind, "label": label}),
                    _ => Value::Null,
                };
                let mut query = pick(args, &["relation", "direction", "limit"]);
                if let (Some(map), false) = (query.as_object_mut(), node.is_null()) {
                    map.insert("node".to_owned(), node);
                }
                json!({"op": "neighbors", "as": who, "query": query})
            }
            "knowledge_learn" => json!({
                "op": "extract",
                "as": who,
                "text": args.get("text")?,
                "origin": "conversation",
                "reference": args.get("reference").cloned().unwrap_or_else(|| json!("")),
                "store": true,
            }),
            "knowledge_observe" => json!({"op": "observe", "as": who, "label": args.get("label")?}),
            "knowledge_correct" => {
                json!({"op": "correct", "as": who, "correction": args.get("correction")?})
            }
            "knowledge_export" => json!({"op": "export", "as": who}),
            _ => return None,
        };
        Some(value)
    }

    fn run(&self, name: &str, args: &Map<String, Value>) -> ToolOutput {
        let Some(who) = (self.identity)() else {
            return ToolOutput::fail("knowledge.identity");
        };
        let Some(request) = Self::request(name, &who, args) else {
            return ToolOutput::fail("knowledge.invalid");
        };
        let reply = self.service.handle(&request.to_string());
        match serde_json::from_str::<Value>(&reply) {
            Ok(parsed) if parsed.get("ok") == Some(&Value::Bool(true)) => ToolOutput::ok(
                parsed
                    .get("data")
                    .map_or_else(String::new, Value::to_string),
            ),
            Ok(parsed) => ToolOutput::fail(
                parsed
                    .get("error")
                    .and_then(Value::as_str)
                    .unwrap_or("knowledge.invalid")
                    .to_owned(),
            ),
            Err(_) => ToolOutput::fail("knowledge.corrupt"),
        }
    }
}

impl ToolServer for KnowledgeServer {
    fn info(&self) -> Implementation {
        Implementation {
            name: self.name.clone(),
            version: env!("CARGO_PKG_VERSION").to_owned(),
            title: None,
        }
    }

    fn tools(&self) -> Vec<Value> {
        spec::tools()
    }

    fn call(&self, name: &str, arguments: &Map<String, Value>) -> ToolOutput {
        self.run(name, arguments)
    }
}

#[cfg(test)]
mod tests;
