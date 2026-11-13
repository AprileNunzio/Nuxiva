use std::collections::{BTreeMap, HashSet};

use serde::{Deserialize, Serialize};

use crate::error::{McpError, McpResult};
use crate::guard::{NetworkPolicy, parse_target};
use crate::normalize::valid_server_id;
use crate::policy::Risk;

pub const MAX_SERVERS: usize = 1_024;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Isolation {
    Internal,
    Sandboxed,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum TransportSpec {
    Stdio {
        program: String,
        args: Vec<String>,
        env: BTreeMap<String, String>,
        secret_env: BTreeMap<String, String>,
        isolation: Isolation,
    },
    Http {
        url: String,
        secret: Option<String>,
        network: Option<NetworkPolicy>,
    },
    Internal {
        name: String,
    },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ServerEntry {
    pub id: String,
    pub enabled: bool,
    pub max_risk: Risk,
    pub honor_read_only: bool,
    pub transport: TransportSpec,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Catalog {
    pub version: u32,
    pub serial: u64,
    pub issued_at: u64,
    pub not_after: u64,
    pub servers: Vec<ServerEntry>,
}

fn env_name_ok(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= 64
        && name
            .chars()
            .all(|c| c.is_ascii_uppercase() || c.is_ascii_digit() || c == '_')
}

impl ServerEntry {
    pub fn validate(&self) -> McpResult<()> {
        if !valid_server_id(&self.id) {
            return Err(McpError::InvalidName);
        }
        match &self.transport {
            TransportSpec::Stdio {
                program,
                args,
                env,
                secret_env,
                ..
            } => {
                let absolute = program.starts_with('/') && !program.contains("..");
                let clean = args.len() <= 64
                    && args.iter().all(|a| a.len() <= 4_096 && !a.contains('\0'))
                    && env.len() <= 64
                    && env.keys().chain(secret_env.keys()).all(|k| env_name_ok(k));
                if absolute && clean && program.len() <= 4_096 {
                    Ok(())
                } else {
                    Err(McpError::InvalidSettings)
                }
            }
            TransportSpec::Http { url, .. } => parse_target(url).map(|_| ()),
            TransportSpec::Internal { name } => {
                if valid_server_id(name) {
                    Ok(())
                } else {
                    Err(McpError::InvalidName)
                }
            }
        }
    }
}

impl Catalog {
    pub fn validate(&self) -> McpResult<()> {
        if self.version != 1 || self.servers.len() > MAX_SERVERS || self.not_after < self.issued_at
        {
            return Err(McpError::InvalidSettings);
        }
        let mut seen = HashSet::new();
        for server in &self.servers {
            server.validate()?;
            if !seen.insert(server.id.as_str()) {
                return Err(McpError::InvalidSettings);
            }
        }
        Ok(())
    }
}
