use std::collections::HashMap;
use std::time::Instant;

use serde::Serialize;
use thiserror::Error;

use crate::scan::{Limits, ScanError, scan};
use crate::search::Hit;

const MAX_TERMS_PER_FILE: usize = 64;

#[derive(Debug, Error, PartialEq, Eq)]
pub enum IndexError {
    #[error("file limit reached: {0}")]
    FileLimit(usize),
    #[error("memory limit reached: {0} bytes")]
    MemoryLimit(usize),
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize)]
pub struct SyncStats {
    pub added: usize,
    pub updated: usize,
    pub removed: usize,
    pub unchanged: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct CorpusMetrics {
    pub file_count: usize,
    pub memory_bytes: usize,
    pub search_latency_micros: u64,
    pub update_latency_micros: u64,
}

#[derive(Debug, Clone)]
struct IndexedDoc {
    path: String,
    bytes: u64,
    mtime_ms: u64,
    active: bool,
}

#[derive(Debug, Clone)]
pub struct CodeIndex {
    max_files: usize,
    max_memory_bytes: usize,
    docs: Vec<IndexedDoc>,
    paths: HashMap<String, u32>,
    postings: HashMap<String, Vec<u32>>,
    estimated_memory: usize,
}

impl CodeIndex {
    #[must_use]
    pub fn new(max_files: usize, max_memory_bytes: usize) -> Self {
        Self {
            max_files,
            max_memory_bytes,
            docs: Vec::new(),
            paths: HashMap::new(),
            postings: HashMap::new(),
            estimated_memory: std::mem::size_of::<Self>(),
        }
    }

    #[must_use]
    pub fn file_count(&self) -> usize {
        self.paths.len()
    }

    #[must_use]
    pub fn estimated_memory_bytes(&self) -> usize {
        self.estimated_memory
    }

    fn terms_from_content(content: &str, path: &str) -> Vec<String> {
        let mut terms = Vec::new();
        for word in path.split(|c: char| !(c.is_alphanumeric() || c == '_')) {
            if word.len() >= 2 {
                terms.push(word.to_lowercase());
            }
        }
        for word in content.split(|c: char| !(c.is_alphanumeric() || c == '_')) {
            if word.len() >= 2 {
                terms.push(word.to_lowercase());
                if terms.len() >= MAX_TERMS_PER_FILE {
                    break;
                }
            }
        }
        terms.sort();
        terms.dedup();
        terms
    }

    pub fn insert_or_update(
        &mut self,
        path: &str,
        mtime_ms: u64,
        bytes: u64,
        content: Option<&str>,
    ) -> Result<bool, IndexError> {
        if let Some(&doc_id) = self.paths.get(path) {
            let doc = self
                .docs
                .get_mut(doc_id as usize)
                .ok_or(IndexError::FileLimit(self.max_files))?;
            if doc.mtime_ms == mtime_ms && doc.bytes == bytes {
                return Ok(false);
            }
            doc.mtime_ms = mtime_ms;
            doc.bytes = bytes;
            if let Some(c) = content {
                let terms = Self::terms_from_content(c, path);
                self.index_terms(doc_id, terms)?;
            }
            return Ok(true);
        }

        if self.paths.len() >= self.max_files {
            return Err(IndexError::FileLimit(self.max_files));
        }

        let path_mem = path.len().saturating_add(64);
        if self.estimated_memory.saturating_add(path_mem) > self.max_memory_bytes {
            return Err(IndexError::MemoryLimit(self.max_memory_bytes));
        }

        let doc_id =
            u32::try_from(self.docs.len()).map_err(|_| IndexError::FileLimit(self.max_files))?;
        self.docs.push(IndexedDoc {
            path: path.to_owned(),
            bytes,
            mtime_ms,
            active: true,
        });
        self.paths.insert(path.to_owned(), doc_id);
        self.estimated_memory = self.estimated_memory.saturating_add(path_mem);

        if let Some(c) = content {
            let terms = Self::terms_from_content(c, path);
            self.index_terms(doc_id, terms)?;
        }

        Ok(true)
    }

    fn index_terms(&mut self, doc_id: u32, terms: Vec<String>) -> Result<(), IndexError> {
        for term in terms {
            let term_mem = if self.postings.contains_key(&term) {
                std::mem::size_of::<u32>()
            } else {
                term.len().saturating_add(48)
            };
            if self.estimated_memory.saturating_add(term_mem) > self.max_memory_bytes {
                return Err(IndexError::MemoryLimit(self.max_memory_bytes));
            }
            self.postings.entry(term).or_default().push(doc_id);
            self.estimated_memory = self.estimated_memory.saturating_add(term_mem);
        }
        Ok(())
    }

    pub fn remove(&mut self, path: &str) -> bool {
        if let Some(doc_id) = self.paths.remove(path) {
            if let Some(doc) = self.docs.get_mut(doc_id as usize) {
                doc.active = false;
            }
            self.estimated_memory = self
                .estimated_memory
                .saturating_sub(path.len().saturating_add(64));
            true
        } else {
            false
        }
    }

    #[must_use]
    pub fn search(&self, query: &str, limit: usize) -> Vec<Hit> {
        if limit == 0 {
            return Vec::new();
        }
        let query_terms: Vec<String> = query
            .split(|c: char| !(c.is_alphanumeric() || c == '_'))
            .filter(|t| t.len() >= 2)
            .map(str::to_lowercase)
            .collect();

        if query_terms.is_empty() {
            return Vec::new();
        }

        let max_candidates = limit.saturating_mul(10).max(100);
        let mut scores: HashMap<u32, usize> = HashMap::new();
        for term in &query_terms {
            if let Some(postings) = self.postings.get(term) {
                for &doc_id in postings.iter().take(max_candidates) {
                    if let Some(doc) = self.docs.get(doc_id as usize) {
                        if doc.active {
                            let score = scores.entry(doc_id).or_insert(0);
                            *score = score.saturating_add(10);
                        }
                    }
                }
            }
        }

        let mut ranked: Vec<(u32, usize)> = scores.into_iter().collect();
        ranked.sort_by(|a, b| b.1.cmp(&a.1).then_with(|| a.0.cmp(&b.0)));

        ranked
            .into_iter()
            .take(limit)
            .filter_map(|(doc_id, score)| {
                self.docs.get(doc_id as usize).map(|doc| Hit {
                    path: doc.path.clone(),
                    line: 1,
                    text: format!("{} [indexed file]", doc.path),
                    score,
                })
            })
            .collect()
    }

    pub fn sync_incremental(
        &mut self,
        root: &std::path::Path,
        limits: Limits,
    ) -> Result<SyncStats, ScanError> {
        let entries = scan(root, limits)?;
        let mut disk_paths = HashMap::new();
        let mut stats = SyncStats::default();

        for entry in &entries {
            disk_paths.insert(entry.path.clone(), entry.bytes);
            let full_path = root.join(&entry.path);
            let mtime_ms = std::fs::metadata(&full_path)
                .and_then(|m| m.modified())
                .ok()
                .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
                .map_or(0, |d| u64::try_from(d.as_millis()).unwrap_or(u64::MAX));

            let is_new = !self.paths.contains_key(&entry.path);
            let content = if entry.bytes <= 64 * 1024 {
                std::fs::read_to_string(&full_path).ok()
            } else {
                None
            };

            match self.insert_or_update(&entry.path, mtime_ms, entry.bytes, content.as_deref()) {
                Ok(true) => {
                    if is_new {
                        stats.added = stats.added.saturating_add(1);
                    } else {
                        stats.updated = stats.updated.saturating_add(1);
                    }
                }
                Ok(false) => {
                    stats.unchanged = stats.unchanged.saturating_add(1);
                }
                Err(_) => break,
            }
        }

        let indexed_paths: Vec<String> = self.paths.keys().cloned().collect();
        for p in indexed_paths {
            if !disk_paths.contains_key(&p) && self.remove(&p) {
                stats.removed = stats.removed.saturating_add(1);
            }
        }

        Ok(stats)
    }

    #[must_use]
    pub fn measure_corpus(file_count: usize) -> CorpusMetrics {
        let max_files = file_count.saturating_add(1_000);
        let max_mem = 512 * 1024 * 1024;
        let mut index = Self::new(max_files, max_mem);

        let t0 = Instant::now();
        for i in 0..file_count {
            let path = format!("src/module_{:04}/file_{:06}.rs", i / 1000, i);
            let _ =
                index.insert_or_update(&path, 1000, 2048, Some("pub fn query_target() -> bool"));
        }
        let update_latency = u64::try_from(t0.elapsed().as_micros()).unwrap_or(u64::MAX);

        let t1 = Instant::now();
        let _ = index.search("query_target", 10);
        let search_latency = u64::try_from(t1.elapsed().as_micros()).unwrap_or(u64::MAX);

        CorpusMetrics {
            file_count: index.file_count(),
            memory_bytes: index.estimated_memory_bytes(),
            search_latency_micros: search_latency,
            update_latency_micros: update_latency,
        }
    }
}
