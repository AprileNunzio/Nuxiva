#![allow(clippy::cast_precision_loss, clippy::arithmetic_side_effects)]

use std::collections::{BTreeMap, HashMap};

use hmac::{Hmac, Mac};
use serde::{Deserialize, Serialize};
use sha2::Sha256;

use crate::error::{NvrError, NvrResult};

pub const MAX_DOCS: usize = 2_000_000;
pub const MAX_TOKENS: usize = 512;
pub const MAX_QUERY_TOKENS: usize = 12;
pub const MIN_TOKEN: usize = 2;
pub const MIN_PREFIX: usize = 4;
pub const MAX_PREFIX: usize = 12;
pub const MAX_TEXT: usize = 16_000;

#[must_use]
pub fn fold_char(c: char) -> Option<char> {
    let lower = c.to_lowercase().next().unwrap_or(c);
    let base = match lower {
        'à' | 'á' | 'â' | 'ä' | 'ã' | 'å' => 'a',
        'è' | 'é' | 'ê' | 'ë' => 'e',
        'ì' | 'í' | 'î' | 'ï' => 'i',
        'ò' | 'ó' | 'ô' | 'ö' | 'õ' => 'o',
        'ù' | 'ú' | 'û' | 'ü' => 'u',
        'ç' => 'c',
        'ñ' => 'n',
        other => other,
    };
    if base.is_ascii_alphanumeric() {
        Some(base)
    } else {
        Some(' ')
    }
}

#[must_use]
pub fn tokens(text: &str) -> Vec<String> {
    let folded: String = text.chars().filter_map(fold_char).collect();
    folded
        .split_whitespace()
        .filter(|t| t.len() >= MIN_TOKEN)
        .take(MAX_TOKENS)
        .map(str::to_owned)
        .collect()
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DocMeta {
    pub key: String,
    pub camera: String,
    pub at_ms: u64,
    pub kind: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Hit {
    pub key: String,
    pub camera: String,
    pub at_ms: u64,
    pub kind: String,
    pub score: f64,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
struct Stored {
    docs: Vec<Option<DocMeta>>,
    postings: BTreeMap<String, Vec<(u32, u16)>>,
}

#[derive(Debug, Clone)]
pub struct BlindIndex {
    key: [u8; 32],
    docs: Vec<Option<DocMeta>>,
    by_key: HashMap<String, u32>,
    postings: BTreeMap<String, Vec<(u32, u16)>>,
}

fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write;
    bytes
        .iter()
        .fold(String::with_capacity(bytes.len() * 2), |mut out, b| {
            let _ = write!(out, "{b:02x}");
            out
        })
}

impl BlindIndex {
    #[must_use]
    pub fn new(key: [u8; 32]) -> Self {
        Self {
            key,
            docs: Vec::new(),
            by_key: HashMap::new(),
            postings: BTreeMap::new(),
        }
    }

    fn blind(&self, label: &str, token: &str) -> String {
        let Ok(mut mac) = Hmac::<Sha256>::new_from_slice(&self.key) else {
            return String::new();
        };
        mac.update(label.as_bytes());
        mac.update(token.as_bytes());
        let out = mac.finalize().into_bytes();
        hex(out.get(..16).unwrap_or_default())
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.by_key.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.by_key.is_empty()
    }

    fn grams(&self, text: &str) -> BTreeMap<String, u16> {
        let mut out: BTreeMap<String, u16> = BTreeMap::new();
        for token in tokens(text) {
            let exact = self.blind("t:", &token);
            let slot = out.entry(exact).or_insert(0);
            *slot = slot.saturating_add(1);
            let chars: Vec<char> = token.chars().collect();
            for n in MIN_PREFIX..chars.len().min(MAX_PREFIX.saturating_add(1)) {
                let prefix: String = chars.iter().take(n).collect();
                out.entry(self.blind("p:", &prefix)).or_insert(1);
            }
        }
        out
    }

    pub fn add(&mut self, meta: DocMeta, text: &str) -> NvrResult<()> {
        if text.len() > MAX_TEXT || meta.key.is_empty() || meta.key.len() > 200 {
            return Err(NvrError::InvalidSegment);
        }
        self.remove(&meta.key);
        if self.by_key.len() >= MAX_DOCS {
            return Err(NvrError::TooMany);
        }
        let id = u32::try_from(self.docs.len()).map_err(|_| NvrError::TooMany)?;
        for (gram, tf) in self.grams(text) {
            self.postings.entry(gram).or_default().push((id, tf));
        }
        self.by_key.insert(meta.key.clone(), id);
        self.docs.push(Some(meta));
        Ok(())
    }

    pub fn remove(&mut self, key: &str) -> bool {
        let Some(id) = self.by_key.remove(key) else {
            return false;
        };
        if let Some(slot) = self.docs.get_mut(id as usize) {
            *slot = None;
        }
        self.postings.retain(|_, list| {
            list.retain(|(doc, _)| *doc != id);
            !list.is_empty()
        });
        true
    }

    pub fn remove_prefix(&mut self, prefix: &str) -> usize {
        let keys: Vec<String> = self
            .by_key
            .keys()
            .filter(|k| k.starts_with(prefix))
            .cloned()
            .collect();
        let gone: std::collections::HashSet<u32> =
            keys.iter().filter_map(|k| self.by_key.remove(k)).collect();
        for id in &gone {
            if let Some(slot) = self.docs.get_mut(*id as usize) {
                *slot = None;
            }
        }
        if !gone.is_empty() {
            self.postings.retain(|_, list| {
                list.retain(|(doc, _)| !gone.contains(doc));
                !list.is_empty()
            });
        }
        gone.len()
    }

    #[must_use]
    pub fn search(
        &self,
        query: &str,
        camera: Option<&str>,
        from_ms: u64,
        to_ms: u64,
        limit: usize,
    ) -> Vec<Hit> {
        let terms: Vec<String> = tokens(query).into_iter().take(MAX_QUERY_TOKENS).collect();
        if terms.is_empty() || limit == 0 {
            return Vec::new();
        }
        let total = self.by_key.len().max(1) as f64;
        let mut scores: HashMap<u32, (f64, usize)> = HashMap::new();
        for term in &terms {
            let mut matched: HashMap<u32, u16> = HashMap::new();
            let label = if term.chars().count() >= MIN_PREFIX {
                vec!["t:", "p:"]
            } else {
                vec!["t:"]
            };
            for l in label {
                for (doc, tf) in self
                    .postings
                    .get(&self.blind(l, term))
                    .map_or(&[][..], Vec::as_slice)
                {
                    let slot = matched.entry(*doc).or_insert(0);
                    *slot = (*slot).max(*tf);
                }
            }
            let idf = (1.0 + total / matched.len().max(1) as f64).ln();
            for (doc, tf) in matched {
                let entry = scores.entry(doc).or_insert((0.0, 0));
                entry.0 += idf * (1.0 + f64::from(tf).ln());
                entry.1 = entry.1.saturating_add(1);
            }
        }
        let mut hits: Vec<Hit> = scores
            .into_iter()
            .filter(|(_, (_, n))| *n == terms.len())
            .filter_map(|(doc, (score, _))| {
                let meta = self.docs.get(doc as usize)?.as_ref()?;
                let in_window = meta.at_ms >= from_ms && meta.at_ms < to_ms;
                let cam_ok = camera.is_none_or(|c| c == meta.camera);
                (in_window && cam_ok).then(|| Hit {
                    key: meta.key.clone(),
                    camera: meta.camera.clone(),
                    at_ms: meta.at_ms,
                    kind: meta.kind.clone(),
                    score: (score * 1e6).round() / 1e6,
                })
            })
            .collect();
        hits.sort_by(|a, b| {
            b.score
                .total_cmp(&a.score)
                .then(b.at_ms.cmp(&a.at_ms))
                .then(a.key.cmp(&b.key))
        });
        hits.truncate(limit);
        hits
    }

    pub fn to_json(&self) -> NvrResult<String> {
        let stored = Stored {
            docs: self.docs.clone(),
            postings: self.postings.clone(),
        };
        serde_json::to_string(&stored).map_err(|e| NvrError::Serialization(e.to_string()))
    }

    pub fn from_json(key: [u8; 32], text: &str) -> NvrResult<Self> {
        let stored: Stored =
            serde_json::from_str(text).map_err(|e| NvrError::Serialization(e.to_string()))?;
        if stored.docs.len() > MAX_DOCS {
            return Err(NvrError::TooMany);
        }
        let mut by_key = HashMap::new();
        for (i, doc) in stored.docs.iter().enumerate() {
            if let Some(d) = doc {
                by_key.insert(
                    d.key.clone(),
                    u32::try_from(i).map_err(|_| NvrError::TooMany)?,
                );
            }
        }
        Ok(Self {
            key,
            docs: stored.docs,
            by_key,
            postings: stored.postings,
        })
    }
}
