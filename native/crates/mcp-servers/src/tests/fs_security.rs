use std::fs;
use std::os::unix::fs::symlink;

use serde_json::json;

use super::support::{Scratch, config, ok, path_json, refused, root, server};
use crate::{FileServer, Mode};

fn outside(scratch: &Scratch) -> std::path::PathBuf {
    let dir = scratch.dir("fuori");
    let _ = fs::write(dir.join("segreto.txt"), "riservato");
    dir
}

#[test]
fn traversal_and_absolute_escapes_are_blocked() {
    let scratch = Scratch::new();
    let out = outside(&scratch);
    let s = server(&config(&scratch));
    for path in [
        "../fuori/segreto.txt",
        "a/../../fuori/segreto.txt",
        "..",
        "a/./../..",
    ] {
        refused(&s, "read_file", &json!({"path": path}));
        refused(&s, "write_file", &json!({"path": path, "content": "x"}));
    }
    refused(&s, "read_file", &path_json(&out.join("segreto.txt")));
    refused(&s, "read_file", &json!({"path": "/etc/passwd"}));
    refused(&s, "list_dir", &json!({"path": "/"}));
    refused(&s, "read_file", &json!({"path": "a\0b"}));
    assert_eq!(
        fs::read_to_string(out.join("segreto.txt")).unwrap_or_default(),
        "riservato"
    );
}

#[test]
fn symlinks_cannot_leave_the_root() {
    let scratch = Scratch::new();
    let out = outside(&scratch);
    let work = scratch.dir("work");
    let s = server(&config(&scratch));
    assert!(symlink(&out, work.join("porta")).is_ok());
    assert!(symlink(out.join("segreto.txt"), work.join("link.txt")).is_ok());
    refused(&s, "read_file", &json!({"path": "porta/segreto.txt"}));
    refused(&s, "list_dir", &json!({"path": "porta"}));
    refused(
        &s,
        "write_file",
        &json!({"path": "porta/nuovo.txt", "content": "x"}),
    );
    refused(&s, "make_dir", &json!({"path": "porta/sotto"}));
    refused(&s, "read_file", &json!({"path": "link.txt"}));
    refused(
        &s,
        "write_file",
        &json!({"path": "link.txt", "content": "x"}),
    );
    refused(&s, "delete", &json!({"path": "porta/segreto.txt"}));
    refused(
        &s,
        "copy",
        &json!({"src": "porta/segreto.txt", "dst": "copia.txt"}),
    );
    refused(&s, "copy", &json!({"src": "porta", "dst": "copia"}));
    assert!(out.join("segreto.txt").exists());
    assert!(!out.join("nuovo.txt").exists());
    assert_eq!(
        fs::read_to_string(out.join("segreto.txt")).unwrap_or_default(),
        "riservato"
    );
}

#[test]
fn symlinks_inside_a_tree_are_never_followed_by_copy() {
    let scratch = Scratch::new();
    let out = outside(&scratch);
    let work = scratch.dir("work");
    let s = server(&config(&scratch));
    ok(
        &s,
        "write_file",
        &json!({"path": "t/ok.txt", "content": "x"}),
    );
    assert!(symlink(out.join("segreto.txt"), work.join("t/trappola.txt")).is_ok());
    refused(&s, "copy", &json!({"src": "t", "dst": "t2"}));
}

#[test]
fn read_only_roots_extensions_and_reserved_names_are_enforced() {
    let scratch = Scratch::new();
    let share = scratch.dir("share");
    let _ = fs::write(share.join("pubblico.txt"), "ok");
    let mut cfg = config(&scratch);
    if let Some(work) = cfg.roots.first_mut() {
        work.extensions = vec!["txt".into(), "md".into()];
    }
    let s = server(&cfg);
    assert_eq!(
        ok(&s, "read_file", &path_json(&share.join("pubblico.txt"))),
        "ok"
    );
    refused(
        &s,
        "write_file",
        &json!({"path": share.join("nuovo.txt").to_string_lossy(), "content": "x"}),
    );
    refused(&s, "delete", &path_json(&share.join("pubblico.txt")));
    refused(
        &s,
        "move",
        &json!({"src": share.join("pubblico.txt").to_string_lossy(), "dst": "p.txt"}),
    );
    ok(
        &s,
        "copy",
        &json!({"src": share.join("pubblico.txt").to_string_lossy(), "dst": "p.txt"}),
    );
    refused(
        &s,
        "write_file",
        &json!({"path": "script.sh", "content": "x"}),
    );
    refused(&s, "write_file", &json!({"path": ".env", "content": "x"}));
    refused(
        &s,
        "write_file",
        &json!({"path": "chiave.PEM", "content": "x"}),
    );
    refused(
        &s,
        "write_file",
        &json!({"path": ".ssh/authorized_keys", "content": "x"}),
    );
    assert!(!share.join("nuovo.txt").exists());
}

#[test]
fn reserved_names_are_hidden_from_listings_and_searches() {
    let scratch = Scratch::new();
    let work = scratch.dir("work");
    let _ = fs::write(work.join("visibile.txt"), "x");
    let _ = fs::write(work.join("segreto.key"), "x");
    let _ = fs::write(work.join(".env"), "x");
    let s = server(&config(&scratch));
    let listing = ok(&s, "list_dir", &json!({}));
    assert!(
        listing.contains("visibile.txt")
            && !listing.contains("segreto.key")
            && !listing.contains(".env"),
        "{listing}"
    );
    assert!(!ok(&s, "find_files", &json!({"pattern": "*"})).contains("segreto.key"));
    refused(&s, "read_file", &json!({"path": "segreto.key"}));
}

#[test]
fn binary_and_oversized_files_and_root_changes_are_refused() {
    let scratch = Scratch::new();
    let work = scratch.dir("work");
    let _ = fs::write(work.join("dati.bin"), [0u8, 1, 2, 3]);
    let _ = fs::write(work.join("grande.txt"), vec![b'a'; 100]);
    let mut cfg = config(&scratch);
    if let Some(first) = cfg.roots.first_mut() {
        first.max_bytes = 50;
    }
    let s = server(&cfg);
    refused(&s, "read_file", &json!({"path": "dati.bin"}));
    refused(&s, "read_file", &json!({"path": "grande.txt"}));
    refused(&s, "delete", &path_json(&work));
    refused(
        &s,
        "move",
        &json!({"src": work.to_string_lossy(), "dst": "x"}),
    );
}

#[test]
fn depth_and_entry_budgets_are_enforced() {
    let scratch = Scratch::new();
    let mut cfg = config(&scratch);
    if let Some(first) = cfg.roots.first_mut() {
        first.max_depth = 2;
    }
    cfg.max_entries = 3;
    let s = server(&cfg);
    refused(&s, "make_dir", &json!({"path": "a/b/c"}));
    for n in 0..5 {
        ok(
            &s,
            "write_file",
            &json!({"path": format!("d/f{n}"), "content": "x"}),
        );
    }
    refused(&s, "copy", &json!({"src": "d", "dst": "e"}));
}

#[test]
fn invalid_configurations_are_rejected_whole() {
    let scratch = Scratch::new();
    let base = config(&scratch);
    let broken = |mutate: &dyn Fn(&mut crate::FsConfig)| {
        let mut cfg = base.clone();
        mutate(&mut cfg);
        FileServer::new("files", &cfg).is_err()
    };
    assert!(broken(&|c| c.roots.clear()));
    assert!(broken(&|c| c.default_root = Some("nessuna".into())));
    assert!(broken(&|c| c.text_limit = 0));
    assert!(broken(&|c| c.roots.push(root(
        "work",
        &scratch.base,
        Mode::Read
    ))));
    assert!(broken(&|c| c.roots.push(root(
        "x",
        std::path::Path::new("relativo"),
        Mode::Read
    ))));
    assert!(broken(&|c| c.roots.push(root(
        "y",
        std::path::Path::new("/tmp/../etc"),
        Mode::Read
    ))));
    assert!(broken(&|c| c.roots.push(root(
        "assente",
        &scratch.base.join("manca"),
        Mode::Read
    ))));
    assert!(broken(&|c| c.trash = Some(
        scratch
            .dir("work")
            .join("cestino")
            .to_string_lossy()
            .into_owned()
    )));
    assert!(crate::FsConfig::from_json(r#"{"roots":[],"extra":1}"#).is_err());
}
