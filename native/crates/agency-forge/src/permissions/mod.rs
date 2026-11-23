mod scope;

use serde::{Deserialize, Serialize};

use crate::error::ForgeError;
pub use scope::{normalize_host, normalize_path};

pub const MAX_SCOPES: usize = 16;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Access<'a> {
    Read(&'a str),
    Write(&'a str),
    Network(&'a str),
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ToolPermissions {
    #[serde(default)]
    pub read_paths: Vec<String>,
    #[serde(default)]
    pub write_paths: Vec<String>,
    #[serde(default)]
    pub network_hosts: Vec<String>,
}

impl ToolPermissions {
    pub fn normalized(&self) -> Result<Self, ForgeError> {
        let total = self
            .read_paths
            .len()
            .saturating_add(self.write_paths.len())
            .saturating_add(self.network_hosts.len());
        if total > MAX_SCOPES {
            return Err(ForgeError::InvalidPermissions(
                "too many permission scopes".to_owned(),
            ));
        }
        Ok(Self {
            read_paths: self
                .read_paths
                .iter()
                .map(|p| normalize_path(p))
                .collect::<Result<_, _>>()?,
            write_paths: self
                .write_paths
                .iter()
                .map(|p| normalize_path(p))
                .collect::<Result<_, _>>()?,
            network_hosts: self
                .network_hosts
                .iter()
                .map(|h| normalize_host(h))
                .collect::<Result<_, _>>()?,
        })
    }

    #[must_use]
    pub fn allows(&self, access: Access<'_>) -> bool {
        match access {
            Access::Read(path) => within(&self.read_paths, path) || within(&self.write_paths, path),
            Access::Write(path) => within(&self.write_paths, path),
            Access::Network(host) => {
                normalize_host(host).is_ok_and(|host| self.network_hosts.contains(&host))
            }
        }
    }
}

fn within(scopes: &[String], path: &str) -> bool {
    let Ok(path) = normalize_path(path) else {
        return false;
    };
    scopes.iter().any(|scope| {
        path == *scope
            || path
                .strip_prefix(scope.as_str())
                .is_some_and(|rest| rest.starts_with('/'))
    })
}

#[cfg(test)]
mod tests;
