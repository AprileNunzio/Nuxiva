use crate::manifest::{Severity, validate};
use crate::registry::{Layout, Origin, Registry, Root};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU32, Ordering};

static SEQ: AtomicU32 = AtomicU32::new(0);

fn scratch() -> PathBuf {
    let n = SEQ.fetch_add(1, Ordering::Relaxed);
    let dir = std::env::temp_dir().join(format!("nuxiva-agent-core-{}-{n}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    let _ = fs::create_dir_all(&dir);
    dir
}

fn put(dir: &Path, rel: &str, body: &str) {
    let path = dir.join(rel);
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let _ = fs::write(path, body);
}

const PARTICLES: &str = r#"{"id":"particles","name":"Particelle","category":"creativita",
"description":"Scultore di particelle 3D","capabilities":["Morfogenesi"],
"routing":{"nouns":["medusa","ologramma"],"phrases":["mostrami le particelle"]},
"requires":{"ram_gb":2,"gpu_vram_gb":1}}"#;

#[test]
fn accepts_complete_manifest_and_converts_legacy_requirements() {
    let report = validate(PARTICLES, "particles", Some("creativita"));
    let Some(m) = report.manifest else {
        unreachable!("manifest rejected")
    };
    assert_eq!(m.profile.ram_mb, 2048);
    assert_eq!(m.profile.vram_mb, 1024);
    assert_eq!(m.routing.nouns, vec!["medusa", "ologramma"]);
    assert!(report.issues.is_empty());
}

#[test]
fn rejects_invalid_identity_and_types() {
    for (raw, code) in [
        (r#"{"id":"Bad Id","name":"x"}"#, "id_invalid"),
        (r#"{"id":"registry","name":"x"}"#, "id_reserved"),
        (r#"{"id":"ok_id"}"#, "name_missing"),
        (
            r#"{"id":"ok_id","name":"x","capabilities":"no"}"#,
            "type_list",
        ),
        (r#"{"id":"ok_id","name":"x\u0007"}"#, "control_chars"),
        (
            r#"{"id":"ok_id","name":"x","profile":{"ram_mb":-5}}"#,
            "out_of_range",
        ),
        ("[1,2]", "not_object"),
        ("{", "invalid_json"),
    ] {
        let report = validate(raw, "ok_id", None);
        assert!(report.manifest.is_none(), "{raw}");
        assert!(
            report
                .issues
                .iter()
                .any(|i| i.code == code && i.severity == Severity::Error),
            "{raw}"
        );
    }
}

#[test]
fn physical_category_wins_and_mismatch_is_reported() {
    let report = validate(PARTICLES, "particles", Some("multimedia"));
    let Some(m) = report.manifest else {
        unreachable!("manifest rejected")
    };
    assert_eq!(m.category, "multimedia");
    assert!(
        report
            .issues
            .iter()
            .any(|i| i.code == "category_folder_mismatch")
    );
}

#[test]
fn scans_categorized_and_flat_roots_with_unique_ids() {
    let base = scratch();
    put(&base, "agenti/creativita/particles/feature.json", PARTICLES);
    put(&base, "features/particles/feature.json", PARTICLES);
    put(
        &base,
        "features/weather/feature.json",
        r#"{"id":"weather","name":"Meteo","category":"casa"}"#,
    );
    put(&base, "features/broken/feature.json", "{");
    put(&base, "features/Not-Valid/feature.json", PARTICLES);
    let roots = vec![
        Root {
            path: base.join("agenti"),
            origin: Origin::System,
            layout: Layout::Categorized,
        },
        Root {
            path: base.join("features"),
            origin: Origin::Legacy,
            layout: Layout::Flat,
        },
    ];
    let mut registry = Registry::new();
    assert!(registry.refresh(&roots));
    let snap = registry.snapshot();
    assert_eq!(snap.agents.len(), 2);
    let Some(p) = snap.locate("particles") else {
        unreachable!("missing")
    };
    assert_eq!(p.origin, Origin::System);
    assert!(p.dir.ends_with("agenti/creativita/particles"));
    assert!(
        snap.rejected
            .iter()
            .any(|r| r.issues.iter().any(|i| i.code == "id_duplicate"))
    );
    assert!(
        snap.rejected
            .iter()
            .any(|r| r.issues.iter().any(|i| i.code == "invalid_json"))
    );
    assert_eq!(snap.by_category.get("creativita").map(Vec::len), Some(1));
    assert_eq!(
        snap.search("Mi mostri una medusa", 3)
            .first()
            .map(|h| h.0.as_str()),
        Some("particles")
    );
    assert!(!registry.refresh(&roots));
    let _ = fs::remove_dir_all(base);
}

#[cfg(unix)]
#[test]
fn ignores_symlinked_agent_directories() {
    let base = scratch();
    put(&base, "outside/evil/feature.json", PARTICLES);
    let _ = fs::create_dir_all(base.join("features"));
    let _ = std::os::unix::fs::symlink(base.join("outside/evil"), base.join("features/evil"));
    let roots = vec![Root {
        path: base.join("features"),
        origin: Origin::Legacy,
        layout: Layout::Flat,
    }];
    let mut registry = Registry::new();
    registry.refresh(&roots);
    assert!(registry.snapshot().agents.is_empty());
    let _ = fs::remove_dir_all(base);
}

#[test]
fn scaffold_builds_a_complete_valid_agent() {
    let spec = crate::layout::ScaffoldSpec {
        id: "medico".into(),
        category: "salute".into(),
        name: "Medico".into(),
        description: "Battito, stress e respiro".into(),
        capabilities: vec!["Battito".into()],
        nouns: vec!["battito".into()],
        ..Default::default()
    };
    let Ok(files) = crate::layout::scaffold(&spec) else {
        unreachable!("scaffold rejected")
    };
    let base = scratch();
    let dir = base.join("agenti/salute/medico");
    for file in &files {
        let path = dir.join(&file.path);
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        let _ = fs::write(path, &file.bytes);
    }
    let report = crate::layout::inspect(&dir);
    assert!(report.complete, "{:?}", report.missing);
    assert_eq!(report.score, 100);
    let roots = vec![Root {
        path: base.join("agenti"),
        origin: Origin::System,
        layout: Layout::Categorized,
    }];
    let mut registry = Registry::new();
    registry.refresh(&roots);
    let Some(entry) = registry.snapshot().locate("medico") else {
        unreachable!("missing")
    };
    assert!(entry.issues.is_empty(), "{:?}", entry.issues);
    let _ = fs::remove_dir_all(base);
}

#[test]
fn scaffold_rejects_unknown_category_and_bad_ids() {
    for (id, category, description) in [
        ("medico", "inventata", "x"),
        ("Medico!", "salute", "x"),
        ("medico", "salute", " "),
    ] {
        let spec = crate::layout::ScaffoldSpec {
            id: id.into(),
            category: category.into(),
            name: "Medico".into(),
            description: description.into(),
            ..Default::default()
        };
        assert!(crate::layout::scaffold(&spec).is_err(), "{id} {category}");
    }
}

#[test]
fn inspect_reports_missing_parts() {
    let base = scratch();
    put(&base, "a/feature.json", PARTICLES);
    let report = crate::layout::inspect(&base.join("a"));
    assert!(!report.complete);
    assert!(report.missing.contains(&"agent.py".to_owned()));
    assert!(report.missing.contains(&"language/es.json".to_owned()));
    assert_eq!(report.optional_missing, vec!["widget/".to_owned()]);
    let _ = fs::remove_dir_all(base);
}
