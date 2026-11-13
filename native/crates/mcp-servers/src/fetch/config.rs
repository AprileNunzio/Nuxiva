use serde::{Deserialize, Serialize};

use nuxiva_mcp_core::{McpError, McpResult, NetworkPolicy};

pub const MAX_HOSTS: usize = 1_024;
pub const MAX_TIMEOUT_MS: u64 = 120_000;
pub const MAX_BYTES: usize = 64 * 1024 * 1024;
pub const MAX_TEXT: usize = 2_000_000;
pub const MAX_REDIRECTS: usize = 16;
pub const MAX_AGENT: usize = 128;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct FetchConfig {
    pub hosts: Vec<String>,
    pub network: NetworkPolicy,
    pub allow_insecure: bool,
    pub timeout_ms: u64,
    pub max_bytes: usize,
    pub text_limit: usize,
    pub max_redirects: usize,
    pub user_agent: String,
}

impl Default for FetchConfig {
    fn default() -> Self {
        Self {
            hosts: vec!["*".into()],
            network: NetworkPolicy {
                allow_loopback: false,
                allow_private: false,
                ports: vec![80, 443],
            },
            allow_insecure: false,
            timeout_ms: 20_000,
            max_bytes: 2 * 1024 * 1024,
            text_limit: 5_000,
            max_redirects: 5,
            user_agent: "Nuxiva/3".into(),
        }
    }
}

fn valid_host(entry: &str) -> bool {
    let body = entry.strip_prefix("*.").unwrap_or(entry);
    entry == "*"
        || (!body.is_empty()
            && body.len() <= 253
            && body.bytes().all(|b| {
                b.is_ascii_alphanumeric() || matches!(b, b'-' | b'.' | b':' | b'[' | b']')
            }))
}

impl FetchConfig {
    pub fn validate(&self) -> McpResult<()> {
        let sound = self.hosts.len() <= MAX_HOSTS
            && self.hosts.iter().all(|h| valid_host(h))
            && (1..=MAX_TIMEOUT_MS).contains(&self.timeout_ms)
            && (1..=MAX_BYTES).contains(&self.max_bytes)
            && (1..=MAX_TEXT).contains(&self.text_limit)
            && self.max_redirects <= MAX_REDIRECTS
            && !self.user_agent.is_empty()
            && self.user_agent.len() <= MAX_AGENT
            && self.user_agent.bytes().all(|b| (0x20..0x7f).contains(&b));
        if sound {
            Ok(())
        } else {
            Err(McpError::InvalidSettings)
        }
    }

    #[must_use]
    pub fn allows(&self, host: &str) -> bool {
        let host = host.to_ascii_lowercase();
        self.hosts.iter().any(|entry| {
            let entry = entry.to_ascii_lowercase();
            if entry == "*" {
                return true;
            }
            match entry.strip_prefix("*.") {
                Some(suffix) => host
                    .strip_suffix(suffix)
                    .is_some_and(|rest| rest.ends_with('.')),
                None => host == entry,
            }
        })
    }
}
