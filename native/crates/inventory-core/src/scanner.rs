use std::fs;
use std::path::PathBuf;

use crate::error::{InventoryError, InventoryResult};
use crate::model::{Found, Kind, Origin};

pub const MAX_MANIFEST_BYTES: u64 = 256 * 1024;
pub const MAX_ENTRIES: usize = 50_000;

pub trait Scanner: Send + Sync {
    fn kind(&self) -> Kind;
    fn scan(&self) -> InventoryResult<Vec<Found>>;
}

fn valid_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 64
        && id
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_' || b == b'.')
}

#[derive(Debug, Clone)]
pub struct DirScanner {
    kind: Kind,
    root: PathBuf,
    origin: Origin,
    manifest: &'static str,
    depth: usize,
}

impl DirScanner {
    #[must_use]
    pub fn new(
        kind: Kind,
        root: PathBuf,
        origin: Origin,
        manifest: &'static str,
        depth: usize,
    ) -> Self {
        Self {
            kind,
            root,
            origin,
            manifest,
            depth: depth.clamp(1, 3),
        }
    }

    fn walk(&self, dir: &PathBuf, level: usize, out: &mut Vec<Found>) -> InventoryResult<()> {
        let entries = match fs::read_dir(dir) {
            Ok(entries) => entries,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound && level == 1 => {
                return Ok(());
            }
            Err(_) => return Err(InventoryError::Scan("read_dir".into())),
        };
        for entry in entries.flatten() {
            let path = entry.path();
            let Ok(meta) = fs::symlink_metadata(&path) else {
                continue;
            };
            if !meta.is_dir() {
                continue;
            }
            let manifest = path.join(self.manifest);
            if let Ok(info) = fs::symlink_metadata(&manifest) {
                if info.is_file() && info.len() <= MAX_MANIFEST_BYTES {
                    let name = entry.file_name().to_string_lossy().into_owned();
                    if valid_id(&name) {
                        let bytes = fs::read(&manifest)
                            .map_err(|_| InventoryError::Scan("read_manifest".into()))?;
                        out.push(Found::new(&name, self.origin, &bytes));
                    }
                }
            } else if level < self.depth {
                self.walk(&path, level.saturating_add(1), out)?;
            }
            if out.len() > MAX_ENTRIES {
                return Err(InventoryError::Scan("too_many".into()));
            }
        }
        Ok(())
    }
}

impl Scanner for DirScanner {
    fn kind(&self) -> Kind {
        self.kind
    }

    fn scan(&self) -> InventoryResult<Vec<Found>> {
        let mut out = Vec::new();
        self.walk(&self.root, 1, &mut out)?;
        out.sort_by(|a, b| a.id.cmp(&b.id));
        Ok(out)
    }
}
