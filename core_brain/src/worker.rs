use std::collections::BTreeMap;
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

pub struct McpWorker {
    hub: Arc<Hub>,
    pending: Pending,
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

impl McpWorker {
    #[must_use]
    pub fn new(hub: Arc<Hub>, pending: Pending) -> Self {
        Self { hub, pending }
    }

    fn pick(&self, intent: &str) -> Option<String> {
        let snapshot = self.hub.registry().snapshot();
        let mut ids: Vec<&str> = snapshot
            .iter()
            .filter(|e| e.id.contains(intent) || e.remote_name.contains(intent))
            .map(|e| e.id.as_str())
            .collect();
        ids.sort_unstable();
        ids.first().map(|s| (*s).to_owned())
    }
}

impl Worker for McpWorker {
    fn run(&self, context: StepContext) -> BoxFuture<'_, Result<Output, WorkerError>> {
        Box::pin(async move {
            let Some(utterance) = self.pending.get(context.task.id.as_str()) else {
                return Err(error(&context, WorkerErrorKind::Invalid, "no-input"));
            };
            let Some(tool) = self.pick(context.step.intent.as_str()) else {
                return Err(error(&context, WorkerErrorKind::Unavailable, "no-tool"));
            };
            context.charge_call()?;
            let mut arguments = Map::new();
            arguments.insert("goal".to_owned(), Value::String(utterance.text));
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
