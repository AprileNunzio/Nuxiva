use std::fs;
use std::path::{Path, PathBuf};

const LIMIT: usize = 500;
const FORBIDDEN: &[&str] = &["music", "camera", "firewall", "home_assistant", "mcpclient"];

fn sources(dir: &Path, out: &mut Vec<PathBuf>) -> std::io::Result<()> {
    for entry in fs::read_dir(dir)? {
        let path = entry?.path();
        if path.is_dir() {
            if path.file_name().is_some_and(|n| n != "tests") {
                sources(&path, out)?;
            }
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
    Ok(())
}

#[test]
fn sources_hold_no_domain_identifiers_and_stay_short() -> std::io::Result<()> {
    let mut files = Vec::new();
    sources(
        &Path::new(env!("CARGO_MANIFEST_DIR")).join("src"),
        &mut files,
    )?;
    assert!(!files.is_empty());
    for file in files {
        let text = fs::read_to_string(&file)?;
        assert!(text.lines().count() <= LIMIT, "{}", file.display());
        for word in FORBIDDEN {
            assert!(!text.contains(word), "{} contains {word}", file.display());
        }
    }
    Ok(())
}
