use std::env;
use std::path::{Component, PathBuf};

use crate::error::DisplayError;

#[derive(Debug, Clone)]
pub struct Config {
    pub socket: PathBuf,
    pub allowed_uids: Vec<u32>,
}

impl Config {
    pub fn from_env() -> Result<Self, DisplayError> {
        let raw = env::var("NUXIVA_DISPLAY_SOCKET")
            .unwrap_or_else(|_| "/run/nuxiva/display/display.sock".to_owned());
        let socket = PathBuf::from(raw);
        if !socket.is_absolute()
            || socket
                .components()
                .any(|c| matches!(c, Component::ParentDir))
        {
            return Err(DisplayError::Config(
                "NUXIVA_DISPLAY_SOCKET must be absolute without '..'",
            ));
        }
        let allowed_uids = env::var("NUXIVA_DISPLAY_ALLOWED_UIDS")
            .unwrap_or_default()
            .split(',')
            .filter(|s| !s.trim().is_empty())
            .map(|s| s.trim().parse::<u32>())
            .collect::<Result<Vec<_>, _>>()
            .map_err(|_| {
                DisplayError::Config("NUXIVA_DISPLAY_ALLOWED_UIDS must list numeric uids")
            })?;
        Ok(Self {
            socket,
            allowed_uids,
        })
    }
}
