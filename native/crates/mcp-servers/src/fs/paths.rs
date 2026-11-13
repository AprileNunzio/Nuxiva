use std::fs;
use std::path::{Component, Path, PathBuf};

use nuxiva_mcp_core::glob_match;

use super::config::{FsConfig, MAX_PATH, Mode, RootConfig};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Fault {
    Invalid,
    Outside,
    ReadOnly,
    Denied,
    Extension,
    Depth,
    Special,
    Missing,
    NotFile,
    NotDir,
    TooBig,
    Binary,
    Limit,
    Io,
    NoTrash,
    IsRoot,
}

impl Fault {
    #[must_use]
    pub fn message(self) -> &'static str {
        match self {
            Self::Invalid => "percorso non valido",
            Self::Outside => "percorso fuori dalle cartelle consentite",
            Self::ReadOnly => "la cartella è consentita solo in lettura",
            Self::Denied => "nome riservato: accesso negato",
            Self::Extension => "tipo di file non consentito in questa cartella",
            Self::Depth => "percorso troppo profondo",
            Self::Special => "i file speciali e i collegamenti non sono consentiti",
            Self::Missing => "il percorso non esiste",
            Self::NotFile => "non è un file",
            Self::NotDir => "non è una cartella",
            Self::TooBig => "file troppo grande",
            Self::Binary => "il file non è di testo",
            Self::Limit => "limite di operazione superato",
            Self::Io => "operazione non riuscita",
            Self::NoTrash => "cestino non configurato",
            Self::IsRoot => "la cartella radice non può essere modificata",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Need {
    Read,
    Write,
}

#[derive(Debug, Clone)]
pub struct Target {
    pub path: PathBuf,
    pub root: usize,
    pub relative: PathBuf,
}

#[derive(Debug)]
pub struct Boundary {
    pub roots: Vec<(RootConfig, PathBuf)>,
    pub default_root: Option<usize>,
    pub trash: Option<PathBuf>,
    denied: Vec<String>,
}

fn canonical_prefix(path: &Path) -> Result<(PathBuf, Vec<std::ffi::OsString>), Fault> {
    let mut rest = Vec::new();
    let mut probe = path.to_path_buf();
    loop {
        if let Ok(canon) = fs::canonicalize(&probe) {
            rest.reverse();
            return Ok((canon, rest));
        }
        let name = probe.file_name().ok_or(Fault::Invalid)?.to_owned();
        rest.push(name);
        if !probe.pop() {
            return Err(Fault::Invalid);
        }
    }
}

impl Boundary {
    pub fn new(config: &FsConfig) -> Result<Self, Fault> {
        let mut roots = Vec::new();
        for root in &config.roots {
            let canon = fs::canonicalize(&root.path).map_err(|_| Fault::Missing)?;
            if !canon.is_dir() {
                return Err(Fault::NotDir);
            }
            roots.push((root.clone(), canon));
        }
        let trash = match &config.trash {
            Some(path) => {
                fs::create_dir_all(path).map_err(|_| Fault::Io)?;
                let canon = fs::canonicalize(path).map_err(|_| Fault::Io)?;
                if roots
                    .iter()
                    .any(|(_, r)| canon.starts_with(r) || r.starts_with(&canon))
                {
                    return Err(Fault::Invalid);
                }
                Some(canon)
            }
            None => None,
        };
        let default_root = config
            .default_root
            .as_ref()
            .and_then(|name| roots.iter().position(|(r, _)| &r.name == name));
        Ok(Self {
            roots,
            default_root,
            trash,
            denied: config
                .denied_names
                .iter()
                .map(|n| n.to_lowercase())
                .collect(),
        })
    }

    fn denied_name(&self, name: &str) -> bool {
        let lower = name.to_lowercase();
        self.denied
            .iter()
            .any(|pattern| glob_match(pattern, &lower))
    }

    pub fn resolve(&self, input: &str, need: Need) -> Result<Target, Fault> {
        if input.len() > MAX_PATH || input.contains('\0') {
            return Err(Fault::Invalid);
        }
        let raw = Path::new(input);
        let candidate = if input.is_empty() {
            let index = self.default_root.ok_or(Fault::Invalid)?;
            self.roots.get(index).ok_or(Fault::Invalid)?.1.clone()
        } else if raw.is_absolute() {
            raw.to_path_buf()
        } else {
            let index = self.default_root.ok_or(Fault::Invalid)?;
            self.roots.get(index).ok_or(Fault::Invalid)?.1.join(raw)
        };
        if candidate
            .components()
            .any(|c| matches!(c, Component::ParentDir))
        {
            return Err(Fault::Invalid);
        }
        let (canon, rest) = canonical_prefix(&candidate)?;
        let mut full = canon;
        for part in &rest {
            full.push(part);
        }
        let (index, (config, root_path)) = self
            .roots
            .iter()
            .enumerate()
            .filter(|(_, (_, p))| full.starts_with(p))
            .max_by_key(|(_, (_, p))| p.components().count())
            .ok_or(Fault::Outside)?;
        if need == Need::Write && config.mode != Mode::Write {
            return Err(Fault::ReadOnly);
        }
        let relative = full
            .strip_prefix(root_path)
            .map_err(|_| Fault::Outside)?
            .to_path_buf();
        let mut depth = 0usize;
        for component in relative.components() {
            let Component::Normal(name) = component else {
                return Err(Fault::Invalid);
            };
            if self.denied_name(&name.to_string_lossy()) {
                return Err(Fault::Denied);
            }
            depth = depth.saturating_add(1);
        }
        if depth > config.max_depth {
            return Err(Fault::Depth);
        }
        Ok(Target {
            path: full,
            root: index,
            relative,
        })
    }

    pub fn config(&self, target: &Target) -> Result<&RootConfig, Fault> {
        self.roots
            .get(target.root)
            .map(|(c, _)| c)
            .ok_or(Fault::Outside)
    }

    pub fn check_extension(&self, target: &Target) -> Result<(), Fault> {
        let config = self.config(target)?;
        if config.extensions.is_empty() {
            return Ok(());
        }
        let ext = target
            .path
            .extension()
            .map(|e| e.to_string_lossy().to_lowercase())
            .unwrap_or_default();
        if config.extensions.iter().any(|e| e.to_lowercase() == ext) {
            Ok(())
        } else {
            Err(Fault::Extension)
        }
    }

    pub fn is_root(target: &Target) -> bool {
        target.relative.as_os_str().is_empty()
    }

    pub fn visible(&self, name: &str) -> bool {
        !self.denied_name(name)
    }
}
