use crate::widget::{check_manifest, inspect};
use serde_json::json;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU32, Ordering};

static SEQ: AtomicU32 = AtomicU32::new(0);

fn scratch() -> PathBuf {
    let n = SEQ.fetch_add(1, Ordering::Relaxed);
    let dir = std::env::temp_dir().join(format!("nuxiva-widget-{}-{n}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    let _ = fs::create_dir_all(dir.join("language"));
    dir
}

fn put(dir: &Path, rel: &str, body: &str) {
    let _ = fs::write(dir.join(rel), body);
}

fn language(title: &str, say: &str) -> String {
    json!({"meta": {}, "dictionary": {"simple_title": title, "say_ok": say}}).to_string()
}

fn build(mode: &str, script: &str) -> PathBuf {
    let dir = scratch();
    put(
        &dir,
        "widget.json",
        &json!({"id": "demo", "category": "home", "chrome": false, "simple": {"icon": "home", "mode": mode}}).to_string(),
    );
    put(&dir, "widget.js", script);
    for lang in ["it", "en", "fr", "es"] {
        put(
            &dir,
            &format!("language/{lang}.json"),
            &language("Titolo", "Tutto bene"),
        );
    }
    dir
}

fn codes(dir: &Path) -> Vec<String> {
    inspect(dir)
        .into_iter()
        .map(|i| format!("{}:{}", i.field, i.code))
        .collect()
}

#[test]
fn a_complete_collapsible_widget_has_no_issues() {
    let dir = build("collapse", "x = { headline(d, ctx) {} };");
    assert!(codes(&dir).is_empty(), "{:?}", codes(&dir));
}

#[test]
fn collapsible_widget_without_headline_is_rejected() {
    let dir = build("collapse", "x = {};");
    assert_eq!(codes(&dir), vec!["widget.js:headline.missing"]);
}

#[test]
fn open_widget_needs_no_headline() {
    let dir = build("open", "x = {};");
    assert!(codes(&dir).is_empty());
}

#[test]
fn language_defects_are_reported() {
    let dir = build("open", "x = {};");
    put(&dir, "language/fr.json", &language("   ", "Tout va bien"));
    put(
        &dir,
        "language/es.json",
        &language("Título", &"y".repeat(120)),
    );
    let found = codes(&dir);
    assert!(found.contains(&"language/fr.json:simple_title.invalid".to_owned()));
    assert!(found.contains(&"language/es.json:say.invalid".to_owned()));
    let _ = fs::remove_file(dir.join("language/en.json"));
    assert!(codes(&dir).contains(&"language/en.json:unreadable".to_owned()));
}

#[test]
fn manifest_rules_are_strict() {
    let bad = json!({"id": "Bad Id", "category": "nope", "chrome": true, "media": "smell", "simple": {"icon": "A B", "mode": "zoom"}});
    let found: Vec<String> = check_manifest(&bad)
        .into_iter()
        .map(|i| format!("{}:{}", i.field, i.code))
        .collect();
    for want in [
        "id:invalid",
        "category:invalid",
        "chrome:must_be_false",
        "media:invalid",
        "simple.icon:invalid",
        "simple.mode:invalid",
    ] {
        assert!(found.contains(&want.to_owned()), "{want} in {found:?}");
    }
    assert_eq!(
        check_manifest(&json!({"id": "ok"}))
            .iter()
            .filter(|i| i.field == "simple")
            .count(),
        1
    );
}

#[test]
fn every_shipped_widget_passes() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../installer_wizard/agenti");
    let mut seen = 0;
    for category in fs::read_dir(root).into_iter().flatten().flatten() {
        for agent in fs::read_dir(category.path())
            .into_iter()
            .flatten()
            .flatten()
        {
            for entry in fs::read_dir(agent.path().join("widget"))
                .into_iter()
                .flatten()
                .flatten()
            {
                if entry.path().join("widget.json").exists() {
                    let found = codes(&entry.path());
                    assert!(found.is_empty(), "{:?}: {found:?}", entry.file_name());
                    seen += 1;
                }
            }
        }
    }
    assert!(seen == 0 || seen > 50);
}
