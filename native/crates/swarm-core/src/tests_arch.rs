use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};

fn walk(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            walk(&path, out);
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
}

fn agent_ids() -> BTreeSet<String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../installer_wizard/agenti");
    let mut ids = BTreeSet::new();
    let Ok(categories) = fs::read_dir(root) else {
        return ids;
    };
    for category in categories.flatten() {
        let Ok(agents) = fs::read_dir(category.path()) else {
            continue;
        };
        for agent in agents.flatten() {
            if agent.path().join("feature.json").is_file() {
                ids.insert(agent.file_name().to_string_lossy().into_owned());
            }
        }
    }
    ids
}

fn literals(source: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut parts = source.split('"');
    parts.next();
    for (index, part) in parts.enumerate() {
        if index % 2 == 0 {
            out.push(part.to_owned());
        }
    }
    out
}

#[test]
fn production_sources_name_no_agent() {
    let ids = agent_ids();
    assert!(ids.len() > 20, "agent tree not found");
    let mut files = Vec::new();
    walk(
        &Path::new(env!("CARGO_MANIFEST_DIR")).join("src"),
        &mut files,
    );
    for file in files {
        let name = file.file_name().map(|n| n.to_string_lossy().into_owned());
        if name.is_some_and(|n| n.starts_with("tests")) {
            continue;
        }
        let Ok(text) = fs::read_to_string(&file) else {
            continue;
        };
        for literal in literals(&text) {
            assert!(
                !ids.contains(&literal),
                "{} names agent {literal}",
                file.display()
            );
        }
    }
}

#[test]
fn every_source_file_stays_within_the_line_limit() {
    let mut files = Vec::new();
    walk(
        &Path::new(env!("CARGO_MANIFEST_DIR")).join("src"),
        &mut files,
    );
    for file in files {
        let lines = fs::read_to_string(&file).map_or(0, |t| t.lines().count());
        assert!(lines <= 500, "{} has {lines} lines", file.display());
    }
}
