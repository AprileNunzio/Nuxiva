use std::sync::Arc;

use serde_json::{Value, json};

use crate::tests::get;
use crate::{KnowledgeSettings, MasterKey, Service, Vault};

fn service(vault: Option<Vault>) -> Service {
    Service::new(
        KnowledgeSettings::default(),
        Some(Arc::new(MasterKey::from_key([5; 32]))),
        vault,
        Arc::new(|| 1_800_000_000_000),
        true,
    )
    .unwrap_or_else(|_| unreachable!("service"))
}

fn call(s: &Service, request: &Value) -> Value {
    serde_json::from_str(&s.handle(&request.to_string())).unwrap_or(Value::Null)
}

fn setup(s: &Service) {
    for (id, role) in [
        ("nunzio", "family"),
        ("anna", "family"),
        ("ospite", "guest"),
    ] {
        let r = call(
            s,
            &json!({"op": "register", "id": id, "name": id, "role": role}),
        );
        assert_eq!(get(&r, "/ok"), true);
    }
}

#[test]
fn extract_store_search_cycle() {
    let s = service(None);
    setup(&s);
    let r = call(
        &s,
        &json!({"op": "extract", "as": "nunzio", "text": "Abito a Torino e mi piace il caffè"}),
    );
    assert_eq!(get(&r, "/ok"), true);
    assert_eq!(get(&r, "/data/report/created"), 2);
    let found = call(
        &s,
        &json!({"op": "search", "as": "nunzio", "query": {"text": "caffè"}}),
    );
    assert_eq!(get(&found, "/data/0/label"), "caffè");
    let stats = call(&s, &json!({"op": "stats", "as": "nunzio"}));
    assert_eq!(get(&stats, "/data/edges"), 2);
}

#[test]
fn strict_validation_rejects_unknown_fields_and_user_origin() {
    let s = service(None);
    setup(&s);
    let bad = call(&s, &json!({"op": "stats", "as": "nunzio", "extra": 1}));
    assert_eq!(get(&bad, "/error"), "knowledge.invalid");
    let forged = call(
        &s,
        &json!({"op": "remember", "as": "nunzio", "kind": "place", "label": "Roma", "origin": "user"}),
    );
    assert_eq!(get(&forged, "/error"), "knowledge.forbidden");
    let garbage = s.handle("{not json");
    assert!(garbage.contains("knowledge.invalid"));
    let huge = s.handle(&"x".repeat(crate::MAX_REQUEST + 1));
    assert!(huge.contains("knowledge.too_large"));
}

#[test]
fn export_and_erase_remove_everything() {
    let dir = std::env::temp_dir().join(format!("nkg-test-{}", std::process::id()));
    let key = Arc::new(MasterKey::from_key([5; 32]));
    let vault = Vault::new(&dir, key).unwrap_or_else(|_| unreachable!("vault"));
    let s = service(Some(vault));
    setup(&s);
    call(
        &s,
        &json!({"op": "remember", "as": "nunzio", "kind": "concept", "label": "pin", "detail": "9911", "level": "secret"}),
    );
    let export = call(&s, &json!({"op": "export", "as": "nunzio"}));
    assert_eq!(get(&export, "/data/nodes/0/detail"), "9911");
    let wrong = call(
        &s,
        &json!({"op": "erase", "as": "nunzio", "confirm": "yes"}),
    );
    assert_eq!(get(&wrong, "/error"), "knowledge.confirm");
    let done = call(
        &s,
        &json!({"op": "erase", "as": "nunzio", "confirm": "ERASE:nunzio"}),
    );
    assert_eq!(get(&done, "/data/file_removed"), true);
    assert_eq!(get(&done, "/data/receipt/nodes"), 1);
    let gone = call(&s, &json!({"op": "stats", "as": "nunzio"}));
    assert_eq!(get(&gone, "/error"), "knowledge.not_found");
    let files = std::fs::read_dir(&dir).map_or(99, Iterator::count);
    assert_eq!(files, 2);
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn vault_roundtrip_is_encrypted_and_tamper_evident() {
    let dir = std::env::temp_dir().join(format!("nkg-vault-{}", std::process::id()));
    let key = Arc::new(MasterKey::from_key([5; 32]));
    let vault = Vault::new(&dir, Arc::clone(&key)).unwrap_or_else(|_| unreachable!("vault"));
    let s = service(Some(vault));
    setup(&s);
    call(
        &s,
        &json!({"op": "extract", "as": "nunzio", "text": "Vivo a Bologna"}),
    );
    let files: Vec<_> = std::fs::read_dir(&dir)
        .map(|d| d.flatten().map(|e| e.path()).collect())
        .unwrap_or_default();
    let mine = format!("{}.nkg", key.file_name("nunzio").unwrap_or_default());
    let blob_path = files
        .iter()
        .find(|p| p.file_name().is_some_and(|n| n.to_string_lossy() == mine))
        .cloned();
    let blob = blob_path
        .as_ref()
        .and_then(|p| std::fs::read(p).ok())
        .unwrap_or_default();
    assert!(!String::from_utf8_lossy(&blob).contains("Bologna"));
    let fresh_vault = Vault::new(&dir, key).unwrap_or_else(|_| unreachable!("vault"));
    let fresh = service(Some(fresh_vault));
    assert_eq!(
        get(
            &call(&fresh, &json!({"op": "restore", "id": "nunzio"})),
            "/ok"
        ),
        true
    );
    let hits = call(
        &fresh,
        &json!({"op": "search", "as": "nunzio", "query": {"text": "Bologna"}}),
    );
    assert_eq!(get(&hits, "/data/0/label"), "Bologna");
    if let Some(path) = blob_path {
        let mut bytes = std::fs::read(&path).unwrap_or_default();
        if let Some(last) = bytes.last_mut() {
            *last ^= 0xff;
        }
        assert!(std::fs::write(&path, bytes).is_ok());
        let tampered = call(&fresh, &json!({"op": "restore", "id": "nunzio"}));
        assert_eq!(get(&tampered, "/error"), "knowledge.seal");
    }
    let _ = std::fs::remove_dir_all(&dir);
}
