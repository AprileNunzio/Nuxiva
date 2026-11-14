use std::fs::{self, DirBuilder};
use std::os::unix::fs::DirBuilderExt;
use std::path::PathBuf;
use std::time::{Duration, Instant};

use crate::error::{Error, Result};
use crate::naming::{is_managed, stamp_secs};
use crate::sink::{Sink, atomic_write};

const BASE_DELAY: u64 = 5;
const MAX_DELAY: u64 = 900;
pub const SPOOL_MAX_BYTES: u64 = 256 * 1024 * 1024;
pub const SPOOL_MAX_FILES: usize = 64;

#[derive(Debug)]
pub struct Spool {
    dir: PathBuf,
}

impl Spool {
    pub fn open(dir: PathBuf) -> Result<Self> {
        if let Ok(meta) = fs::symlink_metadata(&dir) {
            if meta.file_type().is_symlink() || !meta.is_dir() {
                return Err(Error::Path("spool_unsafe"));
            }
        } else {
            DirBuilder::new()
                .recursive(true)
                .mode(0o700)
                .create(&dir)
                .map_err(Error::Io)?;
        }
        Ok(Self { dir })
    }

    #[must_use]
    pub fn pending(&self) -> Vec<(String, u64)> {
        let Ok(entries) = fs::read_dir(&self.dir) else {
            return Vec::new();
        };
        let mut items: Vec<(String, u64)> = entries
            .filter_map(std::result::Result::ok)
            .filter_map(|e| {
                let name = e.file_name().into_string().ok()?;
                is_managed(&name).then_some(())?;
                let meta = fs::symlink_metadata(e.path()).ok()?;
                meta.is_file().then_some((name, meta.len()))
            })
            .collect();
        items.sort_by_key(|(name, _)| stamp_secs(name).unwrap_or(0));
        items
    }

    pub fn enqueue(&self, name: &str, data: &[u8]) -> Result<()> {
        let incoming = u64::try_from(data.len()).unwrap_or(u64::MAX);
        if incoming > SPOOL_MAX_BYTES {
            return Err(Error::Sink("spool_item_too_large".into()));
        }
        loop {
            let items = self.pending();
            let total: u64 = items.iter().map(|(_, s)| *s).sum();
            if items.len() < SPOOL_MAX_FILES && total.saturating_add(incoming) <= SPOOL_MAX_BYTES {
                break;
            }
            match items.first() {
                Some((oldest, _)) => self.discard(oldest),
                None => break,
            }
        }
        atomic_write(&self.dir, name, data, 0o600)
    }

    pub fn read(&self, name: &str) -> Result<Vec<u8>> {
        if !is_managed(name) {
            return Err(Error::Path("name"));
        }
        fs::read(self.dir.join(name)).map_err(Error::Io)
    }

    pub fn discard(&self, name: &str) {
        if is_managed(name) {
            let _ = fs::remove_file(self.dir.join(name));
        }
    }
}

#[derive(Debug)]
pub struct Backoff {
    failures: u32,
    next: Option<Instant>,
}

impl Default for Backoff {
    fn default() -> Self {
        Self::new()
    }
}

impl Backoff {
    #[must_use]
    pub const fn new() -> Self {
        Self {
            failures: 0,
            next: None,
        }
    }

    #[must_use]
    pub fn delay(failures: u32) -> Duration {
        let factor = 1u64.checked_shl(failures.min(20)).unwrap_or(u64::MAX);
        Duration::from_secs(BASE_DELAY.saturating_mul(factor).min(MAX_DELAY))
    }

    #[must_use]
    pub fn ready(&self, now: Instant) -> bool {
        self.next.is_none_or(|t| now >= t)
    }

    pub fn failed(&mut self, now: Instant) {
        self.failures = self.failures.saturating_add(1);
        self.next = now.checked_add(Self::delay(self.failures.saturating_sub(1)));
    }

    pub fn succeeded(&mut self) {
        self.failures = 0;
        self.next = None;
    }

    #[must_use]
    pub const fn failures(&self) -> u32 {
        self.failures
    }
}

#[derive(Debug, Default, PartialEq, Eq)]
pub struct Flush {
    pub delivered: usize,
    pub failed: bool,
}

pub fn flush(spool: &Spool, sink: &dyn Sink, backoff: &mut Backoff, now: Instant) -> Flush {
    let mut report = Flush::default();
    if !backoff.ready(now) {
        return report;
    }
    for (name, _) in spool.pending() {
        let Ok(data) = spool.read(&name) else {
            spool.discard(&name);
            continue;
        };
        match sink.put(&name, &data) {
            Ok(()) => {
                spool.discard(&name);
                report.delivered = report.delivered.saturating_add(1);
                backoff.succeeded();
            }
            Err(Error::Sink(reason)) if reason == "exists" => {
                spool.discard(&name);
                backoff.succeeded();
            }
            Err(_) => {
                backoff.failed(now);
                report.failed = true;
                break;
            }
        }
    }
    report
}
