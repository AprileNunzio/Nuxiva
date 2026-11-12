use serde::Serialize;
use sha1::Sha1;
use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::{self, Read};
use std::path::{Component, Path, PathBuf};

const MAX_LISTED: usize = 40;
const CHUNK: usize = 64 * 1024;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TreeEntry {
    pub mode: String,
    pub oid: String,
    pub path: String,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize)]
pub struct IntegrityReport {
    pub algorithm: &'static str,
    pub checked: usize,
    pub matched: usize,
    pub skipped: usize,
    pub mismatched: Vec<String>,
    pub missing: Vec<String>,
    pub rejected: Vec<String>,
    pub fingerprint: String,
    pub intact: bool,
}

fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write;
    bytes.iter().fold(
        String::with_capacity(bytes.len().saturating_mul(2)),
        |mut acc, b| {
            let _ = write!(acc, "{b:02x}");
            acc
        },
    )
}

fn valid_oid(oid: &str) -> bool {
    (oid.len() == 40 || oid.len() == 64)
        && oid
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

#[must_use]
pub fn parse_ls_tree(raw: &str) -> Vec<TreeEntry> {
    raw.split('\0')
        .filter_map(|record| {
            let (meta, path) = record.split_once('\t')?;
            let mut parts = meta.split(' ');
            let mode = parts.next()?;
            let kind = parts.next()?;
            let oid = parts.next()?;
            let accepted = matches!(kind, "blob" | "commit") && valid_oid(oid) && !path.is_empty();
            accepted.then(|| TreeEntry {
                mode: mode.to_owned(),
                oid: oid.to_owned(),
                path: path.to_owned(),
            })
        })
        .collect()
}

fn safe_join(root: &Path, relative: &str) -> Option<PathBuf> {
    let rel = Path::new(relative);
    if relative.contains('\0') || !rel.components().all(|c| matches!(c, Component::Normal(_))) {
        return None;
    }
    let joined = root.join(rel);
    let parent = joined.parent()?.canonicalize().ok()?;
    parent.starts_with(root).then_some(joined)
}

trait Hasher {
    fn feed(&mut self, data: &[u8]);
    fn finish_hex(self: Box<Self>) -> String;
}

impl Hasher for Sha1 {
    fn feed(&mut self, data: &[u8]) {
        Digest::update(self, data);
    }
    fn finish_hex(self: Box<Self>) -> String {
        hex(&self.finalize())
    }
}

impl Hasher for Sha256 {
    fn feed(&mut self, data: &[u8]) {
        Digest::update(self, data);
    }
    fn finish_hex(self: Box<Self>) -> String {
        hex(&self.finalize())
    }
}

fn hasher(long: bool) -> Box<dyn Hasher> {
    if long {
        Box::new(Sha256::new())
    } else {
        Box::new(Sha1::new())
    }
}

#[must_use]
pub fn blob_oid(content: &[u8], long: bool) -> String {
    let mut h = hasher(long);
    h.feed(format!("blob {}\0", content.len()).as_bytes());
    h.feed(content);
    h.finish_hex()
}

fn file_oid(path: &Path, size: u64, long: bool) -> io::Result<String> {
    let mut h = hasher(long);
    h.feed(format!("blob {size}\0").as_bytes());
    let mut file = File::open(path)?;
    let mut buffer = vec![0_u8; CHUNK];
    let mut total: u64 = 0;
    loop {
        let read = file.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        total = total.saturating_add(u64::try_from(read).unwrap_or(u64::MAX));
        h.feed(buffer.get(..read).unwrap_or_default());
    }
    if total == size {
        Ok(h.finish_hex())
    } else {
        Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "file_changed_during_hash",
        ))
    }
}

#[cfg(unix)]
fn link_bytes(target: &Path) -> Vec<u8> {
    use std::os::unix::ffi::OsStrExt;
    target.as_os_str().as_bytes().to_vec()
}

#[cfg(not(unix))]
fn link_bytes(target: &Path) -> Vec<u8> {
    target.to_string_lossy().replace('\\', "/").into_bytes()
}

fn actual_oid(path: &Path, mode: &str, long: bool) -> io::Result<String> {
    let meta = fs::symlink_metadata(path)?;
    if mode == "120000" {
        if !meta.file_type().is_symlink() {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "expected_symlink",
            ));
        }
        return Ok(blob_oid(&link_bytes(&fs::read_link(path)?), long));
    }
    if !meta.file_type().is_file() {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "expected_file"));
    }
    file_oid(path, meta.len(), long)
}

fn push_capped(list: &mut Vec<String>, value: &str) {
    if list.len() < MAX_LISTED {
        list.push(value.to_owned());
    }
}

#[must_use]
pub fn verify(root: &Path, entries: &[TreeEntry]) -> IntegrityReport {
    let long = entries.first().is_some_and(|e| e.oid.len() == 64);
    let mut report = IntegrityReport {
        algorithm: if long { "sha256" } else { "sha1" },
        ..IntegrityReport::default()
    };
    let Ok(root) = root.canonicalize() else {
        report.rejected.push(String::from("."));
        return report;
    };
    let mut sorted: Vec<&TreeEntry> = entries.iter().collect();
    sorted.sort_by(|a, b| a.path.cmp(&b.path));
    let mut fingerprint = Sha256::new();
    let mut failures: usize = 0;
    for entry in sorted {
        fingerprint.update(format!("{} {} {}\n", entry.mode, entry.oid, entry.path).as_bytes());
        if entry.mode == "160000" {
            report.skipped = report.skipped.saturating_add(1);
            continue;
        }
        report.checked = report.checked.saturating_add(1);
        if (entry.oid.len() == 64) != long {
            failures = failures.saturating_add(1);
            push_capped(&mut report.rejected, &entry.path);
            continue;
        }
        let Some(path) = safe_join(&root, &entry.path) else {
            failures = failures.saturating_add(1);
            push_capped(&mut report.rejected, &entry.path);
            continue;
        };
        match actual_oid(&path, &entry.mode, long) {
            Ok(oid) if oid == entry.oid => report.matched = report.matched.saturating_add(1),
            Err(err) if err.kind() == io::ErrorKind::NotFound => {
                failures = failures.saturating_add(1);
                push_capped(&mut report.missing, &entry.path);
            }
            Ok(_) | Err(_) => {
                failures = failures.saturating_add(1);
                push_capped(&mut report.mismatched, &entry.path);
            }
        }
    }
    report.fingerprint = hex(&fingerprint.finalize());
    report.intact = failures == 0;
    report
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scratch(name: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("nuxiva-update-core-{name}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        let _ = fs::create_dir_all(dir.join("src"));
        dir
    }

    #[test]
    fn blob_oid_matches_git() {
        assert_eq!(
            blob_oid(b"hello\n", false),
            "ce013625030ba8dba906f756967f9e9ca394464a"
        );
        assert_eq!(
            blob_oid(b"", false),
            "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
        );
    }

    #[test]
    fn parses_ls_tree_and_filters_garbage() {
        let raw = "100644 blob ce013625030ba8dba906f756967f9e9ca394464a\tsrc/a.txt\x00160000 commit e69de29bb2d1d6434b8b29ae775ad8c2e48c5391\tvendor\0bad line\x00100644 blob XYZ\tb\0";
        let entries = parse_ls_tree(raw);
        assert_eq!(entries.len(), 2);
        assert_eq!(entries.first().map(|e| e.path.as_str()), Some("src/a.txt"));
    }

    #[test]
    fn verifies_tampered_missing_and_traversal() {
        let dir = scratch("verify");
        let _ = fs::write(dir.join("src/a.txt"), b"hello\n");
        let _ = fs::write(dir.join("src/b.txt"), b"tampered\n");
        let oid = String::from("ce013625030ba8dba906f756967f9e9ca394464a");
        let entry = |path: &str| TreeEntry {
            mode: String::from("100644"),
            oid: oid.clone(),
            path: path.to_owned(),
        };
        let report = verify(
            &dir,
            &[
                entry("src/a.txt"),
                entry("src/b.txt"),
                entry("src/c.txt"),
                entry("../etc/passwd"),
            ],
        );
        assert_eq!(report.matched, 1);
        assert_eq!(report.mismatched, vec![String::from("src/b.txt")]);
        assert_eq!(report.missing, vec![String::from("src/c.txt")]);
        assert_eq!(report.rejected, vec![String::from("../etc/passwd")]);
        assert!(!report.intact);
        assert_eq!(report.fingerprint.len(), 64);
        let clean = verify(&dir, &[entry("src/a.txt")]);
        assert!(clean.intact);
        let _ = fs::remove_dir_all(&dir);
    }
}
