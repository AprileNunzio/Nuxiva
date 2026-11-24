use std::fs::{self, OpenOptions};
use std::io::Write;
use std::os::unix::fs::OpenOptionsExt;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::Serialize;

use crate::error::{Error, Result};

pub const RUNTIME_DIR: &str = "/run/nuxiva-screenshot";
pub const REQUEST: &str = "request";
pub const STATUS: &str = "status.json";
const MAX_FIELD: usize = 240;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Status {
    Saved,
    Queued,
    Blocked,
    Failed,
    Disabled,
    NoTarget,
    DeliveredLater,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Report {
    pub id: u64,
    pub at: u64,
    pub status: Status,
    pub name: String,
    pub folder: String,
    pub count: usize,
}

#[derive(Debug)]
pub struct Bridge {
    dir: PathBuf,
    last: u64,
}

fn clip(text: &str) -> String {
    text.chars()
        .filter(|c| !c.is_control())
        .take(MAX_FIELD)
        .collect()
}

fn millis() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| u64::try_from(d.as_millis()).unwrap_or(u64::MAX))
}

impl Bridge {
    #[must_use]
    pub fn new(dir: PathBuf) -> Self {
        Self { dir, last: 0 }
    }

    #[must_use]
    pub fn take_request(&self) -> bool {
        let path = self.dir.join(REQUEST);
        let Ok(meta) = fs::symlink_metadata(&path) else {
            return false;
        };
        let removed = fs::remove_file(&path).is_ok();
        removed && meta.is_file()
    }

    pub fn publish(
        &mut self,
        status: Status,
        name: &str,
        folder: &str,
        count: usize,
    ) -> Result<Report> {
        let id = millis().max(self.last.saturating_add(1));
        self.last = id;
        let report = Report {
            id,
            at: id / 1000,
            status,
            name: clip(name),
            folder: clip(folder),
            count,
        };
        let body = serde_json::to_vec(&report).map_err(|_| Error::Sink("status".into()))?;
        write_atomic(&self.dir, STATUS, &body)?;
        Ok(report)
    }
}

fn write_atomic(dir: &Path, name: &str, data: &[u8]) -> Result<()> {
    let temp = dir.join(format!(".{name}.tmp"));
    let _ = fs::remove_file(&temp);
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o644)
        .open(&temp)?;
    file.write_all(data)?;
    file.sync_all()?;
    drop(file);
    fs::rename(&temp, dir.join(name))?;
    Ok(())
}
