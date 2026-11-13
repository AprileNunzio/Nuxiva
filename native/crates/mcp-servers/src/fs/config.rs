use std::path::{Component, Path};

use serde::{Deserialize, Serialize};

use nuxiva_mcp_core::{McpError, McpResult, valid_server_id};

pub const MAX_ROOTS: usize = 64;
pub const MAX_DEPTH: usize = 64;
pub const MAX_ENTRIES: usize = 1_000_000;
pub const MAX_TEXT: usize = 2_000_000;
pub const MAX_BYTES: u64 = 1 << 30;
pub const MAX_PATH: usize = 4_096;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Mode {
    Read,
    Write,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct RootConfig {
    pub name: String,
    pub path: String,
    pub mode: Mode,
    pub extensions: Vec<String>,
    pub max_bytes: u64,
    pub max_depth: usize,
}

impl Default for RootConfig {
    fn default() -> Self {
        Self {
            name: String::new(),
            path: String::new(),
            mode: Mode::Read,
            extensions: Vec::new(),
            max_bytes: 8 * 1024 * 1024,
            max_depth: 16,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct FsConfig {
    pub roots: Vec<RootConfig>,
    pub default_root: Option<String>,
    pub trash: Option<String>,
    pub denied_names: Vec<String>,
    pub taint_reads: bool,
    pub text_limit: usize,
    pub list_limit: usize,
    pub find_limit: usize,
    pub max_entries: usize,
}

impl Default for FsConfig {
    fn default() -> Self {
        Self {
            roots: Vec::new(),
            default_root: None,
            trash: None,
            denied_names: [
                ".ssh",
                ".gnupg",
                ".git",
                ".env",
                "*.key",
                "*.pem",
                "*.vault",
                "secrets*",
                "credentials*",
                "id_rsa*",
                "id_ed25519*",
            ]
            .iter()
            .map(|n| (*n).to_owned())
            .collect(),
            taint_reads: true,
            text_limit: 8_000,
            list_limit: 200,
            find_limit: 100,
            max_entries: 20_000,
        }
    }
}

fn absolute_clean(path: &str) -> bool {
    let p = Path::new(path);
    p.is_absolute()
        && path.len() <= MAX_PATH
        && !path.contains('\0')
        && p.components().all(|c| !matches!(c, Component::ParentDir))
}

impl FsConfig {
    pub fn from_json(text: &str) -> McpResult<Self> {
        let config: Self = serde_json::from_str(text).map_err(|_| McpError::InvalidSettings)?;
        config.validate()?;
        Ok(config)
    }

    pub fn validate(&self) -> McpResult<()> {
        let limits = [
            self.text_limit <= MAX_TEXT && self.text_limit > 0,
            self.list_limit <= MAX_ENTRIES && self.list_limit > 0,
            self.find_limit <= MAX_ENTRIES && self.find_limit > 0,
            self.max_entries <= MAX_ENTRIES && self.max_entries > 0,
            !self.roots.is_empty() && self.roots.len() <= MAX_ROOTS,
            self.trash.as_deref().is_none_or(absolute_clean),
            self.default_root
                .as_ref()
                .is_none_or(|d| self.roots.iter().any(|r| &r.name == d)),
        ];
        if limits.iter().any(|ok| !ok) {
            return Err(McpError::InvalidSettings);
        }
        let mut names = Vec::new();
        for root in &self.roots {
            let sane = valid_server_id(&root.name)
                && absolute_clean(&root.path)
                && root.max_bytes > 0
                && root.max_bytes <= MAX_BYTES
                && root.max_depth <= MAX_DEPTH
                && root.extensions.len() <= 256
                && !names.contains(&root.name);
            if !sane {
                return Err(McpError::InvalidSettings);
            }
            names.push(root.name.clone());
        }
        Ok(())
    }
}
