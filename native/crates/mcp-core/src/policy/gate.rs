use std::time::Instant;

use serde_json::{Map, Value};

use super::config::PolicyConfig;
use super::consent::{ConsentKey, ConsentLedger};
use super::rate::RateLimiter;
use super::risk::Risk;
use super::scope::Scope;
use super::taint::TaintLedger;
use crate::audit::hash_value;
use crate::error::{McpError, McpResult};
use crate::registry::ToolEntry;

#[derive(Debug, Clone)]
pub struct CallRequest {
    pub principal: String,
    pub agent: String,
    pub operation: String,
    pub arguments: Map<String, Value>,
    pub consent: Option<String>,
}

#[derive(Debug)]
pub struct Gate {
    config: PolicyConfig,
    pub consent: ConsentLedger,
    pub taint: TaintLedger,
    principals: RateLimiter,
    servers: RateLimiter,
    tools: RateLimiter,
}

impl Gate {
    #[must_use]
    pub fn new(config: PolicyConfig) -> Self {
        let rate = config.rate.clone();
        Self {
            consent: ConsentLedger::new(config.consent_ttl_ms, 4_096),
            taint: TaintLedger::default(),
            principals: RateLimiter::new(rate.per_principal_per_min, rate.max_keys),
            servers: RateLimiter::new(rate.per_server_per_min, rate.max_keys),
            tools: RateLimiter::new(rate.per_tool_per_min, rate.max_keys),
            config,
        }
    }

    #[must_use]
    pub fn consent_key(request: &CallRequest, entry: &ToolEntry) -> ConsentKey {
        ConsentKey {
            operation: request.operation.clone(),
            tool: entry.id.clone(),
            args_hash: hash_value(&Value::Object(request.arguments.clone())),
        }
    }

    #[must_use]
    pub fn needs_consent(&self, risk: Risk, operation: &str) -> bool {
        risk >= self.config.consent_from
            || (risk >= self.config.taint_from && self.taint.is_tainted(operation))
    }

    pub fn check(
        &self,
        request: &CallRequest,
        entry: &ToolEntry,
        scope: &Scope,
        server_max: Risk,
        now: Instant,
    ) -> McpResult<()> {
        if !entry.callable() {
            return Err(McpError::NotCallable);
        }
        let risk = entry.risk;
        if risk > server_max || !scope.permits(&entry.server, &entry.id, risk) {
            return Err(McpError::NotPermitted);
        }
        let allowed = self.principals.allow(&request.principal, now)
            && self.servers.allow(&entry.server, now)
            && self
                .tools
                .allow(&format!("{}\u{0}{}", request.principal, entry.id), now);
        if !allowed {
            return Err(McpError::RateLimited);
        }
        entry.input.check_arguments(&request.arguments)?;
        if self.needs_consent(risk, &request.operation) {
            let token = request
                .consent
                .as_deref()
                .ok_or(McpError::ConsentRequired)?;
            self.consent
                .redeem(token, &Self::consent_key(request, entry), now)?;
        }
        Ok(())
    }
}
