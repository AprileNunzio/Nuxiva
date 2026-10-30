use std::env;
use std::path::{Path, PathBuf};

use crate::error::AgencyError;

#[derive(Debug, Clone)]
pub struct Config {
    pub state_dir: PathBuf,
    pub socket: PathBuf,
    pub workspace_root: PathBuf,
    pub allowed_uids: Vec<u32>,
    pub vram_mb: Option<u64>,
}

fn absolute(name: &str, fallback: &str) -> Result<PathBuf, AgencyError> {
    let raw = env::var(name).unwrap_or_else(|_| fallback.to_owned());
    let path = PathBuf::from(raw);
    let clean = path.is_absolute()
        && path
            .components()
            .all(|c| !matches!(c, std::path::Component::ParentDir));
    if clean {
        Ok(path)
    } else {
        Err(AgencyError::Config("paths must be absolute without '..'"))
    }
}

impl Config {
    pub fn from_env() -> Result<Self, AgencyError> {
        let allowed_uids = env::var("NUXIVA_AGENCY_ALLOWED_UIDS")
            .unwrap_or_default()
            .split(',')
            .filter(|s| !s.trim().is_empty())
            .map(|s| s.trim().parse::<u32>())
            .collect::<Result<Vec<_>, _>>()
            .map_err(|_| {
                AgencyError::Config("NUXIVA_AGENCY_ALLOWED_UIDS must list numeric uids")
            })?;
        let vram_mb = match env::var("NUXIVA_AGENCY_VRAM_MB") {
            Ok(raw) => Some(
                raw.trim()
                    .parse::<u64>()
                    .map_err(|_| AgencyError::Config("NUXIVA_AGENCY_VRAM_MB must be a number"))?,
            ),
            Err(_) => None,
        };
        Ok(Self {
            state_dir: absolute("NUXIVA_AGENCY_STATE", "/var/lib/nuxiva/agency")?,
            socket: absolute("NUXIVA_AGENCY_SOCKET", "/run/nuxiva/agency/agency.sock")?,
            workspace_root: absolute(
                "NUXIVA_AGENCY_WORKSPACE",
                "/srv/nuxiva/condivisa/09 Progetti",
            )?,
            allowed_uids,
            vram_mb,
        })
    }

    #[must_use]
    pub fn projects_dir(&self) -> PathBuf {
        self.state_dir.join("projects")
    }

    #[must_use]
    pub fn path(&self, name: &str) -> PathBuf {
        Path::new(&self.state_dir).join(name)
    }
}
