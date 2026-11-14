use std::fs::{self, File};
use std::io::Read;
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

use nuxiva_graph_core::{Entry, FileSource, GraphError, GraphResult, Language, language};

const MAX_DEPTH: usize = 24;
const MAX_ENTRIES: usize = 200_000;
const MAX_PATH: usize = 512;
const SKIPPED: &[&str] = &[
    ".git",
    "node_modules",
    "target",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
];

#[derive(Debug, Clone)]
pub struct DirSource {
    root: PathBuf,
}

impl DirSource {
    pub fn new(root: &Path) -> GraphResult<Self> {
        let root = fs::canonicalize(root).map_err(|_| GraphError::Source)?;
        if root.is_dir() {
            Ok(Self { root })
        } else {
            Err(GraphError::Source)
        }
    }

    fn walk(dir: &Path, prefix: &str, depth: usize, out: &mut Vec<Entry>) {
        if depth > MAX_DEPTH {
            return;
        }
        let Ok(reader) = fs::read_dir(dir) else {
            return;
        };
        for item in reader.flatten() {
            if out.len() >= MAX_ENTRIES {
                return;
            }
            let Ok(name) = item.file_name().into_string() else {
                continue;
            };
            let Ok(meta) = fs::symlink_metadata(item.path()) else {
                continue;
            };
            let rel = if prefix.is_empty() {
                name.clone()
            } else {
                format!("{prefix}/{name}")
            };
            if meta.is_dir() {
                if !SKIPPED.contains(&name.as_str()) {
                    Self::walk(&item.path(), &rel, depth.saturating_add(1), out);
                }
            } else if meta.is_file()
                && rel.len() <= MAX_PATH
                && !rel.chars().any(char::is_control)
                && language(&rel) != Language::Other
            {
                let stamp = meta
                    .modified()
                    .ok()
                    .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                    .map_or(0, |d| u64::try_from(d.as_nanos()).unwrap_or(u64::MAX));
                out.push(Entry {
                    path: rel,
                    size: meta.len(),
                    stamp,
                });
            }
        }
    }

    fn confined(&self, path: &str) -> GraphResult<PathBuf> {
        nuxiva_graph_core::validate_path(path, MAX_PATH)?;
        let mut current = self.root.clone();
        for part in path.split('/') {
            if SKIPPED.contains(&part) {
                return Err(GraphError::Path);
            }
            current.push(part);
            let meta = fs::symlink_metadata(&current).map_err(|_| GraphError::Source)?;
            if meta.file_type().is_symlink() {
                return Err(GraphError::Path);
            }
        }
        Ok(current)
    }
}

impl FileSource for DirSource {
    fn list(&self) -> GraphResult<Vec<Entry>> {
        let mut out = Vec::new();
        Self::walk(&self.root, "", 0, &mut out);
        out.sort_by(|a, b| a.path.cmp(&b.path));
        Ok(out)
    }

    fn read(&self, path: &str, limit: usize) -> GraphResult<Vec<u8>> {
        let target = self.confined(path)?;
        let file = File::open(&target).map_err(|_| GraphError::Source)?;
        let meta = file.metadata().map_err(|_| GraphError::Source)?;
        if !meta.is_file() {
            return Err(GraphError::Source);
        }
        let cap = u64::try_from(limit).unwrap_or(u64::MAX);
        if meta.len() > cap {
            return Err(GraphError::TooLarge);
        }
        let mut body = Vec::new();
        file.take(cap.saturating_add(1))
            .read_to_end(&mut body)
            .map_err(|_| GraphError::Source)?;
        if body.len() > limit {
            return Err(GraphError::TooLarge);
        }
        Ok(body)
    }
}
