use std::fs;
use std::path::PathBuf;
use std::time::Instant;

use crate::{Chain, DirScanner, Found, Inventory, InventoryError, Kind, Origin, Scanner, State};

fn found(id: &str, origin: Origin, body: &str) -> Found {
    Found::new(id, origin, body.as_bytes())
}

fn temp(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("inventory-{name}-{}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).expect("dir");
    dir
}

#[test]
fn system_items_are_active_and_foreign_items_start_degraded() {
    let mut inv = Inventory::default();
    inv.apply(
        Kind::Tool,
        &[
            found("a", Origin::System, "1"),
            found("g", Origin::Generated, "1"),
        ],
        0,
    );
    assert_eq!(inv.get(Kind::Tool, "a").expect("a").state, State::Active);
    let generated = inv.get(Kind::Tool, "g").expect("g");
    assert_eq!(generated.state, State::Degraded);
    assert!(!generated.verified);
    inv.verify(Kind::Tool, "g", 1).expect("verify");
    assert_eq!(inv.get(Kind::Tool, "g").expect("g").state, State::Active);
}

#[test]
fn change_bumps_generation_and_unverifies_foreign_items() {
    let mut inv = Inventory::default();
    inv.apply(Kind::Agent, &[found("g", Origin::User, "1")], 0);
    inv.verify(Kind::Agent, "g", 1).expect("verify");
    let before = inv.generation();
    let diff = inv.apply(Kind::Agent, &[found("g", Origin::User, "2")], 2);
    assert_eq!(diff.changed, vec!["g"]);
    assert!(inv.generation() > before);
    let item = inv.get(Kind::Agent, "g").expect("g");
    assert_eq!((item.state, item.verified), (State::Degraded, false));
}

#[test]
fn unchanged_scan_leaves_generation_alone() {
    let mut inv = Inventory::default();
    let set = [found("a", Origin::System, "1")];
    inv.apply(Kind::Tool, &set, 0);
    let generation = inv.generation();
    assert!(inv.apply(Kind::Tool, &set, 5).is_empty());
    assert_eq!(inv.generation(), generation);
}

#[test]
fn absent_items_degrade_then_revoke_after_grace() {
    let mut inv = Inventory::new(10_000);
    inv.apply(Kind::Node, &[found("n1", Origin::System, "x")], 0);
    let diff = inv.apply(Kind::Node, &[], 1_000);
    assert_eq!(diff.missing, vec!["n1"]);
    assert_eq!(inv.get(Kind::Node, "n1").expect("n").state, State::Degraded);
    let back = inv.apply(Kind::Node, &[found("n1", Origin::System, "x")], 2_000);
    assert_eq!(back.changed, vec!["n1"]);
    assert_eq!(inv.get(Kind::Node, "n1").expect("n").state, State::Active);
    inv.apply(Kind::Node, &[], 3_000);
    let gone = inv.apply(Kind::Node, &[], 13_000);
    assert_eq!(gone.revoked, vec!["n1"]);
    assert_eq!(inv.get(Kind::Node, "n1").expect("n").state, State::Revoked);
}

#[test]
fn revoked_items_do_not_come_back_by_reappearing() {
    let mut inv = Inventory::new(0);
    inv.apply(Kind::Tool, &[found("a", Origin::System, "1")], 0);
    inv.apply(Kind::Tool, &[], 1);
    assert_eq!(inv.get(Kind::Tool, "a").expect("a").state, State::Revoked);
    inv.apply(Kind::Tool, &[found("a", Origin::System, "1")], 2);
    assert_eq!(inv.get(Kind::Tool, "a").expect("a").state, State::Revoked);
    assert!(inv.verify(Kind::Tool, "a", 3).is_err());
}

#[test]
fn user_items_cannot_take_over_a_system_identifier() {
    let mut inv = Inventory::default();
    inv.apply(
        Kind::Tool,
        &[found("send_email", Origin::System, "real")],
        0,
    );
    let diff = inv.apply(
        Kind::Tool,
        &[found("send_email", Origin::Generated, "fake")],
        1,
    );
    assert_eq!(diff.rejected, vec!["send_email"]);
    let item = inv.get(Kind::Tool, "send_email").expect("item");
    assert_eq!((item.origin, item.state), (Origin::System, State::Active));
}

#[test]
fn duplicate_ids_in_one_scan_are_rejected() {
    let mut inv = Inventory::default();
    let diff = inv.apply(
        Kind::Widget,
        &[
            found("w", Origin::System, "1"),
            found("w", Origin::System, "2"),
        ],
        0,
    );
    assert_eq!(diff.added, vec!["w"]);
    assert_eq!(diff.rejected, vec!["w"]);
}

#[test]
fn kinds_do_not_interfere_with_each_other() {
    let mut inv = Inventory::new(0);
    inv.apply(Kind::Tool, &[found("x", Origin::System, "1")], 0);
    inv.apply(Kind::Widget, &[found("x", Origin::System, "1")], 0);
    inv.apply(Kind::Widget, &[], 1);
    assert_eq!(inv.get(Kind::Tool, "x").expect("t").state, State::Active);
    assert_eq!(inv.get(Kind::Widget, "x").expect("w").state, State::Revoked);
}

#[test]
fn a_plan_on_a_changed_inventory_is_rechecked() {
    let mut inv = Inventory::default();
    inv.apply(
        Kind::Tool,
        &[
            found("a", Origin::System, "1"),
            found("b", Origin::System, "1"),
        ],
        0,
    );
    let snapshot = inv.snapshot();
    inv.apply(
        Kind::Tool,
        &[
            found("a", Origin::System, "1"),
            found("b", Origin::System, "1"),
            found("c", Origin::System, "1"),
        ],
        1,
    );
    inv.check_plan(&snapshot, &[(Kind::Tool, "a"), (Kind::Tool, "b")])
        .expect("still valid");
    inv.apply(
        Kind::Tool,
        &[
            found("a", Origin::System, "2"),
            found("b", Origin::System, "1"),
            found("c", Origin::System, "1"),
        ],
        2,
    );
    assert_eq!(
        inv.check_plan(&snapshot, &[(Kind::Tool, "a")]),
        Err(InventoryError::Stale("a".into()))
    );
    assert!(inv.check_plan(&snapshot, &[(Kind::Tool, "c")]).is_err());
}

#[test]
fn audit_chain_detects_tampering() {
    let mut inv = Inventory::default();
    inv.apply(Kind::Tool, &[found("a", Origin::System, "1")], 0);
    inv.apply(Kind::Tool, &[found("a", Origin::System, "2")], 1);
    inv.apply(Kind::Tool, &[], 2);
    let mut entries = inv.audit().to_vec();
    assert!(entries.len() >= 3);
    assert!(Chain::verify(&entries));
    entries[1].event.push('x');
    assert!(!Chain::verify(&entries));
}

#[test]
fn directory_scanner_discovers_additions_and_removals() {
    let root = temp("dir");
    for name in ["alpha", "beta"] {
        fs::create_dir_all(root.join("cat").join(name)).expect("mk");
        fs::write(root.join("cat").join(name).join("feature.json"), b"{}").expect("w");
    }
    fs::create_dir_all(root.join("cat").join("Bad Name")).expect("mk");
    fs::write(
        root.join("cat").join("Bad Name").join("feature.json"),
        b"{}",
    )
    .expect("w");
    let scanner = DirScanner::new(Kind::Agent, root.clone(), Origin::System, "feature.json", 2);
    let mut inv = Inventory::new(0);
    let diff = inv.scan(&scanner, 0).expect("scan");
    assert_eq!(diff.added, vec!["alpha", "beta"]);
    fs::create_dir_all(root.join("cat").join("gamma")).expect("mk");
    fs::write(root.join("cat").join("gamma").join("feature.json"), b"{}").expect("w");
    fs::remove_dir_all(root.join("cat").join("alpha")).expect("rm");
    let diff = inv.scan(&scanner, 5).expect("scan");
    assert_eq!(diff.added, vec!["gamma"]);
    assert_eq!(diff.revoked, vec!["alpha"]);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn missing_root_is_empty_and_symlinked_manifests_are_ignored() {
    let scanner = DirScanner::new(
        Kind::Agent,
        PathBuf::from("/nonexistent/x"),
        Origin::User,
        "feature.json",
        2,
    );
    assert!(scanner.scan().expect("scan").is_empty());
    #[cfg(unix)]
    {
        let root = temp("link");
        fs::create_dir_all(root.join("evil")).expect("mk");
        fs::write(root.join("outside.json"), b"{}").expect("w");
        std::os::unix::fs::symlink(
            root.join("outside.json"),
            root.join("evil").join("feature.json"),
        )
        .expect("ln");
        let scanner = DirScanner::new(Kind::Agent, root.clone(), Origin::User, "feature.json", 1);
        assert!(scanner.scan().expect("scan").is_empty());
        let _ = fs::remove_dir_all(root);
    }
}

#[test]
fn scanning_five_thousand_capabilities_is_fast() {
    let mut inv = Inventory::default();
    let set: Vec<Found> = (0..5_000)
        .map(|i| found(&format!("tool_{i}"), Origin::System, &format!("v{i}")))
        .collect();
    inv.apply(Kind::Tool, &set, 0);
    let started = Instant::now();
    let diff = inv.apply(Kind::Tool, &set, 1);
    assert!(diff.is_empty());
    assert!(started.elapsed().as_millis() < 1_000);
    assert_eq!(inv.count(Kind::Tool), 5_000);
}
