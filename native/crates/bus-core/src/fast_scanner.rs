use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::sync::RwLock;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DiscoveredEntry {
    pub id: String,
    pub path: String,
    pub fingerprint: u64,
    pub is_dir: bool,
}

#[derive(Debug, Clone, Default)]
pub struct ScanReport {
    pub total: usize,
    pub added: Vec<String>,
    pub modified: Vec<String>,
    pub removed: Vec<String>,
    pub entries: Vec<DiscoveredEntry>,
}

fn fnv1a_hash(data: &[u8]) -> u64 {
    let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
    for byte in data {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x0100_0000_01b3);
    }
    hash
}

fn compute_fingerprint(path: &Path) -> u64 {
    if let Ok(metadata) = fs::metadata(path) {
        let size = metadata.len();
        let mtime = metadata
            .modified()
            .ok()
            .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
            .map_or(0, |d| d.as_secs());
        let mut seed = Vec::with_capacity(16);
        seed.extend_from_slice(&size.to_le_bytes());
        seed.extend_from_slice(&mtime.to_le_bytes());
        if size < 65536 {
            if let Ok(bytes) = fs::read(path) {
                seed.extend_from_slice(&bytes);
            }
        }
        fnv1a_hash(&seed)
    } else {
        0
    }
}

#[derive(Debug, Default)]
pub struct FastScannerRegistry {
    cache: RwLock<HashMap<String, u64>>,
}

impl FastScannerRegistry {
    #[must_use]
    pub fn new() -> Self {
        Self {
            cache: RwLock::new(HashMap::new()),
        }
    }

    pub fn scan_directory(&self, root_dir: &str, target_file: &str) -> ScanReport {
        let root = Path::new(root_dir);
        let mut report = ScanReport::default();
        if !root.exists() || !root.is_dir() {
            return report;
        }

        let mut current_ids = HashMap::new();
        if let Ok(entries) = fs::read_dir(root) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_dir() {
                    let target_path = path.join(target_file);
                    if target_path.exists() {
                        let dir_name = path
                            .file_name()
                            .and_then(|n| n.to_str())
                            .unwrap_or_default()
                            .to_string();
                        if !dir_name.starts_with('_') && !dir_name.starts_with('.') {
                            let fp = compute_fingerprint(&target_path);
                            current_ids.insert(
                                dir_name.clone(),
                                (target_path.to_string_lossy().to_string(), fp),
                            );
                        }
                    }
                }
            }
        }

        let mut cache_guard = match self.cache.write() {
            Ok(guard) => guard,
            Err(poisoned) => poisoned.into_inner(),
        };

        for (id, (path, fp)) in &current_ids {
            report.entries.push(DiscoveredEntry {
                id: id.clone(),
                path: path.clone(),
                fingerprint: *fp,
                is_dir: true,
            });

            match cache_guard.get(id) {
                None => {
                    report.added.push(id.clone());
                    cache_guard.insert(id.clone(), *fp);
                }
                Some(&cached_fp) if cached_fp != *fp => {
                    report.modified.push(id.clone());
                    cache_guard.insert(id.clone(), *fp);
                }
                _ => {}
            }
        }

        let removed_keys: Vec<String> = cache_guard
            .keys()
            .filter(|k| !current_ids.contains_key(*k))
            .cloned()
            .collect();

        for key in removed_keys {
            report.removed.push(key.clone());
            cache_guard.remove(&key);
        }

        report.total = report.entries.len();
        report
    }

    pub fn invalidate(&self, id: &str) -> bool {
        let mut cache_guard = match self.cache.write() {
            Ok(guard) => guard,
            Err(poisoned) => poisoned.into_inner(),
        };
        cache_guard.remove(id).is_some()
    }

    pub fn clear(&self) {
        let mut cache_guard = match self.cache.write() {
            Ok(guard) => guard,
            Err(poisoned) => poisoned.into_inner(),
        };
        cache_guard.clear();
    }
}
