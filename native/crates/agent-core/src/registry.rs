use crate::manifest::{self, Issue, Manifest, Severity, valid_folder};
use crate::text::tokens;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

pub const MANIFEST: &str = "feature.json";
pub const MAX_AGENTS: usize = 200_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Origin {
    System,
    Legacy,
    User,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Layout {
    Categorized,
    Flat,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Root {
    pub path: PathBuf,
    pub origin: Origin,
    pub layout: Layout,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Entry {
    pub manifest: Manifest,
    pub dir: String,
    pub origin: Origin,
    pub issues: Vec<Issue>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Rejected {
    pub path: String,
    pub issues: Vec<Issue>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Snapshot {
    pub signature: String,
    pub agents: BTreeMap<String, Entry>,
    pub rejected: Vec<Rejected>,
    pub by_category: BTreeMap<String, Vec<String>>,
    pub keywords: BTreeMap<String, Vec<String>>,
}

#[derive(Debug, Clone)]
struct Found {
    path: PathBuf,
    folder: String,
    category: Option<String>,
    origin: Origin,
    stamp: String,
}

fn real_dir(path: &Path) -> bool {
    fs::symlink_metadata(path).is_ok_and(|m| m.file_type().is_dir())
}

fn stamp(path: &Path) -> Option<String> {
    let meta = fs::symlink_metadata(path).ok()?;
    if !meta.file_type().is_file() {
        return None;
    }
    let nanos = meta
        .modified()
        .ok()?
        .duration_since(UNIX_EPOCH)
        .ok()?
        .as_nanos();
    Some(format!("{}:{nanos}:{}", path.display(), meta.len()))
}

fn children(dir: &Path) -> Vec<(String, PathBuf)> {
    let Ok(read) = fs::read_dir(dir) else {
        return Vec::new();
    };
    let mut out: Vec<(String, PathBuf)> = read
        .filter_map(Result::ok)
        .filter_map(|e| e.file_name().into_string().ok().map(|n| (n, e.path())))
        .filter(|(name, path)| valid_folder(name) && real_dir(path))
        .collect();
    out.sort();
    out
}

fn collect(root: &Root, out: &mut Vec<Found>) {
    let groups: Vec<(Option<String>, PathBuf)> = match root.layout {
        Layout::Flat => vec![(None, root.path.clone())],
        Layout::Categorized => children(&root.path)
            .into_iter()
            .map(|(n, p)| (Some(n), p))
            .collect(),
    };
    for (category, dir) in groups {
        for (folder, path) in children(&dir) {
            if out.len() >= MAX_AGENTS {
                return;
            }
            let file = path.join(MANIFEST);
            if let Some(stamp) = stamp(&file) {
                out.push(Found {
                    path: file,
                    folder,
                    category: category.clone(),
                    origin: root.origin,
                    stamp,
                });
            }
        }
    }
}

fn fnv(parts: &[&str]) -> String {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for part in parts {
        for b in part.bytes().chain(std::iter::once(0u8)) {
            h ^= u64::from(b);
            h = h.wrapping_mul(0x0100_0000_01b3);
        }
    }
    format!("{h:016x}")
}

fn keywords_of(m: &Manifest) -> BTreeSet<String> {
    let mut set = BTreeSet::new();
    let fields = [
        m.id.replace('_', " "),
        m.name.clone(),
        m.description.clone(),
    ];
    for field in fields
        .iter()
        .chain(&m.capabilities)
        .chain(&m.routing.nouns)
        .chain(&m.routing.verbs)
    {
        set.extend(tokens(field));
    }
    set
}

#[derive(Debug, Default)]
pub struct Registry {
    snapshot: Snapshot,
}

impl Registry {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    #[must_use]
    pub fn snapshot(&self) -> &Snapshot {
        &self.snapshot
    }

    pub fn refresh(&mut self, roots: &[Root]) -> bool {
        let mut found = Vec::new();
        for root in roots {
            collect(root, &mut found);
        }
        let stamps: Vec<&str> = found.iter().map(|f| f.stamp.as_str()).collect();
        let signature = fnv(&stamps);
        if signature == self.snapshot.signature && !self.snapshot.signature.is_empty() {
            return false;
        }
        self.snapshot = build(&found, signature);
        true
    }
}

fn build(found: &[Found], signature: String) -> Snapshot {
    let mut snap = Snapshot {
        signature,
        ..Snapshot::default()
    };
    for item in found {
        let path = item.path.display().to_string();
        let report = match fs::read(&item.path) {
            Ok(bytes) if bytes.len() <= manifest::MAX_MANIFEST_BYTES => {
                match String::from_utf8(bytes) {
                    Ok(raw) => manifest::validate(&raw, &item.folder, item.category.as_deref()),
                    Err(_) => reject(&mut snap, path, "invalid_utf8"),
                }
            }
            Ok(_) => reject(&mut snap, path, "too_large"),
            Err(_) => reject(&mut snap, path, "unreadable"),
        };
        let Some(m) = report.manifest else {
            if !report.issues.is_empty() {
                snap.rejected.push(Rejected {
                    path: item.path.display().to_string(),
                    issues: report.issues,
                });
            }
            continue;
        };
        if snap.agents.contains_key(&m.id) {
            snap.rejected.push(Rejected {
                path: item.path.display().to_string(),
                issues: vec![Issue {
                    field: "id".into(),
                    code: "id_duplicate".into(),
                    severity: Severity::Error,
                }],
            });
            continue;
        }
        let dir = item
            .path
            .parent()
            .map(|p| p.display().to_string())
            .unwrap_or_default();
        snap.by_category
            .entry(m.category.clone())
            .or_default()
            .push(m.id.clone());
        for word in keywords_of(&m) {
            snap.keywords.entry(word).or_default().push(m.id.clone());
        }
        snap.agents.insert(
            m.id.clone(),
            Entry {
                manifest: m,
                dir,
                origin: item.origin,
                issues: report.issues,
            },
        );
    }
    snap
}

fn reject(snap: &mut Snapshot, path: String, code: &str) -> manifest::Report {
    snap.rejected.push(Rejected {
        path,
        issues: vec![Issue {
            field: String::new(),
            code: code.into(),
            severity: Severity::Error,
        }],
    });
    manifest::Report {
        manifest: None,
        issues: Vec::new(),
    }
}

impl Snapshot {
    #[must_use]
    pub fn search(&self, query: &str, limit: usize) -> Vec<(String, usize)> {
        let mut hits: BTreeMap<&str, usize> = BTreeMap::new();
        for word in tokens(query) {
            if let Some(ids) = self.keywords.get(&word) {
                for id in ids {
                    let slot = hits.entry(id.as_str()).or_insert(0);
                    *slot = slot.saturating_add(1);
                }
            }
        }
        let mut ranked: Vec<(String, usize)> =
            hits.into_iter().map(|(id, n)| (id.to_owned(), n)).collect();
        ranked.sort_by(|a, b| b.1.cmp(&a.1).then_with(|| a.0.cmp(&b.0)));
        ranked.truncate(limit);
        ranked
    }

    #[must_use]
    pub fn locate(&self, id: &str) -> Option<&Entry> {
        self.agents.get(id)
    }
}
