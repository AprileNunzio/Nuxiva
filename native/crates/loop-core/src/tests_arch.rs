use std::fs;
use std::path::Path;

fn source(name: &str) -> String {
    fs::read_to_string(Path::new(env!("CARGO_MANIFEST_DIR")).join("src").join(name))
        .expect("source")
}

#[test]
fn permits_are_only_constructed_in_the_gate() {
    for name in [
        "engine.rs",
        "judge.rs",
        "wire.rs",
        "settings.rs",
        "paths.rs",
        "redact.rs",
        "error.rs",
        "lib.rs",
    ] {
        assert!(!source(name).contains("Permit {"), "{name}");
    }
    let gate = source("gate.rs");
    assert_eq!(gate.matches("Some(Permit {").count(), 1);
    assert!(gate.contains("pub struct Permit {\n    digest: String"));
}

#[test]
fn engine_never_references_the_gate_or_the_network() {
    let engine = source("engine.rs");
    for banned in ["Gate", "Permit", "std::net", "std::process", "std::fs"] {
        assert!(!engine.contains(banned), "{banned}");
    }
}

#[test]
fn no_file_is_oversized() {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
    for entry in fs::read_dir(dir).expect("dir").flatten() {
        let text = fs::read_to_string(entry.path()).expect("read");
        assert!(text.lines().count() <= 500, "{:?}", entry.path());
    }
}
