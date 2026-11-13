use serde::{Deserialize, Serialize};

use crate::error::{SwarmError, SwarmResult};
use crate::limits::Ceilings;
use crate::wire::ident::valid_token;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Settings {
    pub max_payload_bytes: usize,
    pub max_text_chars: usize,
    pub max_presence: usize,
    pub max_steps: usize,
    pub max_edges: usize,
    pub max_redelegation_depth: usize,
    pub max_workers: usize,
    pub default_worker_kind: String,
    pub default_concurrency: u64,
    pub default_tokens: u64,
    pub default_tool_calls: u64,
    pub default_time_ms: u64,
    pub max_tokens: u64,
    pub max_tool_calls: u64,
    pub max_time_ms: u64,
    pub graph_ref_ttl_ms: u64,
    pub max_evidence: usize,
    pub max_output_bytes: usize,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            max_payload_bytes: 256 * 1024,
            max_text_chars: 16_000,
            max_presence: 16,
            max_steps: 32,
            max_edges: 128,
            max_redelegation_depth: 2,
            max_workers: 16,
            default_worker_kind: "bridge".to_owned(),
            default_concurrency: 1,
            default_tokens: 8_000,
            default_tool_calls: 24,
            default_time_ms: 120_000,
            max_tokens: 200_000,
            max_tool_calls: 200,
            max_time_ms: 1_800_000,
            graph_ref_ttl_ms: 900_000,
            max_evidence: 32,
            max_output_bytes: 256 * 1024,
        }
    }
}

fn within(value: usize, ceiling: usize) -> bool {
    (1..=ceiling).contains(&value)
}

fn within_u64(value: u64, ceiling: u64) -> bool {
    (1..=ceiling).contains(&value)
}

impl Settings {
    pub fn validate(&self) -> SwarmResult<()> {
        let sizes = [
            (self.max_payload_bytes, Ceilings::PAYLOAD_BYTES),
            (self.max_text_chars, Ceilings::TEXT_CHARS),
            (self.max_presence, Ceilings::PRESENCE),
            (self.max_steps, Ceilings::STEPS),
            (self.max_edges, Ceilings::EDGES),
            (self.max_workers, Ceilings::WORKERS),
            (self.max_evidence, Ceilings::EVIDENCE),
            (self.max_output_bytes, Ceilings::OUTPUT_BYTES),
        ];
        let numbers = [
            (self.max_tokens, Ceilings::TOKENS),
            (self.max_tool_calls, Ceilings::TOOL_CALLS),
            (self.max_time_ms, Ceilings::TIME_MS),
            (self.graph_ref_ttl_ms, Ceilings::GRAPH_TTL_MS),
            (self.default_concurrency, Ceilings::WORKERS as u64),
        ];
        let ok = sizes.iter().all(|(v, c)| within(*v, *c))
            && numbers.iter().all(|(v, c)| within_u64(*v, *c))
            && self.max_redelegation_depth <= Ceilings::REDELEGATION_DEPTH
            && within_u64(self.default_tokens, self.max_tokens)
            && within_u64(self.default_tool_calls, self.max_tool_calls)
            && within_u64(self.default_time_ms, self.max_time_ms)
            && self.max_edges >= self.max_steps.saturating_sub(1)
            && self.default_worker_kind.len() <= Ceilings::KIND
            && valid_token(&self.default_worker_kind, Ceilings::KIND);
        if ok {
            Ok(())
        } else {
            Err(SwarmError::Settings)
        }
    }

    pub fn from_json(raw: &str) -> SwarmResult<Self> {
        if raw.len() > Ceilings::PAYLOAD_BYTES {
            return Err(SwarmError::TooLarge);
        }
        let parsed: Self = serde_json::from_str(raw).map_err(|_| SwarmError::Settings)?;
        parsed.validate()?;
        Ok(parsed)
    }
}
