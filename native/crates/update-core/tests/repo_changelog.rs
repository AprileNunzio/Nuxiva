use nuxiva_update_core::release_notes::{self, DIR};
use std::fs;
use std::path::PathBuf;

#[test]
fn every_repository_changelog_file_is_valid() -> Result<(), String> {
    let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../..")
        .join(DIR);
    let entries = fs::read_dir(&dir).map_err(|e| format!("{}: {e}", dir.display()))?;
    let mut checked = 0usize;
    for entry in entries {
        let path = entry.map_err(|e| e.to_string())?.path();
        let name = path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or_default()
            .to_owned();
        if name == "README.md" {
            continue;
        }
        let raw = fs::read_to_string(&path).map_err(|e| format!("{name}: {e}"))?;
        release_notes::parse(&name, &raw).map_err(|e| format!("{name}: {e}"))?;
        checked += 1;
    }
    if checked == 0 {
        return Err(format!("no changelog files in {}", dir.display()));
    }
    Ok(())
}
