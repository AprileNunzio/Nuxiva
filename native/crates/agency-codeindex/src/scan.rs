use std::fs;
use std::path::{Path, PathBuf};

use serde::Serialize;
use thiserror::Error;

const SKIPPED_DIRS: [&str; 8] = [
    "node_modules",
    "target",
    "dist",
    "build",
    "__pycache__",
    "venv",
    ".git",
    ".venv",
];

#[derive(Debug, Error)]
pub enum ScanError {
    #[error("root is not a directory")]
    NotDirectory,
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
}

#[derive(Debug, Clone, Copy)]
pub struct Limits {
    pub max_files: usize,
    pub max_depth: usize,
    pub max_file_bytes: u64,
}

impl Default for Limits {
    fn default() -> Self {
        Self {
            max_files: 20_000,
            max_depth: 16,
            max_file_bytes: 1024 * 1024,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct FileEntry {
    pub path: String,
    pub bytes: u64,
    pub language: &'static str,
}

#[must_use]
pub fn language(path: &Path) -> &'static str {
    match path.extension().and_then(|e| e.to_str()).unwrap_or("") {
        "rs" => "rust",
        "py" => "python",
        "js" | "mjs" | "cjs" | "jsx" => "javascript",
        "ts" | "tsx" => "typescript",
        "html" | "htm" => "html",
        "css" | "scss" => "css",
        "json" => "json",
        "md" => "markdown",
        "toml" | "yaml" | "yml" | "ini" => "config",
        "sql" => "sql",
        "php" => "php",
        "sh" => "shell",
        "go" => "go",
        "java" | "kt" => "jvm",
        _ => "other",
    }
}

fn relative(root: &Path, path: &Path) -> Option<String> {
    let rel = path.strip_prefix(root).ok()?;
    let parts: Option<Vec<&str>> = rel.components().map(|c| c.as_os_str().to_str()).collect();
    parts.map(|p| p.join("/"))
}

pub fn scan(root: &Path, limits: Limits) -> Result<Vec<FileEntry>, ScanError> {
    let meta = fs::symlink_metadata(root)?;
    if !meta.is_dir() {
        return Err(ScanError::NotDirectory);
    }
    let mut out = Vec::new();
    let mut stack: Vec<(PathBuf, usize)> = vec![(root.to_path_buf(), 0)];
    while let Some((dir, depth)) = stack.pop() {
        let mut entries: Vec<fs::DirEntry> = fs::read_dir(&dir)?.filter_map(Result::ok).collect();
        entries.sort_by_key(fs::DirEntry::file_name);
        for entry in entries {
            if out.len() >= limits.max_files {
                return Ok(out);
            }
            let name = entry.file_name();
            let Some(name) = name.to_str() else {
                continue;
            };
            if name.starts_with('.') {
                continue;
            }
            let kind = entry.file_type()?;
            let path = entry.path();
            if kind.is_dir() {
                if depth < limits.max_depth && !SKIPPED_DIRS.contains(&name) {
                    stack.push((path, depth.saturating_add(1)));
                }
            } else if kind.is_file() {
                let bytes = entry.metadata()?.len();
                let rel = relative(root, &path).filter(|_| bytes <= limits.max_file_bytes);
                if let Some(rel) = rel {
                    out.push(FileEntry {
                        language: language(&path),
                        path: rel,
                        bytes,
                    });
                }
            }
        }
    }
    out.sort_by(|a, b| a.path.cmp(&b.path));
    Ok(out)
}
