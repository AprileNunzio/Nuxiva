use std::fs::{self, DirBuilder};
use std::os::unix::fs::DirBuilderExt;
use std::path::{Component, Path, PathBuf};

use crate::error::{Error, Result};

pub const ALLOWED_ROOTS: &[&str] = &["/mnt", "/media", "/srv/nuxiva", "/run/media"];
const MAX_SEGMENTS: usize = 4;
const MAX_SEGMENT_LEN: usize = 64;

#[must_use]
pub fn valid_segment(segment: &str) -> bool {
    !segment.is_empty()
        && segment.len() <= MAX_SEGMENT_LEN
        && !segment.starts_with('.')
        && !segment.starts_with(' ')
        && !segment.ends_with(' ')
        && !segment.ends_with('.')
        && segment
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, ' ' | '.' | '_' | '-'))
}

#[must_use]
pub fn valid_subdir(subdir: &str) -> bool {
    if subdir.is_empty() {
        return true;
    }
    let parts: Vec<&str> = subdir.split('/').collect();
    parts.len() <= MAX_SEGMENTS && parts.iter().all(|p| valid_segment(p))
}

#[must_use]
pub fn valid_host(host: &str) -> bool {
    !host.is_empty()
        && host.len() <= 253
        && !host.starts_with(['-', '.'])
        && host
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '-'))
}

#[must_use]
pub fn valid_share(share: &str) -> bool {
    !share.is_empty()
        && share.len() <= MAX_SEGMENT_LEN
        && share
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '_' | '-'))
}

#[must_use]
pub fn allowed_in(path: &Path, roots: &[&str]) -> bool {
    path.is_absolute()
        && path
            .components()
            .all(|c| matches!(c, Component::RootDir | Component::Normal(_)))
        && roots.iter().any(|root| path.starts_with(root))
}

#[must_use]
pub fn allowed_root(path: &Path) -> bool {
    allowed_in(path, ALLOWED_ROOTS)
}

pub fn resolve_dir(root: &Path, subdir: &str) -> Result<PathBuf> {
    resolve_dir_in(root, subdir, ALLOWED_ROOTS)
}

pub fn resolve_dir_in(root: &Path, subdir: &str, roots: &[&str]) -> Result<PathBuf> {
    if !allowed_in(root, roots) {
        return Err(Error::Path("root_not_allowed"));
    }
    if !valid_subdir(subdir) {
        return Err(Error::Path("subdir_invalid"));
    }
    let base = fs::canonicalize(root).map_err(|_| Error::Path("root_missing"))?;
    if !allowed_in(&base, roots) {
        return Err(Error::Path("root_escapes"));
    }
    if !fs::metadata(&base)?.is_dir() {
        return Err(Error::Path("root_not_dir"));
    }
    let mut current = base.clone();
    if !subdir.is_empty() {
        for part in subdir.split('/') {
            current.push(part);
            match fs::symlink_metadata(&current) {
                Ok(meta) if meta.file_type().is_symlink() || !meta.is_dir() => {
                    return Err(Error::Path("subdir_unsafe"));
                }
                Ok(_) => {}
                Err(_) => {
                    DirBuilder::new()
                        .mode(0o770)
                        .create(&current)
                        .map_err(Error::Io)?;
                }
            }
        }
    }
    let real = fs::canonicalize(&current)?;
    if !real.starts_with(&base) {
        return Err(Error::Path("subdir_escapes"));
    }
    Ok(real)
}
