use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::error::{LoopError, LoopResult};
use crate::paths::{is_protected, normalize};
use crate::settings::Settings;

pub const SCHEMA_VERSION: u32 = 1;

#[must_use]
pub fn hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len().saturating_mul(2));
    for byte in bytes {
        out.push(char::from_digit(u32::from(byte >> 4), 16).unwrap_or('0'));
        out.push(char::from_digit(u32::from(byte & 0x0f), 16).unwrap_or('0'));
    }
    out
}

#[must_use]
pub fn is_digest(text: &str) -> bool {
    text.len() == 64
        && text
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FileEntry {
    pub path: String,
    pub bytes: u64,
    pub digest: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ArtifactDraft {
    pub schema_version: u32,
    pub files: Vec<FileEntry>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Artifact {
    pub schema_version: u32,
    pub files: Vec<FileEntry>,
    pub digest: String,
}

impl Artifact {
    pub fn seal(draft: ArtifactDraft, settings: &Settings) -> LoopResult<Self> {
        if draft.schema_version != SCHEMA_VERSION {
            return Err(LoopError::Version);
        }
        if draft.files.is_empty() || draft.files.len() > settings.max_files {
            return Err(LoopError::Invalid);
        }
        let mut files = Vec::with_capacity(draft.files.len());
        for entry in draft.files {
            let path = normalize(&entry.path)?;
            if is_protected(&path, &settings.protected_prefixes) {
                return Err(LoopError::Protected);
            }
            if !is_digest(&entry.digest) {
                return Err(LoopError::Digest);
            }
            files.push(FileEntry {
                path,
                bytes: entry.bytes,
                digest: entry.digest,
            });
        }
        files.sort_by(|a, b| a.path.cmp(&b.path));
        if files
            .windows(2)
            .any(|w| w.first().map(|f| &f.path) == w.get(1).map(|f| &f.path))
        {
            return Err(LoopError::Invalid);
        }
        let mut hasher = Sha256::new();
        for file in &files {
            hasher.update(file.path.as_bytes());
            hasher.update([0]);
            hasher.update(file.digest.as_bytes());
            hasher.update(b"\n");
        }
        Ok(Self {
            schema_version: SCHEMA_VERSION,
            files,
            digest: hex(&hasher.finalize()),
        })
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Severity {
    Info,
    Low,
    Medium,
    High,
    Critical,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Verdict {
    Pass,
    Fail,
    Inconclusive,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Check {
    pub name: String,
    pub passed: bool,
    pub severity: Severity,
    pub log: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CriticReport {
    pub schema_version: u32,
    pub digest: String,
    pub sandbox_run: String,
    pub checks: Vec<Check>,
    pub verdict: Verdict,
    pub iteration: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Feedback {
    pub iteration: u32,
    pub failed: Vec<String>,
    pub untrusted_log: String,
}

pub fn parse<T: serde::de::DeserializeOwned>(text: &str) -> LoopResult<T> {
    if text.len() > crate::settings::MAX_PAYLOAD {
        return Err(LoopError::TooLarge);
    }
    serde_json::from_str(text).map_err(|_| LoopError::Parse)
}
