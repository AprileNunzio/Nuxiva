use serde::{Deserialize, Serialize};

use crate::error::{McpError, McpResult};
use crate::limits::Ceilings;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ChangePolicy {
    Compatible,
    Quarantine,
    Accept,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Settings {
    pub max_message_bytes: usize,
    pub max_pages: usize,
    pub max_tools_per_server: usize,
    pub max_tools_total: usize,
    pub max_name_len: usize,
    pub max_description_chars: usize,
    pub max_schema_bytes: usize,
    pub max_schema_depth: usize,
    pub max_schema_nodes: usize,
    pub request_timeout_ms: usize,
    pub max_in_flight: usize,
    pub event_queue: usize,
    pub change_policy: ChangePolicy,
    pub backoff_base_ms: usize,
    pub backoff_max_ms: usize,
    pub backoff_jitter_pct: usize,
    pub stale_retire_ms: usize,
    pub breaker_failures: usize,
    pub breaker_window_ms: usize,
    pub refresh_debounce_ms: usize,
    pub refresh_interval_ms: usize,
    pub foreground_budget_ms: usize,
    pub max_jobs: usize,
    pub job_ttl_ms: usize,
    pub error_queue: usize,
    pub critic_threshold: usize,
    pub critic_window_ms: usize,
    pub pressure_scale_pct: [usize; 4],
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            max_message_bytes: 1024 * 1024,
            max_pages: 50,
            max_tools_per_server: 500,
            max_tools_total: 5_000,
            max_name_len: 64,
            max_description_chars: 1_000,
            max_schema_bytes: 64 * 1024,
            max_schema_depth: 24,
            max_schema_nodes: 20_000,
            request_timeout_ms: 30_000,
            max_in_flight: 64,
            event_queue: 256,
            change_policy: ChangePolicy::Compatible,
            backoff_base_ms: 1_000,
            backoff_max_ms: 300_000,
            backoff_jitter_pct: 20,
            stale_retire_ms: 600_000,
            breaker_failures: 5,
            breaker_window_ms: 60_000,
            refresh_debounce_ms: 200,
            refresh_interval_ms: 300_000,
            foreground_budget_ms: 4_000,
            max_jobs: 64,
            job_ttl_ms: 600_000,
            error_queue: 256,
            critic_threshold: 3,
            critic_window_ms: 60_000,
            pressure_scale_pct: [100, 75, 50, 25],
        }
    }
}

fn within(value: usize, ceiling: usize) -> McpResult<()> {
    if (1..=ceiling).contains(&value) {
        Ok(())
    } else {
        Err(McpError::InvalidSettings)
    }
}

impl Settings {
    pub fn from_json(text: &str) -> McpResult<Self> {
        let settings: Self = serde_json::from_str(text).map_err(|_| McpError::InvalidSettings)?;
        settings.validate()?;
        Ok(settings)
    }

    pub fn for_pressure(&self, level: usize) -> McpResult<Self> {
        let percent = *self
            .pressure_scale_pct
            .get(level.min(3))
            .ok_or(McpError::InvalidSettings)?;
        let scale = |value: usize| (value.saturating_mul(percent) / 100).max(1);
        let mut scaled = self.clone();
        scaled.max_in_flight = scale(self.max_in_flight);
        scaled.max_jobs = scale(self.max_jobs);
        scaled.max_tools_total = scale(self.max_tools_total);
        scaled.event_queue = scale(self.event_queue);
        scaled.error_queue = scale(self.error_queue);
        scaled.max_tools_per_server = scaled.max_tools_per_server.min(scaled.max_tools_total);
        scaled.validate()?;
        Ok(scaled)
    }

    pub fn validate(&self) -> McpResult<()> {
        within(self.max_message_bytes, Ceilings::MESSAGE_BYTES)?;
        within(self.max_pages, Ceilings::PAGES)?;
        within(self.max_tools_per_server, Ceilings::TOOLS_PER_SERVER)?;
        within(self.max_tools_total, Ceilings::TOOLS_TOTAL)?;
        within(self.max_name_len, Ceilings::NAME_LEN)?;
        within(self.max_description_chars, Ceilings::DESCRIPTION_CHARS)?;
        within(self.max_schema_bytes, Ceilings::SCHEMA_BYTES)?;
        within(self.max_schema_depth, Ceilings::SCHEMA_DEPTH)?;
        within(self.max_schema_nodes, Ceilings::SCHEMA_NODES)?;
        within(self.request_timeout_ms, Ceilings::TIMEOUT_MS)?;
        within(self.max_in_flight, Ceilings::IN_FLIGHT)?;
        within(self.event_queue, Ceilings::EVENT_QUEUE)?;
        within(self.backoff_base_ms, Ceilings::LONG_MS)?;
        within(self.backoff_max_ms, Ceilings::LONG_MS)?;
        within(self.stale_retire_ms, Ceilings::LONG_MS)?;
        within(self.breaker_failures, Ceilings::BREAKER_FAILURES)?;
        within(self.breaker_window_ms, Ceilings::LONG_MS)?;
        within(self.refresh_debounce_ms, Ceilings::LONG_MS)?;
        within(self.refresh_interval_ms, Ceilings::LONG_MS)?;
        within(self.foreground_budget_ms, Ceilings::TIMEOUT_MS)?;
        within(self.max_jobs, Ceilings::JOBS)?;
        within(self.job_ttl_ms, Ceilings::LONG_MS)?;
        within(self.error_queue, Ceilings::ERROR_QUEUE)?;
        within(self.critic_threshold, Ceilings::BREAKER_FAILURES)?;
        within(self.critic_window_ms, Ceilings::LONG_MS)?;
        if self
            .pressure_scale_pct
            .iter()
            .any(|p| !(1..=100).contains(p))
        {
            return Err(McpError::InvalidSettings);
        }
        if self.backoff_jitter_pct > 100 || self.backoff_base_ms > self.backoff_max_ms {
            return Err(McpError::InvalidSettings);
        }
        if self.max_tools_per_server > self.max_tools_total {
            return Err(McpError::InvalidSettings);
        }
        Ok(())
    }
}
