use std::fs::OpenOptions;
use std::io::Write;
use std::path::Path;

use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};

use crate::error::{McpError, McpResult};
use crate::policy::Risk;

pub const GENESIS: &str = "0000000000000000000000000000000000000000000000000000000000000000";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Verdict {
    Completed,
    Denied,
    Failed,
    TimedOut,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuditEvent {
    pub ts_ms: u64,
    pub principal: String,
    pub agent: String,
    pub server: String,
    pub tool: String,
    pub risk: Risk,
    pub verdict: Verdict,
    pub duration_ms: u64,
    pub args_hash: String,
    pub response_hash: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuditRecord {
    pub seq: u64,
    pub prev: String,
    pub hash: String,
    pub event: AuditEvent,
}

pub trait AuditSink: Send {
    fn append(&mut self, line: &str) -> McpResult<()>;
}

#[derive(Debug, Default)]
pub struct MemorySink {
    pub lines: Vec<String>,
}

impl AuditSink for MemorySink {
    fn append(&mut self, line: &str) -> McpResult<()> {
        self.lines.push(line.to_owned());
        Ok(())
    }
}

#[derive(Debug)]
pub struct FileSink {
    file: std::fs::File,
}

impl FileSink {
    pub fn open(path: &Path) -> McpResult<Self> {
        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
            .map_err(|_| McpError::Io)?;
        Ok(Self { file })
    }
}

impl AuditSink for FileSink {
    fn append(&mut self, line: &str) -> McpResult<()> {
        self.file
            .write_all(line.as_bytes())
            .and_then(|()| self.file.write_all(b"\n"))
            .and_then(|()| self.file.sync_data())
            .map_err(|_| McpError::Io)
    }
}

#[must_use]
pub fn hash_value(value: &Value) -> String {
    hex(&Sha256::digest(
        serde_json::to_vec(value).unwrap_or_default(),
    ))
}

fn hex(bytes: &[u8]) -> String {
    bytes
        .iter()
        .flat_map(|b| [b >> 4, b & 15])
        .filter_map(|n| char::from_digit(u32::from(n), 16))
        .collect()
}

fn link_hash(seq: u64, prev: &str, event: &AuditEvent) -> McpResult<String> {
    let body = serde_json::to_vec(event).map_err(|_| McpError::Serialize)?;
    let mut hasher = Sha256::new();
    hasher.update(seq.to_be_bytes());
    hasher.update(prev.as_bytes());
    hasher.update(&body);
    Ok(hex(&hasher.finalize()))
}

#[derive(Debug)]
pub struct AuditChain<S: AuditSink> {
    sink: S,
    seq: u64,
    last: String,
}

impl<S: AuditSink> AuditChain<S> {
    pub fn new(sink: S) -> Self {
        Self {
            sink,
            seq: 0,
            last: GENESIS.to_owned(),
        }
    }

    pub fn resume(sink: S, seq: u64, last: String) -> Self {
        Self { sink, seq, last }
    }

    pub fn append(&mut self, event: AuditEvent) -> McpResult<AuditRecord> {
        let seq = self.seq.checked_add(1).ok_or(McpError::ChainBroken)?;
        let hash = link_hash(seq, &self.last, &event)?;
        let record = AuditRecord {
            seq,
            prev: self.last.clone(),
            hash: hash.clone(),
            event,
        };
        let line = serde_json::to_string(&record).map_err(|_| McpError::Serialize)?;
        self.sink.append(&line)?;
        self.seq = seq;
        self.last = hash;
        Ok(record)
    }

    #[must_use]
    pub fn head(&self) -> (u64, &str) {
        (self.seq, &self.last)
    }

    pub fn sink(&self) -> &S {
        &self.sink
    }
}

pub fn verify<'a>(lines: impl IntoIterator<Item = &'a str>) -> McpResult<(u64, String)> {
    let mut seq = 0u64;
    let mut last = GENESIS.to_owned();
    for line in lines {
        let record: AuditRecord = serde_json::from_str(line).map_err(|_| McpError::ChainBroken)?;
        let expected_seq = seq.checked_add(1).ok_or(McpError::ChainBroken)?;
        if record.seq != expected_seq || record.prev != last {
            return Err(McpError::ChainBroken);
        }
        if link_hash(record.seq, &record.prev, &record.event)? != record.hash {
            return Err(McpError::ChainBroken);
        }
        seq = expected_seq;
        last = record.hash;
    }
    Ok((seq, last))
}
