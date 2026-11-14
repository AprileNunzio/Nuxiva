use std::fs;
use std::os::unix::fs::symlink;

use nuxiva_graph_core::{FileSource, GraphError};

use crate::graph::DirSource;
use crate::tests::support::Scratch;

fn project() -> (Scratch, DirSource) {
    let scratch = Scratch::new();
    let root = scratch.dir("proj");
    fs::create_dir_all(root.join("src")).expect("src");
    fs::create_dir_all(root.join("target")).expect("target");
    fs::create_dir_all(root.join("node_modules/x")).expect("nm");
    fs::write(root.join("src/lib.rs"), "pub fn a() {}\n").expect("lib");
    fs::write(root.join("README.md"), "# Titolo\n").expect("readme");
    fs::write(root.join("image.png"), [0_u8; 8]).expect("png");
    fs::write(root.join("target/gen.rs"), "fn x() {}\n").expect("gen");
    fs::write(root.join("node_modules/x/i.js"), "1\n").expect("js");
    let source = DirSource::new(&root).expect("source");
    (scratch, source)
}

#[test]
fn lists_only_known_languages_and_skips_build_dirs() {
    let (_scratch, source) = project();
    let paths: Vec<String> = source
        .list()
        .expect("list")
        .into_iter()
        .map(|e| e.path)
        .collect();
    assert_eq!(paths, vec!["README.md".to_owned(), "src/lib.rs".to_owned()]);
}

#[test]
fn reads_within_limit_and_rejects_oversize() {
    let (_scratch, source) = project();
    assert_eq!(
        source.read("src/lib.rs", 1024).expect("read"),
        b"pub fn a() {}\n"
    );
    assert_eq!(source.read("src/lib.rs", 4), Err(GraphError::TooLarge));
}

#[test]
fn rejects_traversal_absolute_and_skipped_paths() {
    let (_scratch, source) = project();
    for bad in [
        "../x",
        "/etc/passwd",
        "src/../../x",
        "target/gen.rs",
        "",
        "a//b",
        "a\\b",
    ] {
        assert!(source.read(bad, 1024).is_err(), "{bad}");
    }
}

#[test]
fn symlinks_are_neither_listed_nor_followed() {
    let scratch = Scratch::new();
    let root = scratch.dir("p2");
    let outside = scratch.dir("outside");
    fs::write(outside.join("secret.rs"), "fn secret() {}\n").expect("secret");
    symlink(outside.join("secret.rs"), root.join("link.rs")).expect("file link");
    symlink(&outside, root.join("linkdir")).expect("dir link");
    fs::write(root.join("ok.rs"), "fn ok() {}\n").expect("ok");
    let source = DirSource::new(&root).expect("source");
    let paths: Vec<String> = source
        .list()
        .expect("list")
        .into_iter()
        .map(|e| e.path)
        .collect();
    assert_eq!(paths, vec!["ok.rs".to_owned()]);
    assert!(source.read("link.rs", 1024).is_err());
    assert!(source.read("linkdir/secret.rs", 1024).is_err());
}

#[test]
fn missing_root_is_an_error() {
    assert!(DirSource::new(std::path::Path::new("/nonexistent/nuxiva-graph")).is_err());
}

#[test]
fn stamp_changes_when_file_is_rewritten() {
    let (scratch, source) = project();
    let before = source.list().expect("list");
    std::thread::sleep(std::time::Duration::from_millis(20));
    fs::write(scratch.base.join("proj/src/lib.rs"), "pub fn b() {}\n").expect("rewrite");
    let after = source.list().expect("list");
    assert_ne!(before, after);
}
