use std::fs;

use serde_json::json;

use super::support::{Scratch, call, config, ok, refused, server};

#[test]
fn write_read_list_and_info_round_trip() {
    let scratch = Scratch::new();
    let s = server(&config(&scratch));
    ok(
        &s,
        "write_file",
        &json!({"path": "note.txt", "content": "ciao mondo"}),
    );
    assert_eq!(
        ok(&s, "read_file", &json!({"path": "note.txt"})),
        "ciao mondo"
    );
    let listing = ok(&s, "list_dir", &json!({}));
    assert!(listing.contains("📄 note.txt (10 B)"), "{listing}");
    let info = ok(&s, "file_info", &json!({"path": "note.txt"}));
    assert!(
        info.contains("10 B") && info.contains("modificato il"),
        "{info}"
    );
}

#[test]
fn append_and_overwrite_keep_the_previous_version_in_the_trash() {
    let scratch = Scratch::new();
    let s = server(&config(&scratch));
    ok(
        &s,
        "write_file",
        &json!({"path": "a.txt", "content": "uno"}),
    );
    ok(
        &s,
        "write_file",
        &json!({"path": "a.txt", "content": "+due", "append": true}),
    );
    assert_eq!(ok(&s, "read_file", &json!({"path": "a.txt"})), "uno+due");
    ok(
        &s,
        "write_file",
        &json!({"path": "a.txt", "content": "nuovo", "append": "false"}),
    );
    assert_eq!(ok(&s, "read_file", &json!({"path": "a.txt"})), "nuovo");
    let saved: Vec<String> = fs::read_dir(scratch.base.join("trash"))
        .into_iter()
        .flatten()
        .flatten()
        .flat_map(|d| fs::read_dir(d.path()).into_iter().flatten().flatten())
        .filter_map(|f| fs::read_to_string(f.path()).ok())
        .collect();
    assert_eq!(saved, vec!["uno+due".to_owned()]);
}

#[test]
fn nested_directories_copy_move_and_delete_to_trash() {
    let scratch = Scratch::new();
    let s = server(&config(&scratch));
    ok(&s, "make_dir", &json!({"path": "a/b/c"}));
    ok(
        &s,
        "write_file",
        &json!({"path": "a/b/c/f.txt", "content": "x"}),
    );
    ok(&s, "copy", &json!({"src": "a", "dst": "copia"}));
    assert_eq!(
        ok(&s, "read_file", &json!({"path": "copia/b/c/f.txt"})),
        "x"
    );
    ok(&s, "move", &json!({"src": "copia", "dst": "a"}));
    assert_eq!(
        ok(&s, "read_file", &json!({"path": "a/copia/b/c/f.txt"})),
        "x"
    );
    let gone = ok(&s, "delete", &json!({"path": "a/copia"}));
    assert!(gone.starts_with("spostato nel cestino"), "{gone}");
    refused(&s, "read_file", &json!({"path": "a/copia/b/c/f.txt"}));
    assert_eq!(
        call(&s, "read_file", &json!({"path": "a/b/c/f.txt"})).text,
        "x"
    );
}

#[test]
fn find_files_matches_case_insensitively_and_skips_hidden_folders() {
    let scratch = Scratch::new();
    let s = server(&config(&scratch));
    ok(
        &s,
        "write_file",
        &json!({"path": "docs/Preventivo.TXT", "content": "x"}),
    );
    ok(
        &s,
        "write_file",
        &json!({"path": ".nascosta/preventivo2.txt", "content": "x"}),
    );
    ok(
        &s,
        "write_file",
        &json!({"path": "docs/altro.stl", "content": "x"}),
    );
    let by_word = ok(&s, "find_files", &json!({"pattern": "preventivo"}));
    assert!(
        by_word.contains("Preventivo.TXT") && !by_word.contains("preventivo2"),
        "{by_word}"
    );
    let by_glob = ok(&s, "find_files", &json!({"pattern": "*.stl"}));
    assert!(by_glob.contains("altro.stl"), "{by_glob}");
    assert!(
        ok(&s, "find_files", &json!({"pattern": "inesistente"})).starts_with("nessun file trovato")
    );
}

#[test]
fn limits_come_from_configuration() {
    let scratch = Scratch::new();
    let mut cfg = config(&scratch);
    cfg.text_limit = 5;
    cfg.list_limit = 2;
    cfg.find_limit = 1;
    if let Some(first) = cfg.roots.first_mut() {
        first.max_bytes = 20;
    }
    let s = server(&cfg);
    ok(
        &s,
        "write_file",
        &json!({"path": "g.txt", "content": "0123456789"}),
    );
    assert_eq!(
        ok(&s, "read_file", &json!({"path": "g.txt"})),
        "01234\n…(troncato)"
    );
    refused(
        &s,
        "write_file",
        &json!({"path": "grande.txt", "content": "x".repeat(21)}),
    );
    for n in 0..4 {
        ok(
            &s,
            "write_file",
            &json!({"path": format!("f{n}.txt"), "content": "x"}),
        );
    }
    assert_eq!(ok(&s, "list_dir", &json!({})).lines().count(), 3);
    assert_eq!(
        ok(&s, "find_files", &json!({"pattern": "f"}))
            .lines()
            .count(),
        1
    );
}

#[test]
fn unknown_tools_and_missing_arguments_are_refused() {
    let scratch = Scratch::new();
    let s = server(&config(&scratch));
    refused(&s, "format_disk", &json!({}));
    refused(&s, "read_file", &json!({}));
    refused(&s, "read_file", &json!({"path": "manca.txt"}));
}
