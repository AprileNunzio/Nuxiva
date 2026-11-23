use super::{Access, ToolPermissions, normalize_host, normalize_path};

fn grants() -> ToolPermissions {
    ToolPermissions {
        read_paths: vec!["data".to_owned()],
        write_paths: vec!["out/reports".to_owned()],
        network_hosts: vec!["API.Example.com".to_owned()],
    }
    .normalized()
    .unwrap_or_default()
}

#[test]
fn rejects_traversal_and_malformed_scopes() {
    for bad in [
        "", "/etc", "a/../b", "..", "a//b", ".hidden", "a\\b", "a/./b", "a\0b",
    ] {
        assert!(normalize_path(bad).is_err(), "{bad:?}");
    }
    for bad in [
        "",
        "-a.com",
        "a..com",
        "exa mple.com",
        "a_b.com",
        "http://a.com",
    ] {
        assert!(normalize_host(bad).is_err(), "{bad:?}");
    }
    assert_eq!(normalize_path("a/b"), Ok("a/b".to_owned()));
}

#[test]
fn reads_and_writes_stay_inside_declared_scopes() {
    let p = grants();
    assert!(p.allows(Access::Read("data")));
    assert!(p.allows(Access::Read("data/catalog/items.json")));
    assert!(p.allows(Access::Read("out/reports/a.txt")));
    assert!(!p.allows(Access::Read("database/items.json")));
    assert!(!p.allows(Access::Read("../data")));
    assert!(p.allows(Access::Write("out/reports/a.txt")));
    assert!(!p.allows(Access::Write("data/items.json")));
    assert!(!p.allows(Access::Write("out/reports2/a.txt")));
    assert!(!p.allows(Access::Write("/etc/passwd")));
}

#[test]
fn network_matches_normalized_hosts_only() {
    let p = grants();
    assert!(p.allows(Access::Network("api.example.com")));
    assert!(p.allows(Access::Network("API.EXAMPLE.COM")));
    assert!(!p.allows(Access::Network("evil.example.com")));
    assert!(!p.allows(Access::Network("example.com")));
    assert!(!ToolPermissions::default().allows(Access::Network("api.example.com")));
}

#[test]
fn scope_count_is_bounded() {
    let many = ToolPermissions {
        read_paths: (0..20).map(|i| format!("d{i}")).collect(),
        ..ToolPermissions::default()
    };
    assert!(many.normalized().is_err());
}
