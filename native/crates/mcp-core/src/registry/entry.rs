use sha2::{Digest, Sha256};

use crate::error::{McpError, McpResult};
use crate::normalize::canonical_name;
use crate::policy::Risk;
use crate::protocol::ToolSpec;
use crate::schema::CompiledSchema;
use crate::settings::Settings;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ToolState {
    Active,
    Stale,
    Quarantined,
}

#[derive(Debug, Clone)]
pub struct ToolEntry {
    pub id: String,
    pub server: String,
    pub remote_name: String,
    pub spec: ToolSpec,
    pub hash: String,
    pub state: ToolState,
    pub risk: Risk,
    pub input: CompiledSchema,
    pub output: Option<CompiledSchema>,
}

impl ToolState {
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Active => "active",
            Self::Stale => "stale",
            Self::Quarantined => "quarantined",
        }
    }
}

impl ToolEntry {
    pub fn build(server: &str, spec: ToolSpec, settings: &Settings) -> McpResult<Self> {
        let id = canonical_name(server, &spec.name, settings.max_name_len)?;
        let input = CompiledSchema::compile(&spec.input_schema)?;
        let output = spec
            .output_schema
            .as_ref()
            .map(CompiledSchema::compile)
            .transpose()?;
        let bytes = serde_json::to_vec(&spec).map_err(|_| McpError::Serialize)?;
        let hash: String = Sha256::digest(&bytes)
            .iter()
            .flat_map(|b| [b >> 4, b & 15])
            .filter_map(|n| char::from_digit(u32::from(n), 16))
            .collect();
        Ok(Self {
            id,
            server: server.to_owned(),
            remote_name: spec.name.clone(),
            spec,
            hash,
            state: ToolState::Active,
            risk: Risk::Critical,
            input,
            output,
        })
    }

    #[must_use]
    pub fn callable(&self) -> bool {
        self.state == ToolState::Active
    }

    #[must_use]
    pub fn with_risk(mut self, risk: Risk) -> Self {
        self.risk = risk;
        self
    }

    #[must_use]
    pub fn with_state(&self, state: ToolState) -> Self {
        Self {
            state,
            ..self.clone()
        }
    }
}
