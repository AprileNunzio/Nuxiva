use std::collections::HashMap;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::error::{Error, Result};
use crate::pathguard::{allowed_root, valid_host, valid_share, valid_subdir};

pub const MAX_CONFIG_BYTES: usize = 16_384;
pub const SMB_AUTH_FILE: &str = "/etc/nuxiva/screenshot-smb.cred";
pub const DEFAULT_SUBDIR: &str = "05 Scambio/Screenshot";
pub const DEFAULT_SPOOL: &str = "/var/lib/nuxiva-screenshot/spool";
pub const DEFAULT_GUEST_FLAG: &str = "/run/nuxiva/guests-present";
const MAX_MASKS: usize = 16;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase", deny_unknown_fields)]
pub enum Target {
    None,
    Dir { path: PathBuf },
    Smb { host: String, share: String },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Mask {
    pub x: u16,
    pub y: u16,
    pub w: u16,
    pub h: u16,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Retention {
    pub days: u32,
    pub max_files: u32,
    pub max_bytes: u64,
}

impl Default for Retention {
    fn default() -> Self {
        Self {
            days: 30,
            max_files: 500,
            max_bytes: 2 * 1024 * 1024 * 1024,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
#[allow(clippy::struct_excessive_bools)]
pub struct Config {
    pub enabled: bool,
    pub target: Target,
    pub subdir: String,
    pub masks: Vec<Mask>,
    pub retention: Retention,
    pub block_locked: bool,
    pub block_guests: bool,
    pub notice: bool,
    pub lang: String,
    pub spool: PathBuf,
    pub guest_flag: PathBuf,
    pub smb_auth: PathBuf,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            enabled: false,
            target: Target::None,
            subdir: DEFAULT_SUBDIR.to_owned(),
            masks: Vec::new(),
            retention: Retention::default(),
            block_locked: true,
            block_guests: true,
            notice: true,
            lang: "it".to_owned(),
            spool: PathBuf::from(DEFAULT_SPOOL),
            guest_flag: PathBuf::from(DEFAULT_GUEST_FLAG),
            smb_auth: PathBuf::from(SMB_AUTH_FILE),
        }
    }
}

impl Config {
    pub fn parse(text: &str) -> Result<Self> {
        if text.len() > MAX_CONFIG_BYTES {
            return Err(Error::Config("too_large"));
        }
        let config: Self = serde_json::from_str(text).map_err(|_| Error::Config("malformed"))?;
        config.validate()?;
        Ok(config)
    }

    pub fn validate(&self) -> Result<()> {
        if !valid_subdir(&self.subdir) {
            return Err(Error::Config("subdir"));
        }
        if self.masks.len() > MAX_MASKS || !self.masks.iter().copied().all(valid_mask) {
            return Err(Error::Config("mask"));
        }
        if self.retention.days > 3650
            || self.retention.max_files == 0
            || self.retention.max_files > 100_000
            || self.retention.max_bytes < 1_048_576
        {
            return Err(Error::Config("retention"));
        }
        if !matches!(self.lang.as_str(), "it" | "en" | "fr" | "es") {
            return Err(Error::Config("lang"));
        }
        for path in [&self.spool, &self.guest_flag, &self.smb_auth] {
            if !path.is_absolute() || path.components().any(|c| c.as_os_str() == "..") {
                return Err(Error::Config("path"));
            }
        }
        match &self.target {
            Target::None => Ok(()),
            Target::Dir { path } => {
                if allowed_root(path) {
                    Ok(())
                } else {
                    Err(Error::Config("target_dir"))
                }
            }
            Target::Smb { host, share } => {
                if valid_host(host) && valid_share(share) {
                    Ok(())
                } else {
                    Err(Error::Config("target_smb"))
                }
            }
        }
    }

    #[must_use]
    pub fn active(&self) -> bool {
        self.enabled && self.target != Target::None
    }

    #[must_use]
    pub fn from_settings(settings: &HashMap<String, String>) -> Self {
        let get = |key: &str| settings.get(key).map(|v| v.trim()).unwrap_or_default();
        let flag = |key: &str, default: bool| match get(key) {
            "1" | "true" | "yes" => true,
            "0" | "false" | "no" => false,
            _ => default,
        };
        let mut config = Self {
            enabled: flag("NUXIVA_SCREENSHOT", get("NUXIVA_SHARES") != "0"),
            block_locked: flag("NUXIVA_SCREENSHOT_BLOCK_LOCKED", true),
            block_guests: flag("NUXIVA_SCREENSHOT_BLOCK_GUESTS", true),
            notice: flag("NUXIVA_SCREENSHOT_NOTICE", true),
            target: parse_target(get("NUXIVA_SCREENSHOT_TARGET")),
            masks: parse_masks(get("NUXIVA_SCREENSHOT_MASK")),
            ..Self::default()
        };
        let subdir = get("NUXIVA_SCREENSHOT_SUBDIR");
        if !subdir.is_empty() {
            subdir.clone_into(&mut config.subdir);
        }
        let lang = get("NUXIVA_UI_LANG");
        if matches!(lang, "it" | "en" | "fr" | "es") {
            lang.clone_into(&mut config.lang);
        }
        if let Ok(days) = get("NUXIVA_SCREENSHOT_RETENTION_DAYS").parse::<u32>() {
            config.retention.days = days;
        }
        if let Ok(max) = get("NUXIVA_SCREENSHOT_MAX_FILES").parse::<u32>() {
            config.retention.max_files = max;
        }
        if config.validate().is_err() {
            return Self::default();
        }
        config
    }
}

fn valid_mask(mask: Mask) -> bool {
    mask.w > 0
        && mask.h > 0
        && mask.x.checked_add(mask.w).is_some_and(|v| v <= 1000)
        && mask.y.checked_add(mask.h).is_some_and(|v| v <= 1000)
}

#[must_use]
pub fn parse_target(raw: &str) -> Target {
    if let Some(rest) = raw.strip_prefix("smb://") {
        if let Some((host, share)) = rest.split_once('/') {
            return Target::Smb {
                host: host.to_owned(),
                share: share.trim_end_matches('/').to_owned(),
            };
        }
        return Target::None;
    }
    if raw.is_empty() {
        Target::None
    } else {
        Target::Dir {
            path: Path::new(raw).to_path_buf(),
        }
    }
}

#[must_use]
pub fn parse_masks(raw: &str) -> Vec<Mask> {
    raw.split(';')
        .filter(|item| !item.trim().is_empty())
        .filter_map(|item| {
            let nums: Vec<u16> = item
                .split(',')
                .filter_map(|n| n.trim().parse::<u16>().ok())
                .collect();
            match nums.as_slice() {
                [x, y, w, h] => Some(Mask {
                    x: *x,
                    y: *y,
                    w: *w,
                    h: *h,
                }),
                _ => None,
            }
        })
        .collect()
}

#[must_use]
pub fn parse_env_text(text: &str) -> HashMap<String, String> {
    text.lines()
        .map(str::trim)
        .filter(|l| !l.starts_with('#'))
        .filter_map(|l| l.strip_prefix("export ").or(Some(l)))
        .filter_map(|l| l.split_once('='))
        .filter(|(k, _)| {
            k.starts_with("NUXIVA_SCREENSHOT") || *k == "NUXIVA_UI_LANG" || *k == "NUXIVA_SHARES"
        })
        .map(|(k, v)| {
            let v = v.trim();
            let v = v
                .strip_prefix('"')
                .and_then(|r| r.strip_suffix('"'))
                .or_else(|| v.strip_prefix('\'').and_then(|r| r.strip_suffix('\'')))
                .unwrap_or(v);
            (k.to_owned(), v.to_owned())
        })
        .collect()
}
