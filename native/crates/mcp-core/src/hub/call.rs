use std::sync::PoisonError;
use std::sync::atomic::Ordering;
use std::time::{Instant, SystemTime, UNIX_EPOCH};

use serde::Serialize;
use serde_json::Value;

use super::Hub;
use crate::audit::{AuditEvent, Verdict, hash_value};
use crate::error::{McpError, McpResult};
use crate::policy::{CallRequest, ExternalData, Gate, Risk, Scope, wrap_result};
use crate::registry::ToolEntry;

#[derive(Debug, Clone, Serialize)]
pub struct CallOutput {
    pub external: ExternalData,
    pub structured: Option<Value>,
    pub risk: Risk,
}

fn verdict_of(error: McpError) -> Verdict {
    match error {
        McpError::Timeout => Verdict::TimedOut,
        McpError::NotPermitted
        | McpError::ConsentRequired
        | McpError::ConsentDenied
        | McpError::RateLimited
        | McpError::InvalidArguments
        | McpError::NotCallable
        | McpError::UnknownTool => Verdict::Denied,
        _ => Verdict::Failed,
    }
}

fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| u64::try_from(d.as_millis()).unwrap_or(u64::MAX))
}

impl Hub {
    fn lookup(&self, request: &CallRequest) -> McpResult<(std::sync::Arc<ToolEntry>, Risk)> {
        let snapshot = self.registry.snapshot();
        let entry = snapshot.get(&request.tool).ok_or(McpError::UnknownTool)?;
        Ok((std::sync::Arc::clone(entry), entry.risk))
    }

    #[must_use]
    pub fn needs_consent(&self, tool_id: &str, operation: &str) -> bool {
        self.registry
            .snapshot()
            .get(tool_id)
            .is_none_or(|entry| self.gate.needs_consent(entry.risk, operation))
    }

    pub fn request_consent(&self, request: &CallRequest) -> McpResult<String> {
        let (entry, _) = self.lookup(request)?;
        self.gate
            .consent
            .issue(Gate::consent_key(request, &entry), Instant::now())
    }

    pub async fn call(&self, request: CallRequest) -> McpResult<CallOutput> {
        let started = Instant::now();
        let looked = self.lookup(&request);
        let outcome = match &looked {
            Ok((entry, _)) => self.execute(&request, entry).await,
            Err(error) => Err(*error),
        };
        let (server, risk) = looked
            .as_ref()
            .map_or((String::new(), Risk::Critical), |(e, r)| {
                (e.server.clone(), *r)
            });
        let (verdict, response_hash) = match &outcome {
            Ok(out) if out.external.is_error => (
                Verdict::Failed,
                hash_value(&Value::String(out.external.text.clone())),
            ),
            Ok(out) => (
                Verdict::Completed,
                hash_value(&Value::String(out.external.text.clone())),
            ),
            Err(error) => (
                verdict_of(*error),
                hash_value(&Value::String(error.code().to_owned())),
            ),
        };
        let event = AuditEvent {
            ts_ms: now_ms(),
            principal: request.principal.clone(),
            agent: request.agent.clone(),
            server,
            tool: request.tool.clone(),
            risk,
            verdict,
            duration_ms: u64::try_from(started.elapsed().as_millis()).unwrap_or(u64::MAX),
            args_hash: hash_value(&Value::Object(request.arguments.clone())),
            response_hash,
        };
        self.audit
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .append(event)?;
        outcome
    }

    async fn execute(&self, request: &CallRequest, entry: &ToolEntry) -> McpResult<CallOutput> {
        let scope = self
            .scopes
            .read()
            .unwrap_or_else(PoisonError::into_inner)
            .get(&request.agent)
            .cloned()
            .unwrap_or_else(Scope::none);
        let server_max = self
            .servers
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .get(&entry.server)
            .map(|r| r.entry.max_risk)
            .ok_or(McpError::NotCallable)?;
        self.gate
            .check(request, entry, &scope, server_max, Instant::now())?;
        let session = {
            let servers = self.servers.lock().unwrap_or_else(PoisonError::into_inner);
            let running = servers.get(&entry.server).ok_or(McpError::NotCallable)?;
            let slot = running.slot.read().unwrap_or_else(PoisonError::into_inner);
            slot.clone().ok_or(McpError::Closed)?
        };
        let result = session
            .call_tool(&entry.remote_name, request.arguments.clone())
            .await?;
        if let (Some(schema), Some(structured)) = (&entry.output, &result.structured_content) {
            schema.check_output(structured)?;
        }
        let call_id = format!(
            "{}-{}",
            request.operation,
            self.counter.fetch_add(1, Ordering::Relaxed)
        );
        let external = wrap_result(
            &entry.server,
            &entry.remote_name,
            &call_id,
            &result,
            self.policy.max_result_chars,
            &self.policy.allowed_image_mime,
        );
        self.gate.taint.mark(&request.operation);
        Ok(CallOutput {
            external,
            structured: result.structured_content,
            risk: entry.risk,
        })
    }
}
