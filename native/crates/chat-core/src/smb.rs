use std::path::{Component, Path, PathBuf};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SmbShareCategory {
    Documenti,
    Codice,
    Scambio,
    Progetti,
}

impl SmbShareCategory {
    #[must_use]
    pub const fn folder_name(self) -> &'static str {
        match self {
            Self::Documenti => "01 Documenti",
            Self::Codice => "04 Codice",
            Self::Scambio => "05 Scambio",
            Self::Progetti => "09 Progetti",
        }
    }

    #[must_use]
    pub fn from_folder_name(name: &str) -> Option<Self> {
        match name {
            "01 Documenti" | "documenti" => Some(Self::Documenti),
            "04 Codice" | "codice" => Some(Self::Codice),
            "05 Scambio" | "scambio" => Some(Self::Scambio),
            "09 Progetti" | "progetti" => Some(Self::Progetti),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SmbPathGuard {
    base_dir: PathBuf,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SmbGuardError {
    InvalidCharacters,
    PathTraversalDetected,
    EmptyFilename,
    UnknownCategory,
}

impl SmbPathGuard {
    #[must_use]
    pub fn new(base_dir: impl Into<PathBuf>) -> Self {
        Self {
            base_dir: base_dir.into(),
        }
    }

    pub fn sanitize_component(raw: &str) -> Result<String, SmbGuardError> {
        let trimmed = raw.trim();
        if trimmed.is_empty() {
            return Err(SmbGuardError::EmptyFilename);
        }
        if trimmed.contains('\0')
            || trimmed.contains('\\')
            || trimmed.contains('/')
            || trimmed.contains("..")
            || trimmed.contains(':')
            || trimmed.contains('*')
            || trimmed.contains('?')
            || trimmed.contains('"')
            || trimmed.contains('<')
            || trimmed.contains('>')
            || trimmed.contains('|')
        {
            return Err(SmbGuardError::InvalidCharacters);
        }
        Ok(trimmed.to_string())
    }

    pub fn resolve_safe_path(
        &self,
        category: SmbShareCategory,
        subpath: &str,
    ) -> Result<PathBuf, SmbGuardError> {
        let mut resolved = self.base_dir.join(category.folder_name());
        let relative = Path::new(subpath);

        for component in relative.components() {
            match component {
                Component::Normal(segment) => {
                    let seg_str = segment.to_str().ok_or(SmbGuardError::InvalidCharacters)?;
                    let clean = Self::sanitize_component(seg_str)?;
                    resolved.push(clean);
                }
                Component::CurDir => {}
                Component::ParentDir | Component::RootDir | Component::Prefix(_) => {
                    return Err(SmbGuardError::PathTraversalDetected);
                }
            }
        }

        Ok(resolved)
    }

    #[must_use]
    pub fn format_unc(ip_or_host: &str, category: SmbShareCategory, subpath: &str) -> String {
        let mut unc = format!(
            "\\\\{}\\\\condivisa\\\\{}",
            ip_or_host,
            category.folder_name()
        );
        let clean_sub = subpath.trim().trim_matches(['/', '\\']);
        if !clean_sub.is_empty() {
            let win_sub = clean_sub.replace('/', "\\");
            unc.push('\\');
            unc.push_str(&win_sub);
        }
        unc
    }
}
