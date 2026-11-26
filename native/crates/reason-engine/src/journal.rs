use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};

use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{XChaCha20Poly1305, XNonce};
use reason_exec::{ExecError, ExecResult, Journal, Record};
use serde::{Deserialize, Serialize};
use zeroize::Zeroizing;

pub const NONCE_LEN: usize = 24;
pub const MAX_JOURNAL_BYTES: u64 = 32 * 1024 * 1024;
pub const MAX_LINE_BYTES: usize = 160 * 1024;
const AAD: &[u8] = b"nuxiva.reason.journal.v1";

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Line {
    k: String,
    r: u8,
    #[serde(default)]
    o: String,
}

pub struct SealedJournal {
    path: PathBuf,
    cipher: XChaCha20Poly1305,
    last: BTreeMap<String, Record>,
    lines: usize,
    limit: usize,
}

impl std::fmt::Debug for SealedJournal {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SealedJournal")
            .field("keys", &self.last.len())
            .field("lines", &self.lines)
            .finish_non_exhaustive()
    }
}

fn io<T, E>(result: Result<T, E>) -> ExecResult<T> {
    result.map_err(|_| ExecError::Journal("io"))
}

fn key_ok(key: &str) -> bool {
    key.len() == 64 && key.bytes().all(|b| b.is_ascii_hexdigit())
}

fn encode(record: &Record) -> (u8, String) {
    match record {
        Record::Started => (0, String::new()),
        Record::Succeeded(out) => (1, out.clone()),
        Record::Failed => (2, String::new()),
    }
}

fn decode(code: u8, out: String) -> Option<Record> {
    match code {
        0 => Some(Record::Started),
        1 => Some(Record::Succeeded(out)),
        2 => Some(Record::Failed),
        _ => None,
    }
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().fold(
        String::with_capacity(bytes.len().saturating_mul(2)),
        |mut out, b| {
            let _ = write!(out, "{b:02x}");
            out
        },
    )
}

fn unhex(text: &str) -> Option<Vec<u8>> {
    if text.len() % 2 != 0 {
        return None;
    }
    (0..text.len())
        .step_by(2)
        .map(|i| {
            text.get(i..i.saturating_add(2))
                .and_then(|p| u8::from_str_radix(p, 16).ok())
        })
        .collect()
}

impl SealedJournal {
    pub fn open(path: &Path, key: [u8; 32], limit: usize) -> ExecResult<Self> {
        let key = Zeroizing::new(key);
        let cipher = XChaCha20Poly1305::new(key.as_ref().into());
        let mut journal = Self {
            path: path.to_path_buf(),
            cipher,
            last: BTreeMap::new(),
            lines: 0,
            limit: limit.max(16),
        };
        if path.exists() {
            journal.load()?;
        }
        Ok(journal)
    }

    #[must_use]
    pub fn keys(&self) -> usize {
        self.last.len()
    }

    fn load(&mut self) -> ExecResult<()> {
        let file = io(File::open(&self.path))?;
        let reader = BufReader::new(file.take(MAX_JOURNAL_BYTES));
        for line in reader.lines() {
            let line = io(line)?;
            if line.len() > MAX_LINE_BYTES {
                return Err(ExecError::Journal("corrupt"));
            }
            let (key, record) = self.open_line(&line)?;
            self.last.insert(key, record);
            self.lines = self.lines.saturating_add(1);
        }
        Ok(())
    }

    fn open_line(&self, line: &str) -> ExecResult<(String, Record)> {
        let (nonce, data) = line.split_once(':').ok_or(ExecError::Journal("corrupt"))?;
        let nonce = unhex(nonce)
            .filter(|n| n.len() == NONCE_LEN)
            .ok_or(ExecError::Journal("corrupt"))?;
        let data = unhex(data).ok_or(ExecError::Journal("corrupt"))?;
        let plain = Zeroizing::new(
            self.cipher
                .decrypt(
                    XNonce::from_slice(&nonce),
                    Payload {
                        msg: &data,
                        aad: AAD,
                    },
                )
                .map_err(|_| ExecError::Journal("tampered"))?,
        );
        let parsed: Line =
            serde_json::from_slice(&plain).map_err(|_| ExecError::Journal("corrupt"))?;
        if !key_ok(&parsed.k) {
            return Err(ExecError::Journal("corrupt"));
        }
        let record = decode(parsed.r, parsed.o).ok_or(ExecError::Journal("corrupt"))?;
        Ok((parsed.k, record))
    }

    fn seal_line(&self, key: &str, record: &Record) -> ExecResult<String> {
        let (r, o) = encode(record);
        let plain = Zeroizing::new(
            serde_json::to_vec(&Line {
                k: key.to_owned(),
                r,
                o,
            })
            .map_err(|_| ExecError::Journal("encode"))?,
        );
        let mut nonce = [0_u8; NONCE_LEN];
        getrandom::fill(&mut nonce).map_err(|_| ExecError::Journal("random"))?;
        let data = self
            .cipher
            .encrypt(
                XNonce::from_slice(&nonce),
                Payload {
                    msg: &plain,
                    aad: AAD,
                },
            )
            .map_err(|_| ExecError::Journal("seal"))?;
        Ok(format!("{}:{}\n", hex(&nonce), hex(&data)))
    }

    fn options() -> OpenOptions {
        let mut options = OpenOptions::new();
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.mode(0o600);
        }
        options
    }

    fn compact(&mut self) -> ExecResult<()> {
        let temp = self.path.with_extension("compact");
        let mut out = String::new();
        let mut kept = 0usize;
        for (key, record) in &self.last {
            if matches!(record, Record::Failed) {
                continue;
            }
            out.push_str(&self.seal_line(key, record)?);
            kept = kept.saturating_add(1);
        }
        let mut file = io(Self::options()
            .write(true)
            .create(true)
            .truncate(true)
            .open(&temp))?;
        io(file.write_all(out.as_bytes()))?;
        io(file.sync_all())?;
        io(fs::rename(&temp, &self.path))?;
        self.last.retain(|_, r| !matches!(r, Record::Failed));
        self.lines = kept;
        if self.lines >= self.limit {
            return Err(ExecError::Journal("full"));
        }
        Ok(())
    }
}

impl Journal for SealedJournal {
    fn append(&mut self, key: &str, record: Record) -> ExecResult<()> {
        if !key_ok(key) {
            return Err(ExecError::Journal("key"));
        }
        if self.lines >= self.limit {
            self.compact()?;
        }
        let line = self.seal_line(key, &record)?;
        let mut file = io(Self::options().append(true).create(true).open(&self.path))?;
        io(file.write_all(line.as_bytes()))?;
        io(file.sync_data())?;
        self.lines = self.lines.saturating_add(1);
        self.last.insert(key.to_owned(), record);
        Ok(())
    }

    fn last(&self, key: &str) -> Option<&Record> {
        self.last.get(key)
    }
}
