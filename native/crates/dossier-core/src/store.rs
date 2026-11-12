use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};

use agency_ledger::{Entry, LedgerKey, LedgerStore};
use serde::{Deserialize, Serialize};
use serde_json::json;
use sha2::{Digest, Sha256};
use zeroize::Zeroizing;

use crate::clock;
use crate::doc::{self, Doc, Problem};
use crate::kind::{Kind, Level};
use crate::redact::redact;

pub const LEDGER: &str = "registro.jsonl";
pub const KEEP_AFTER_PRUNE: &str = "99-esito.md";
const MAX_FILE: u64 = doc::MAX_DOC as u64;

#[derive(Debug)]
pub enum StoreError {
    Path(&'static str),
    Invalid(Vec<Problem>),
    Ledger(String),
    Io(std::io::Error),
}

impl std::fmt::Display for StoreError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Path(why) => write!(f, "path: {why}"),
            Self::Invalid(p) => write!(f, "invalid document: {} problems", p.len()),
            Self::Ledger(e) => write!(f, "ledger: {e}"),
            Self::Io(e) => write!(f, "io: {e}"),
        }
    }
}

impl From<std::io::Error> for StoreError {
    fn from(e: std::io::Error) -> Self {
        Self::Io(e)
    }
}

impl From<agency_ledger::LedgerError> for StoreError {
    fn from(e: agency_ledger::LedgerError) -> Self {
        Self::Ledger(e.to_string())
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Report {
    pub ok: bool,
    pub level: String,
    pub complete: bool,
    pub files: Vec<String>,
    pub problems: Vec<Problem>,
}

pub struct Store {
    root: PathBuf,
    key: Zeroizing<[u8; 32]>,
}

impl std::fmt::Debug for Store {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Store")
            .field("root", &self.root)
            .finish_non_exhaustive()
    }
}

fn sha_hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .fold(String::new(), |mut out, b| {
            let _ = write!(out, "{b:02x}");
            out
        })
}

fn digits(part: &str, len: usize) -> bool {
    part.len() == len && part.bytes().all(|b| b.is_ascii_digit())
}

fn valid_id(id: &str) -> bool {
    let parts: Vec<&str> = id.split('-').collect();
    matches!(parts.as_slice(), [d, t, r] if digits(d, 8) && digits(t, 6)
        && r.len() == 6 && r.bytes().all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase()))
}

#[must_use]
pub fn valid_rel(rel: &str) -> bool {
    let parts: Vec<&str> = rel.split('/').collect();
    matches!(parts.as_slice(), [y, m, d, id] if digits(y, 4) && digits(m, 2) && digits(d, 2) && valid_id(id))
}

fn private_dir(path: &Path) -> Result<(), StoreError> {
    match fs::symlink_metadata(path) {
        Ok(meta) if meta.file_type().is_symlink() || !meta.is_dir() => {
            Err(StoreError::Path("not_a_directory"))
        }
        Ok(_) => Ok(()),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            let mut builder = fs::DirBuilder::new();
            #[cfg(unix)]
            {
                use std::os::unix::fs::DirBuilderExt;
                builder.mode(0o700);
            }
            builder.create(path)?;
            Ok(())
        }
        Err(e) => Err(e.into()),
    }
}

fn nofollow(options: &mut OpenOptions) {
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        let flag = i32::try_from(rustix::fs::OFlags::NOFOLLOW.bits()).unwrap_or(0);
        options.mode(0o600).custom_flags(flag);
    }
    #[cfg(not(unix))]
    let _ = options;
}

fn read_limited(path: &Path) -> Result<Vec<u8>, StoreError> {
    let mut options = OpenOptions::new();
    options.read(true);
    nofollow(&mut options);
    let file = options.open(path)?;
    let mut out = Vec::new();
    file.take(MAX_FILE.saturating_add(1))
        .read_to_end(&mut out)?;
    if u64::try_from(out.len()).unwrap_or(u64::MAX) > MAX_FILE {
        return Err(StoreError::Path("file_too_large"));
    }
    Ok(out)
}

fn random_tag() -> Result<String, StoreError> {
    let mut bytes = [0u8; 8];
    getrandom::fill(&mut bytes).map_err(|e| std::io::Error::other(e.to_string()))?;
    Ok(sha_hex(&bytes).chars().take(16).collect())
}

fn atomic_write(dir: &Path, name: &str, bytes: &[u8]) -> Result<(), StoreError> {
    let tmp = dir.join(format!(".{name}.{}.tmp", random_tag()?));
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    nofollow(&mut options);
    let result = (|| -> Result<(), StoreError> {
        let mut file = options.open(&tmp)?;
        file.write_all(bytes)?;
        file.sync_all()?;
        fs::rename(&tmp, dir.join(name))?;
        File::open(dir)?.sync_all()?;
        Ok(())
    })();
    if result.is_err() {
        let _ = fs::remove_file(&tmp);
    }
    result
}

impl Store {
    pub fn new(root: &Path, key: [u8; 32]) -> Result<Self, StoreError> {
        let meta = fs::symlink_metadata(root)?;
        if meta.file_type().is_symlink() || !meta.is_dir() {
            return Err(StoreError::Path("root_not_directory"));
        }
        Ok(Self {
            root: root.to_path_buf(),
            key: Zeroizing::new(key),
        })
    }

    fn dir(&self, rel: &str) -> Result<PathBuf, StoreError> {
        if !valid_rel(rel) {
            return Err(StoreError::Path("bad_operation"));
        }
        Ok(self.root.join(rel))
    }

    fn ledger(&self, dir: &Path) -> Result<LedgerStore, StoreError> {
        Ok(LedgerStore::open(
            &dir.join(LEDGER),
            LedgerKey::from_bytes(*self.key),
        )?)
    }

    pub fn open(&self, now_ms: u64, level: Level) -> Result<String, StoreError> {
        let mut suffix = [0u8; 3];
        getrandom::fill(&mut suffix).map_err(|e| std::io::Error::other(e.to_string()))?;
        let id = clock::operation_id(now_ms, suffix);
        let rel = format!("{}/{id}", clock::day_path(now_ms));
        let mut path = self.root.clone();
        for part in rel.split('/') {
            path.push(part);
            private_dir(&path)?;
        }
        let mut ledger = self.ledger(&path)?;
        if !ledger.chain().is_empty() {
            return Err(StoreError::Path("operation_exists"));
        }
        ledger.append(
            "dossier.open",
            json!({"id": id, "level": level.as_str()}),
            now_ms,
        )?;
        Ok(rel)
    }

    pub fn write(
        &self,
        rel: &str,
        name: &str,
        document: &Doc,
        now_ms: u64,
    ) -> Result<String, StoreError> {
        let kind = Kind::of_name(name).ok_or(StoreError::Path("bad_file_name"))?;
        let clean = doc::sanitize(document);
        let problems = doc::validate(&clean, kind);
        if !problems.is_empty() {
            return Err(StoreError::Invalid(problems));
        }
        let base = self.dir(rel)?;
        private_dir(&base)?;
        let (folder, file) = match name.split_once('/') {
            Some((sub, file)) => {
                let folder = base.join(sub);
                private_dir(&folder)?;
                (folder, file)
            }
            None => (base.clone(), name),
        };
        let text = redact(&doc::render(&clean));
        if text.len() > doc::MAX_DOC {
            return Err(StoreError::Invalid(vec![Problem::new("", "too_large")]));
        }
        let sha = sha_hex(text.as_bytes());
        let mut ledger = self.ledger(&base)?;
        if ledger.chain().is_empty() {
            return Err(StoreError::Path("operation_not_open"));
        }
        atomic_write(&folder, file, text.as_bytes())?;
        ledger.append(
            "dossier.write",
            json!({"file": name, "sha256": sha, "bytes": text.len()}),
            now_ms,
        )?;
        Ok(sha)
    }

    pub fn read(&self, rel: &str, name: &str) -> Result<Doc, StoreError> {
        Kind::of_name(name).ok_or(StoreError::Path("bad_file_name"))?;
        let bytes = read_limited(&self.dir(rel)?.join(name))?;
        let text = String::from_utf8(bytes).map_err(|_| StoreError::Path("not_utf8"))?;
        doc::parse(&text).map_err(|p| StoreError::Invalid(vec![p]))
    }

    fn entries(dir: &Path) -> Result<Vec<Entry>, StoreError> {
        let reader = BufReader::new(File::open(dir.join(LEDGER))?);
        let mut out = Vec::new();
        for raw in reader.lines() {
            let raw = raw?;
            out.push(serde_json::from_str(&raw).map_err(|e| StoreError::Ledger(e.to_string()))?);
        }
        Ok(out)
    }

    pub fn verify(&self, rel: &str) -> Result<Report, StoreError> {
        let dir = self.dir(rel)?;
        let mut problems = Vec::new();
        if self.ledger(&dir).is_err() {
            problems.push(Problem::new(LEDGER, "chain_broken"));
            return Ok(Report {
                ok: false,
                level: String::new(),
                complete: false,
                files: Vec::new(),
                problems,
            });
        }
        let mut expected: BTreeMap<String, Option<String>> = BTreeMap::new();
        let mut level = String::new();
        for entry in Self::entries(&dir)? {
            let file = entry
                .payload
                .get("file")
                .and_then(|v| v.as_str())
                .map(str::to_owned);
            match entry.kind.as_str() {
                "dossier.open" => {
                    entry
                        .payload
                        .get("level")
                        .and_then(|v| v.as_str())
                        .unwrap_or("")
                        .clone_into(&mut level);
                }
                "dossier.write" => {
                    if let Some(file) = file {
                        let sha = entry
                            .payload
                            .get("sha256")
                            .and_then(|v| v.as_str())
                            .map(str::to_owned);
                        expected.insert(file, sha);
                    }
                }
                "dossier.prune" => {
                    for value in entry
                        .payload
                        .get("files")
                        .and_then(|v| v.as_array())
                        .into_iter()
                        .flatten()
                    {
                        if let Some(name) = value.as_str() {
                            expected.insert(name.to_owned(), None);
                        }
                    }
                }
                _ => problems.push(Problem::new(LEDGER, "unknown_entry")),
            }
        }
        let mut files = Vec::new();
        for (name, sha) in &expected {
            let path = dir.join(name);
            match (sha, read_limited(&path)) {
                (Some(want), Ok(bytes)) if &sha_hex(&bytes) == want => files.push(name.clone()),
                (Some(_), Ok(_)) => problems.push(Problem::new(name, "edited")),
                (Some(_), Err(_)) => problems.push(Problem::new(name, "missing")),
                (None, Ok(_)) => problems.push(Problem::new(name, "should_be_pruned")),
                (None, Err(_)) => {}
            }
        }
        for name in Self::on_disk(&dir)? {
            if !expected.contains_key(&name) {
                problems.push(Problem::new(&name, "unlogged"));
            }
        }
        let parsed = Level::parse(&level);
        let complete = parsed.is_some_and(|l| {
            l.required()
                .iter()
                .all(|k| files.iter().any(|f| Kind::of_name(f) == Some(*k)))
        });
        Ok(Report {
            ok: problems.is_empty() && parsed.is_some(),
            level,
            complete,
            files,
            problems,
        })
    }

    fn on_disk(dir: &Path) -> Result<Vec<String>, StoreError> {
        let mut out = Vec::new();
        for entry in fs::read_dir(dir)? {
            let entry = entry?;
            let name = entry.file_name().to_string_lossy().into_owned();
            let kind = entry.file_type()?;
            if kind.is_dir() && name == "passi" {
                for step in fs::read_dir(entry.path())? {
                    let step = step?.file_name().to_string_lossy().into_owned();
                    out.push(format!("passi/{step}"));
                }
            } else if name != LEDGER {
                out.push(name);
            }
        }
        out.sort();
        Ok(out)
    }

    pub fn recent(&self, limit: usize) -> Result<Vec<String>, StoreError> {
        let names = |path: PathBuf, size: usize| -> Result<Vec<String>, StoreError> {
            let mut out = Vec::new();
            for entry in fs::read_dir(path)? {
                let entry = entry?;
                let name = entry.file_name().to_string_lossy().into_owned();
                if entry.file_type()?.is_dir() && digits(&name, size) {
                    out.push(name);
                }
            }
            out.sort_unstable_by(|a, b| b.cmp(a));
            Ok(out)
        };
        let mut out = Vec::new();
        for y in names(self.root.clone(), 4)? {
            for m in names(self.root.join(&y), 2)? {
                for d in names(self.root.join(&y).join(&m), 2)? {
                    let day = self.root.join(&y).join(&m).join(&d);
                    let mut ids: Vec<String> = fs::read_dir(&day)?
                        .filter_map(Result::ok)
                        .filter(|e| e.file_type().is_ok_and(|t| t.is_dir()))
                        .map(|e| e.file_name().to_string_lossy().into_owned())
                        .filter(|n| valid_id(n))
                        .collect();
                    ids.sort_unstable_by(|a, b| b.cmp(a));
                    for id in ids {
                        out.push(format!("{y}/{m}/{d}/{id}"));
                        if out.len() >= limit {
                            return Ok(out);
                        }
                    }
                }
            }
        }
        Ok(out)
    }

    pub fn expired(&self, now_ms: u64, days: u64, limit: usize) -> Result<Vec<String>, StoreError> {
        let cutoff = clock::day_path(now_ms.saturating_sub(days.saturating_mul(86_400_000)));
        let mut out = Vec::new();
        let walk = |rel: &str| -> Result<Vec<String>, StoreError> {
            let path = if rel.is_empty() {
                self.root.clone()
            } else {
                self.root.join(rel)
            };
            let mut names = Vec::new();
            for entry in fs::read_dir(path)? {
                let entry = entry?;
                if entry.file_type()?.is_dir() {
                    names.push(entry.file_name().to_string_lossy().into_owned());
                }
            }
            names.sort();
            Ok(names)
        };
        for y in walk("")?.into_iter().filter(|n| digits(n, 4)) {
            for m in walk(&y)?.into_iter().filter(|n| digits(n, 2)) {
                for d in walk(&format!("{y}/{m}"))?
                    .into_iter()
                    .filter(|n| digits(n, 2))
                {
                    let day = format!("{y}/{m}/{d}");
                    if day >= cutoff {
                        return Ok(out);
                    }
                    for id in walk(&day)?.into_iter().filter(|n| valid_id(n)) {
                        let rel = format!("{day}/{id}");
                        if Self::on_disk(&self.root.join(&rel))?
                            .iter()
                            .any(|n| n != KEEP_AFTER_PRUNE)
                        {
                            out.push(rel);
                        }
                        if out.len() >= limit {
                            return Ok(out);
                        }
                    }
                }
            }
        }
        Ok(out)
    }

    pub fn prune(&self, rel: &str, now_ms: u64) -> Result<usize, StoreError> {
        let dir = self.dir(rel)?;
        let mut ledger = self.ledger(&dir)?;
        let doomed: Vec<String> = Self::on_disk(&dir)?
            .into_iter()
            .filter(|n| n != KEEP_AFTER_PRUNE && Kind::of_name(n).is_some())
            .collect();
        if doomed.is_empty() {
            return Ok(0);
        }
        ledger.append("dossier.prune", json!({"files": doomed}), now_ms)?;
        for name in &doomed {
            fs::remove_file(dir.join(name))?;
        }
        let steps = dir.join("passi");
        if fs::symlink_metadata(&steps).is_ok_and(|m| m.is_dir()) {
            let _ = fs::remove_dir(&steps);
        }
        Ok(doomed.len())
    }
}
