use std::collections::{BTreeMap, BTreeSet};

use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{XChaCha20Poly1305, XNonce};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::error::{GraphError, GraphResult};
use crate::extract::{extract, language};
use crate::graph::Graph;
use crate::model::{Facts, Language};
use crate::path::validate;
use crate::settings::GraphSettings;
use crate::source::FileSource;

const SEAL_AAD: &[u8] = b"nuxiva.graph.cache.v1";
const NONCE_LEN: usize = 24;
const MAX_SEALED: usize = 256 * 1024 * 1024;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Parsed {
    pub facts: Facts,
    pub digest: [u8; 32],
    pub language: Language,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Slot {
    size: u64,
    stamp: u64,
    parsed: Parsed,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct SyncReport {
    pub added: usize,
    pub changed: usize,
    pub removed: usize,
    pub unchanged: usize,
    pub skipped: usize,
}

impl SyncReport {
    #[must_use]
    pub const fn touched(&self) -> bool {
        self.added > 0 || self.changed > 0 || self.removed > 0
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Cache {
    settings: Option<GraphSettings>,
    slots: BTreeMap<String, Slot>,
    skipped: usize,
}

fn parse(source: &dyn FileSource, path: &str, settings: &GraphSettings) -> Option<Parsed> {
    let lang = language(path);
    if lang == Language::Other {
        return Some(Parsed {
            facts: Facts::default(),
            digest: [0; 32],
            language: lang,
        });
    }
    let bytes = source.read(path, settings.max_file_bytes).ok()?;
    let text = std::str::from_utf8(&bytes).ok()?;
    let digest: [u8; 32] = Sha256::digest(&bytes).into();
    Some(Parsed {
        facts: extract(lang, text, settings),
        digest,
        language: lang,
    })
}

impl Cache {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.slots.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.slots.is_empty()
    }

    pub fn sync(
        &mut self,
        source: &dyn FileSource,
        settings: &GraphSettings,
    ) -> GraphResult<SyncReport> {
        settings.validate()?;
        if self.settings.as_ref() != Some(settings) {
            self.slots.clear();
            self.settings = Some(settings.clone());
        }
        let mut report = SyncReport::default();
        let mut listed = BTreeMap::new();
        for entry in source.list()? {
            if validate(&entry.path, settings.max_path_chars).is_err() {
                report.skipped = report.skipped.saturating_add(1);
                continue;
            }
            listed.insert(entry.path, (entry.size, entry.stamp));
        }
        report.skipped = report
            .skipped
            .saturating_add(listed.len().saturating_sub(settings.max_files));
        let keep: BTreeSet<String> = listed.keys().take(settings.max_files).cloned().collect();
        let before = self.slots.len();
        self.slots.retain(|path, _| keep.contains(path));
        report.removed = before.saturating_sub(self.slots.len());
        for path in &keep {
            let Some(&(size, stamp)) = listed.get(path) else {
                continue;
            };
            if self
                .slots
                .get(path)
                .is_some_and(|slot| slot.size == size && slot.stamp == stamp)
            {
                report.unchanged = report.unchanged.saturating_add(1);
                continue;
            }
            let Some(parsed) = parse(source, path, settings) else {
                report.skipped = report.skipped.saturating_add(1);
                if self.slots.remove(path).is_some() {
                    report.removed = report.removed.saturating_add(1);
                }
                continue;
            };
            match self.slots.get_mut(path) {
                Some(slot)
                    if slot.parsed.digest == parsed.digest
                        && slot.parsed.language == parsed.language =>
                {
                    slot.size = size;
                    slot.stamp = stamp;
                    report.unchanged = report.unchanged.saturating_add(1);
                }
                Some(slot) => {
                    *slot = Slot {
                        size,
                        stamp,
                        parsed,
                    };
                    report.changed = report.changed.saturating_add(1);
                }
                None => {
                    self.slots.insert(
                        path.clone(),
                        Slot {
                            size,
                            stamp,
                            parsed,
                        },
                    );
                    report.added = report.added.saturating_add(1);
                }
            }
        }
        self.skipped = report.skipped;
        Ok(report)
    }

    pub fn graph(&self) -> GraphResult<Graph> {
        let paths: Vec<String> = self.slots.keys().cloned().collect();
        let parsed: Vec<Parsed> = self
            .slots
            .values()
            .map(|slot| slot.parsed.clone())
            .collect();
        crate::build::assemble(&paths, &parsed, self.skipped)
    }

    pub fn seal(&self, key: &[u8; 32]) -> GraphResult<Vec<u8>> {
        let plain = serde_json::to_vec(self).map_err(|_| GraphError::Source)?;
        let mut nonce = [0u8; NONCE_LEN];
        getrandom::fill(&mut nonce).map_err(|_| GraphError::Source)?;
        let cipher = XChaCha20Poly1305::new(key.into());
        let body = cipher
            .encrypt(
                XNonce::from_slice(&nonce),
                Payload {
                    msg: &plain,
                    aad: SEAL_AAD,
                },
            )
            .map_err(|_| GraphError::Source)?;
        let mut out = Vec::with_capacity(NONCE_LEN.saturating_add(body.len()));
        out.extend_from_slice(&nonce);
        out.extend_from_slice(&body);
        Ok(out)
    }

    pub fn open(sealed: &[u8], key: &[u8; 32]) -> GraphResult<Self> {
        if sealed.len() > MAX_SEALED {
            return Err(GraphError::TooLarge);
        }
        let (nonce, body) = sealed
            .split_at_checked(NONCE_LEN)
            .ok_or(GraphError::Source)?;
        let cipher = XChaCha20Poly1305::new(key.into());
        let plain = cipher
            .decrypt(
                XNonce::from_slice(nonce),
                Payload {
                    msg: body,
                    aad: SEAL_AAD,
                },
            )
            .map_err(|_| GraphError::Source)?;
        let cache: Self = serde_json::from_slice(&plain).map_err(|_| GraphError::Source)?;
        if let Some(settings) = &cache.settings {
            settings.validate()?;
        }
        Ok(cache)
    }
}
