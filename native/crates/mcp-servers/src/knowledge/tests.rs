use std::sync::Arc;

use nuxiva_knowledge_core::{KnowledgeSettings, MasterKey, Service};
use nuxiva_mcp_core::ToolServer;
use serde_json::{Map, Value, json};

use super::KnowledgeServer;

fn server(who: Option<&'static str>) -> (KnowledgeServer, Arc<Service>) {
    let service = Arc::new(
        Service::new(
            KnowledgeSettings::default(),
            Some(Arc::new(MasterKey::from_key([4; 32]))),
            None,
            Arc::new(|| 1_800_000_000_000),
            false,
        )
        .unwrap_or_else(|_| unreachable!("service")),
    );
    let reg = json!({"op": "register", "id": "nunzio", "name": "Nunzio", "role": "family"});
    assert!(service.handle(&reg.to_string()).contains("true"));
    let identity: super::Identity = Arc::new(move || who.map(str::to_owned));
    (
        KnowledgeServer::new("knowledge", Arc::clone(&service), identity),
        service,
    )
}

fn args(value: &Value) -> Map<String, Value> {
    value.as_object().cloned().unwrap_or_default()
}

#[test]
fn learn_then_search_uses_bound_identity() {
    let (s, _) = server(Some("nunzio"));
    let learned = s.call("knowledge_learn", &args(&json!({"text": "Abito a Torino"})));
    assert!(!learned.is_error);
    let found = s.call("knowledge_search", &args(&json!({"text": "Torino"})));
    assert!(!found.is_error);
    assert!(found.text.contains("Torino"));
}

#[test]
fn missing_identity_fails_closed() {
    let (s, _) = server(None);
    let out = s.call("knowledge_search", &args(&json!({"text": "x"})));
    assert!(out.is_error);
    assert_eq!(out.text, "knowledge.identity");
}

#[test]
fn reveal_and_foreign_identity_arguments_are_not_forwarded() {
    let (s, _) = server(Some("nunzio"));
    let out = s.call(
        "knowledge_search",
        &args(&json!({"text": "x", "reveal": true, "as": "anna"})),
    );
    assert!(!out.is_error);
    let unknown = s.call("knowledge_erase", &args(&json!({})));
    assert!(unknown.is_error);
}

#[test]
fn tools_do_not_expose_erase_or_secrets() {
    let (s, _) = server(Some("nunzio"));
    let names: Vec<String> = s
        .tools()
        .iter()
        .filter_map(|t| t.get("name").and_then(Value::as_str).map(str::to_owned))
        .collect();
    assert!(
        names
            .iter()
            .all(|n| !n.contains("erase") && !n.contains("restore"))
    );
    assert!(names.contains(&"knowledge_correct".to_owned()));
}
