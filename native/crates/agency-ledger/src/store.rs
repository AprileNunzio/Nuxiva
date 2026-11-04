use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Read, Write};
use std::path::Path;

use serde_json::Value;

use crate::chain::{Chain, MAX_PAYLOAD};
use crate::entry::Entry;
use crate::error::LedgerError;
use crate::key::LedgerKey;

const MAX_LINE: usize = MAX_PAYLOAD.saturating_mul(2);

#[derive(Debug)]
pub struct LedgerStore {
    file: File,
    chain: Chain,
    poisoned: bool,
}

fn open_options() -> OpenOptions {
    let mut options = OpenOptions::new();
    options.create(true).read(true).append(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        let nofollow = i32::try_from(rustix::fs::OFlags::NOFOLLOW.bits()).unwrap_or(0);
        options.mode(0o600).custom_flags(nofollow);
    }
    options
}

impl LedgerStore {
    pub fn open(path: &Path, key: LedgerKey) -> Result<Self, LedgerError> {
        let file = open_options().open(path)?;
        let mut chain = Chain::new(key);
        let mut reader = BufReader::new(&file);
        let mut line = String::new();
        let mut number = 0u64;
        loop {
            line.clear();
            let limit = u64::try_from(MAX_LINE).unwrap_or(u64::MAX);
            let read = (&mut reader).take(limit).read_line(&mut line)?;
            if read == 0 {
                break;
            }
            number = number.saturating_add(1);
            if !line.ends_with('\n') {
                return Err(LedgerError::Malformed(number));
            }
            let entry: Entry = serde_json::from_str(line.trim_end())
                .map_err(|_| LedgerError::Malformed(number))?;
            chain.accept(&entry)?;
        }
        Ok(Self {
            file,
            chain,
            poisoned: false,
        })
    }

    #[must_use]
    pub fn chain(&self) -> &Chain {
        &self.chain
    }

    pub fn append(&mut self, kind: &str, payload: Value, at_ms: u64) -> Result<Entry, LedgerError> {
        if self.poisoned {
            return Err(LedgerError::Poisoned);
        }
        let entry = self.chain.seal(kind, payload, at_ms)?;
        let mut line = serde_json::to_vec(&entry)?;
        line.push(b'\n');
        let written = self
            .file
            .write_all(&line)
            .and_then(|()| self.file.sync_data());
        if let Err(error) = written {
            self.poisoned = true;
            return Err(error.into());
        }
        Ok(entry)
    }
}
