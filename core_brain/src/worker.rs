use std::collections::{BTreeMap, BTreeSet};
use std::sync::{Arc, Mutex, PoisonError};

use nuxiva_mcp_core::{CallRequest, Hub, McpError};
use nuxiva_swarm_core::{
    BoxFuture, Ident, Output, StepContext, Worker, WorkerError, WorkerErrorKind,
};
use serde_json::{Map, Value, json};

const MAX_PENDING: usize = 256;

#[derive(Debug, Clone)]
pub struct Utterance {
    pub text: String,
    pub principal: String,
}

#[derive(Debug, Clone, Default)]
pub struct Pending {
    inner: Arc<Mutex<BTreeMap<String, Utterance>>>,
}

impl Pending {
    pub fn insert(&self, task: &str, utterance: Utterance) -> bool {
        let mut guard = self.inner.lock().unwrap_or_else(PoisonError::into_inner);
        if guard.len() >= MAX_PENDING && !guard.contains_key(task) {
            return false;
        }
        guard.insert(task.to_owned(), utterance);
        true
    }

    #[must_use]
    pub fn get(&self, task: &str) -> Option<Utterance> {
        self.inner
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .get(task)
            .cloned()
    }

    pub fn remove(&self, task: &str) {
        self.inner
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .remove(task);
    }
}

pub type Declared = BTreeMap<String, BTreeSet<String>>;

pub struct McpWorker {
    hub: Arc<Hub>,
    pending: Pending,
    declared: Declared,
}

impl std::fmt::Debug for McpWorker {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("McpWorker(..)")
    }
}

fn error(context: &StepContext, kind: WorkerErrorKind, code: &str) -> WorkerError {
    let ident = Ident::new(code).unwrap_or_else(|_| context.step.id.clone());
    WorkerError::new(kind, ident, context.step.id.clone())
}

fn kind_of(error: McpError) -> WorkerErrorKind {
    match error {
        McpError::Timeout => WorkerErrorKind::Timeout,
        McpError::UnknownTool | McpError::NotCallable => WorkerErrorKind::Unavailable,
        _ => WorkerErrorKind::Denied,
    }
}

const TEXT_ARGS: [&str; 6] = ["goal", "query", "text", "prompt", "message", "input"];

fn is_string(schema: &Value, name: &str) -> bool {
    schema
        .get("properties")
        .and_then(|p| p.get(name))
        .and_then(|p| p.get("type"))
        .and_then(Value::as_str)
        == Some("string")
}

#[must_use]
pub fn arguments_for(schema: &Value, text: &str) -> Option<Map<String, Value>> {
    let properties = schema.get("properties").and_then(Value::as_object);
    let required: Vec<&str> = schema
        .get("required")
        .and_then(Value::as_array)
        .map(|r| r.iter().filter_map(Value::as_str).collect())
        .unwrap_or_default();
    let strings: Vec<&str> = properties
        .map(|p| {
            p.keys()
                .map(String::as_str)
                .filter(|k| is_string(schema, k))
                .collect()
        })
        .unwrap_or_default();
    let target = TEXT_ARGS
        .iter()
        .copied()
        .find(|k| strings.contains(k))
        .or_else(|| match required.as_slice() {
            [only] if strings.contains(only) => Some(*only),
            [] => match strings.as_slice() {
                [only] => Some(*only),
                _ => None,
            },
            _ => None,
        })?;
    if required.iter().any(|r| *r != target) {
        return None;
    }
    let mut arguments = Map::new();
    arguments.insert(target.to_owned(), Value::String(text.to_owned()));
    Some(arguments)
}

impl McpWorker {
    #[must_use]
    pub fn new(hub: Arc<Hub>, pending: Pending, declared: Declared) -> Self {
        Self {
            hub,
            pending,
            declared,
        }
    }

    fn pick(&self, agent: &str, intent: &str) -> Result<(String, Value), &'static str> {
        let snapshot = self.hub.registry().snapshot();
        let names = self.declared.get(agent);
        let mut owned: Vec<_> = snapshot
            .iter()
            .filter(|e| names.is_some_and(|n| n.contains(&e.remote_name)))
            .collect();
        if owned.is_empty() {
            owned = snapshot.iter().filter(|e| e.server == agent).collect();
        }
        owned.sort_by(|a, b| a.id.cmp(&b.id));
        let narrowed: Vec<_> = owned
            .iter()
            .filter(|e| e.id.contains(intent) || e.remote_name.contains(intent))
            .collect();
        let chosen = match (owned.as_slice(), narrowed.as_slice()) {
            ([], _) => return Err("no-tool"),
            ([only], _) => only,
            (_, [one]) => *one,
            _ => return Err("ambiguous-tool"),
        };
        Ok((chosen.id.clone(), chosen.spec.input_schema.clone()))
    }
}

impl Worker for McpWorker {
    fn run(&self, context: StepContext) -> BoxFuture<'_, Result<Output, WorkerError>> {
        Box::pin(async move {
            let Some(utterance) = self.pending.get(context.task.id.as_str()) else {
                return Err(error(&context, WorkerErrorKind::Invalid, "no-input"));
            };
            let (tool, schema) = self
                .pick(
                    context.step.worker_template.as_str(),
                    context.step.intent.as_str(),
                )
                .map_err(|code| error(&context, WorkerErrorKind::Unavailable, code))?;
            let Some(arguments) = arguments_for(&schema, &utterance.text) else {
                return Err(error(&context, WorkerErrorKind::Invalid, "bad-arguments"));
            };
            context.charge_call()?;
            let request = CallRequest {
                tool: tool.clone(),
                principal: utterance.principal,
                agent: context.step.worker_template.as_str().to_owned(),
                operation: context.step.intent.as_str().to_owned(),
                arguments,
                consent: None,
            };
            let outcome = self.hub.call(request).await;
            match outcome {
                Ok(out) if out.external.is_error => {
                    Err(error(&context, WorkerErrorKind::Unavailable, "tool-error"))
                }
                Ok(out) => Ok(Output {
                    value: json!({
                        "tool": tool,
                        "external": true,
                        "trusted": out.external.trusted,
                        "text": out.external.text,
                        "structured": out.structured,
                    }),
                    evidence: Vec::new(),
                }),
                Err(e) => Err(error(&context, kind_of(e), "mcp-denied")),
            }
        })
    }
}
