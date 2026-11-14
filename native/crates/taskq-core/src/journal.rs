use std::fs::{File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::error::{TaskqError, TaskqResult};
use crate::limits::Ceilings;
use crate::queue::Change;
use crate::spec::TaskState;

const GENESIS: &str = "0000000000000000000000000000000000000000000000000000000000000000";

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Record {
    seq: u64,
    at: u64,
    prev: String,
    change: Change,
    hash: String,
}

fn seal(prev: &str, seq: u64, at: u64, change: &Change) -> TaskqResult<String> {
    let body = serde_json::to_string(change).map_err(|_| TaskqError::Serialize)?;
    let mut hasher = Sha256::new();
    hasher.update(prev.as_bytes());
    hasher.update(seq.to_le_bytes());
    hasher.update(at.to_le_bytes());
    hasher.update(body.as_bytes());
    let digest = hasher.finalize();
    let mut out = String::with_capacity(64);
    for byte in digest {
        out.push(char::from_digit(u32::from(byte >> 4), 16).unwrap_or('0'));
        out.push(char::from_digit(u32::from(byte & 0x0f), 16).unwrap_or('0'));
    }
    Ok(out)
}

pub trait Journal: Send {
    fn append(&mut self, at: u64, changes: &[Change]) -> TaskqResult<()>;
    fn load(&mut self) -> TaskqResult<Vec<Change>>;
    fn compact(&mut self, at: u64, live: &[Change]) -> TaskqResult<()>;
    fn size(&self) -> u64;
    fn soft_limit(&self) -> u64;
}

#[derive(Debug, Default)]
pub struct MemoryJournal {
    changes: Vec<Change>,
}

impl MemoryJournal {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }
}

impl Journal for MemoryJournal {
    fn append(&mut self, _at: u64, changes: &[Change]) -> TaskqResult<()> {
        self.changes.extend_from_slice(changes);
        Ok(())
    }

    fn load(&mut self) -> TaskqResult<Vec<Change>> {
        Ok(self.changes.clone())
    }

    fn compact(&mut self, _at: u64, live: &[Change]) -> TaskqResult<()> {
        self.changes = live.to_vec();
        Ok(())
    }

    fn size(&self) -> u64 {
        u64::try_from(self.changes.len()).unwrap_or(u64::MAX)
    }

    fn soft_limit(&self) -> u64 {
        u64::MAX
    }
}

#[derive(Debug)]
pub struct FileJournal {
    path: PathBuf,
    file: File,
    seq: u64,
    prev: String,
    bytes: u64,
    max_bytes: u64,
    loaded: Vec<Change>,
}

fn open_append(path: &Path) -> TaskqResult<File> {
    let mut options = OpenOptions::new();
    options.create(true).append(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    options.open(path).map_err(|_| TaskqError::Journal)
}

impl FileJournal {
    pub fn open(path: &Path, max_bytes: u64) -> TaskqResult<Self> {
        if max_bytes == 0 || max_bytes > Ceilings::JOURNAL_BYTES {
            return Err(TaskqError::Settings);
        }
        let mut raw = String::new();
        if path.exists() {
            File::open(path)
                .and_then(|mut f| f.read_to_string(&mut raw))
                .map_err(|_| TaskqError::Journal)?;
        }
        let complete = raw.rfind('\n').map_or(0, |i| i.saturating_add(1));
        let torn = complete < raw.len();
        let mut prev = GENESIS.to_owned();
        let mut seq = 0u64;
        let mut loaded = Vec::new();
        for line in raw.get(..complete).unwrap_or_default().lines() {
            let record: Record = serde_json::from_str(line).map_err(|_| TaskqError::Tamper)?;
            if record.seq != seq || record.prev != prev {
                return Err(TaskqError::Tamper);
            }
            if seal(&prev, record.seq, record.at, &record.change)? != record.hash {
                return Err(TaskqError::Tamper);
            }
            prev = record.hash;
            seq = seq.saturating_add(1);
            loaded.push(record.change);
        }
        if torn {
            let keep = u64::try_from(complete).map_err(|_| TaskqError::Journal)?;
            OpenOptions::new()
                .write(true)
                .open(path)
                .and_then(|f| f.set_len(keep))
                .map_err(|_| TaskqError::Journal)?;
        }
        let file = open_append(path)?;
        let bytes = u64::try_from(complete).map_err(|_| TaskqError::Journal)?;
        Ok(Self {
            path: path.to_path_buf(),
            file,
            seq,
            prev,
            bytes,
            max_bytes,
            loaded,
        })
    }

    fn encode(
        at: u64,
        changes: &[Change],
        mut seq: u64,
        mut prev: String,
    ) -> TaskqResult<(String, u64, String)> {
        let mut out = String::new();
        for change in changes {
            let hash = seal(&prev, seq, at, change)?;
            let record = Record {
                seq,
                at,
                prev: prev.clone(),
                change: change.clone(),
                hash: hash.clone(),
            };
            out.push_str(&serde_json::to_string(&record).map_err(|_| TaskqError::Serialize)?);
            out.push('\n');
            prev = hash;
            seq = seq.saturating_add(1);
        }
        Ok((out, seq, prev))
    }
}

impl Journal for FileJournal {
    fn append(&mut self, at: u64, changes: &[Change]) -> TaskqResult<()> {
        if changes.is_empty() {
            return Ok(());
        }
        let (text, seq, prev) = Self::encode(at, changes, self.seq, self.prev.clone())?;
        let added = u64::try_from(text.len()).map_err(|_| TaskqError::Journal)?;
        if self.bytes.saturating_add(added) > self.max_bytes {
            return Err(TaskqError::Full);
        }
        self.file
            .write_all(text.as_bytes())
            .map_err(|_| TaskqError::Journal)?;
        let durable = changes.iter().any(|c| match c {
            Change::State { event } => {
                event.state.is_terminal() || event.state == TaskState::Running
            }
            Change::Submitted { .. } => true,
        });
        if durable {
            self.file.sync_data().map_err(|_| TaskqError::Journal)?;
        }
        self.seq = seq;
        self.prev = prev;
        self.bytes = self.bytes.saturating_add(added);
        Ok(())
    }

    fn load(&mut self) -> TaskqResult<Vec<Change>> {
        Ok(std::mem::take(&mut self.loaded))
    }

    fn compact(&mut self, at: u64, live: &[Change]) -> TaskqResult<()> {
        let (text, seq, prev) = Self::encode(at, live, 0, GENESIS.to_owned())?;
        let tmp = self.path.with_extension("compact");
        let mut options = OpenOptions::new();
        options.create(true).write(true).truncate(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.mode(0o600);
        }
        let mut file = options.open(&tmp).map_err(|_| TaskqError::Journal)?;
        file.write_all(text.as_bytes())
            .map_err(|_| TaskqError::Journal)?;
        file.sync_all().map_err(|_| TaskqError::Journal)?;
        std::fs::rename(&tmp, &self.path).map_err(|_| TaskqError::Journal)?;
        self.file = open_append(&self.path)?;
        self.seq = seq;
        self.prev = prev;
        self.bytes = u64::try_from(text.len()).map_err(|_| TaskqError::Journal)?;
        Ok(())
    }

    fn size(&self) -> u64 {
        self.bytes
    }

    fn soft_limit(&self) -> u64 {
        self.max_bytes / 2
    }
}
