use std::fs::{self, File};
use std::io::Read;
use std::path::{Path, PathBuf};

const READ_LIMIT: u64 = 256 * 1024;
const LIST_LIMIT: usize = 256;

#[derive(Debug, Clone)]
pub struct Root {
    base: PathBuf,
}

impl Default for Root {
    fn default() -> Self {
        Self::new("/")
    }
}

impl Root {
    pub fn new(base: impl Into<PathBuf>) -> Self {
        Self { base: base.into() }
    }

    #[must_use]
    pub fn path(&self, absolute: &str) -> PathBuf {
        self.base.join(absolute.trim_start_matches('/'))
    }

    #[must_use]
    pub fn exists(&self, absolute: &str) -> bool {
        self.path(absolute).exists()
    }

    #[must_use]
    pub fn read(&self, absolute: &str) -> Option<String> {
        read_limited(&self.path(absolute))
    }

    #[must_use]
    pub fn read_trim(&self, absolute: &str) -> Option<String> {
        self.read(absolute)
            .map(|text| {
                text.trim_matches(|c: char| c.is_whitespace() || c == '\0')
                    .to_owned()
            })
            .filter(|text| !text.is_empty())
    }

    pub fn entries(&self, absolute: &str) -> Vec<String> {
        let Ok(dir) = fs::read_dir(self.path(absolute)) else {
            return Vec::new();
        };
        let mut names: Vec<String> = dir
            .filter_map(Result::ok)
            .filter_map(|entry| entry.file_name().into_string().ok())
            .take(LIST_LIMIT)
            .collect();
        names.sort();
        names
    }

    #[must_use]
    pub fn link_name(&self, absolute: &str) -> Option<String> {
        fs::read_link(self.path(absolute)).ok().and_then(|target| {
            target
                .file_name()
                .map(|name| name.to_string_lossy().into_owned())
        })
    }

    #[must_use]
    pub fn base(&self) -> &Path {
        &self.base
    }
}

fn read_limited(path: &Path) -> Option<String> {
    let file = File::open(path).ok()?;
    let mut buffer = Vec::new();
    file.take(READ_LIMIT).read_to_end(&mut buffer).ok()?;
    Some(String::from_utf8_lossy(&buffer).into_owned())
}

#[must_use]
pub fn clean_label(raw: &str, limit: usize) -> String {
    raw.chars()
        .filter(|c| {
            c.is_alphanumeric()
                || matches!(c, ' ' | '.' | ',' | ':' | '-' | '_' | '(' | ')' | '/' | '+')
        })
        .collect::<String>()
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .chars()
        .take(limit)
        .collect()
}
