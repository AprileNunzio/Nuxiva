use std::fs;
use std::path::{Path, PathBuf};

use agency_domain::WorkspacePath;

use crate::error::AgencyError;

pub fn prepare(root: &Path, relative: &WorkspacePath) -> Result<PathBuf, AgencyError> {
    use std::os::unix::fs::DirBuilderExt;
    let root = fs::canonicalize(root)
        .map_err(|_| AgencyError::Config("shared workspace folder is missing"))?;
    let target = relative.resolve(&root);
    fs::DirBuilder::new()
        .recursive(true)
        .mode(0o775)
        .create(&target)?;
    let resolved = fs::canonicalize(&target)?;
    if resolved.starts_with(&root) && resolved != root {
        Ok(resolved)
    } else {
        Err(AgencyError::Escape)
    }
}

pub fn locate(root: &Path, relative: &WorkspacePath) -> Result<PathBuf, AgencyError> {
    let root = fs::canonicalize(root)
        .map_err(|_| AgencyError::Config("shared workspace folder is missing"))?;
    let resolved = fs::canonicalize(relative.resolve(&root))?;
    if resolved.starts_with(&root) && resolved != root {
        Ok(resolved)
    } else {
        Err(AgencyError::Escape)
    }
}
