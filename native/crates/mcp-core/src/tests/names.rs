use crate::{McpError, canonical_name, valid_server_id};

#[test]
fn server_ids_are_validated() {
    assert!(valid_server_id("files-1"));
    assert!(!valid_server_id(""));
    assert!(!valid_server_id("-x"));
    assert!(!valid_server_id("Up"));
    assert!(!valid_server_id("a.b"));
    assert!(!valid_server_id(&"a".repeat(33)));
}

#[test]
fn canonical_names_are_stable_and_bounded() {
    assert_eq!(
        canonical_name("fs", "Read File!", 64).as_deref(),
        Ok("fs.read_file")
    );
    let long = "x".repeat(300);
    let first = canonical_name("fs", &long, 64);
    assert_eq!(first, canonical_name("fs", &long, 64));
    assert!(first.is_ok_and(|n| n.len() <= 64));
    let other = format!("{long}y");
    assert_ne!(
        canonical_name("fs", &long, 64),
        canonical_name("fs", &other, 64)
    );
}

#[test]
fn bad_names_are_rejected() {
    assert_eq!(canonical_name("Bad", "t", 64), Err(McpError::InvalidName));
    assert_eq!(canonical_name("fs", "!!!", 64), Err(McpError::InvalidName));
    assert_eq!(canonical_name("fs", "t", 5), Err(McpError::InvalidName));
}
