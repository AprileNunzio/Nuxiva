use std::sync::Arc;

use serde_json::{Map, Value, json};

use nuxiva_graph_core::{FileSource, GraphSettings, MemorySource};
use nuxiva_mcp_core::{InternalRegistry, McpError, ToolServer};

use crate::{GraphServer, ServerDefinition, register_with_source};

fn source() -> Arc<dyn FileSource> {
    let mut files = MemorySource::new();
    files.put("src/lib.rs", "mod util;\npub fn start() {}\n");
    files.put("src/util.rs", "pub fn helper() {}\n");
    files.put("docs/guide.md", "# Guida\nVedi `src/util.rs`.\n");
    Arc::new(files)
}

fn server() -> GraphServer {
    GraphServer::new("graph", &GraphSettings::default(), source()).expect("server")
}

fn args(value: &Value) -> Map<String, Value> {
    value.as_object().cloned().unwrap_or_default()
}

fn call(server: &GraphServer, tool: &str, value: &Value) -> (bool, Value) {
    let out = server.call(tool, &args(value));
    let parsed = serde_json::from_str(&out.text).unwrap_or(Value::String(out.text));
    (out.is_error, parsed)
}

#[test]
fn lists_the_read_only_tools() {
    let tools = server().tools();
    let names: Vec<&str> = tools
        .iter()
        .filter_map(|t| t.get("name").and_then(Value::as_str))
        .collect();
    assert_eq!(
        names,
        [
            "graph_sync",
            "graph_locate",
            "graph_neighbors",
            "graph_impact",
            "graph_path",
            "graph_pack"
        ]
    );
    assert!(
        tools
            .iter()
            .all(|t| t.pointer("/annotations/readOnlyHint") == Some(&Value::Bool(true)))
    );
}

#[test]
fn sync_reports_then_detects_no_change() {
    let server = server();
    let (error, first) = call(&server, "graph_sync", &json!({}));
    assert!(!error);
    assert_eq!(first["files"], 3);
    assert_eq!(first["added"], 3);
    let (_, second) = call(&server, "graph_sync", &json!({}));
    assert_eq!(second["added"], 0);
    assert_eq!(second["unchanged"], 3);
    assert_eq!(first["graph_ref"], second["graph_ref"]);
}

#[test]
fn queries_answer_without_an_explicit_sync() {
    let server = server();
    let (error, hits) = call(&server, "graph_locate", &json!({"query": "helper"}));
    assert!(!error);
    assert_eq!(hits[0]["name"], "helper");
    let (_, impact) = call(
        &server,
        "graph_impact",
        &json!({"target": "src/util.rs", "depth": 3}),
    );
    let paths: Vec<&str> = impact["items"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(|i| i["hit"]["path"].as_str())
        .collect();
    assert!(paths.contains(&"src/lib.rs") && paths.contains(&"docs/guide.md"));
    assert!(impact["graph_ref"].as_str().is_some_and(|r| r.len() == 16));
    let (_, near) = call(&server, "graph_neighbors", &json!({"target": "src/lib.rs"}));
    assert!(near["items"].as_array().is_some_and(|i| !i.is_empty()));
    let (_, route) = call(
        &server,
        "graph_path",
        &json!({"from": "src/lib.rs", "to": "src/util.rs"}),
    );
    assert_eq!(route.as_array().map(Vec::len), Some(2));
    let (_, pack) = call(
        &server,
        "graph_pack",
        &json!({"targets": ["src/util.rs"], "budget": 500}),
    );
    assert!(
        pack["text"]
            .as_str()
            .is_some_and(|t| t.contains("used_by: "))
    );
}

#[test]
fn bad_input_is_refused_without_panicking() {
    let server = server();
    for (tool, value) in [
        ("graph_locate", json!({})),
        ("graph_locate", json!({"query": 5})),
        ("graph_neighbors", json!({"target": ""})),
        ("graph_neighbors", json!({"target": "x".repeat(600)})),
        ("graph_impact", json!({"target": "inesistente"})),
        ("graph_path", json!({"from": "src/lib.rs"})),
        (
            "graph_path",
            json!({"from": "src/lib.rs", "to": "inesistente"}),
        ),
        ("graph_pack", json!({"targets": ["inesistente"]})),
        ("graph_pack", json!({})),
        ("graph_impact", json!({"target": "src/lib.rs", "depth": -3})),
        ("graph_delete", json!({})),
    ] {
        let out = server.call(tool, &args(&value));
        let sane = out.is_error || serde_json::from_str::<Value>(&out.text).is_ok();
        assert!(sane, "{tool} {value}");
    }
    assert!(call(&server, "graph_delete", &json!({})).0);
    assert!(call(&server, "graph_impact", &json!({"target": "inesistente"})).0);
}

#[test]
fn definition_needs_a_file_source_and_valid_settings() {
    let registry = InternalRegistry::default();
    let definition = ServerDefinition {
        id: "graph".into(),
        kind: "graph".into(),
        config: json!({}),
    };
    let handle = tokio::runtime::Handle::try_current();
    assert!(handle.is_err());
    let runtime = tokio::runtime::Builder::new_current_thread()
        .build()
        .expect("runtime");
    let missing = register_with_source(
        &registry,
        std::slice::from_ref(&definition),
        runtime.handle(),
        1 << 20,
        8,
        None,
        None,
    );
    assert_eq!(missing.err(), Some(McpError::InvalidSettings));
    let bad = ServerDefinition {
        config: json!({"max_files": 0}),
        ..definition.clone()
    };
    let invalid = register_with_source(
        &registry,
        &[bad],
        runtime.handle(),
        1 << 20,
        8,
        None,
        Some(&source()),
    );
    assert_eq!(invalid.err(), Some(McpError::InvalidSettings));
    let unknown = ServerDefinition {
        config: json!({"nope": 1}),
        ..definition.clone()
    };
    assert!(
        register_with_source(
            &registry,
            &[unknown],
            runtime.handle(),
            1 << 20,
            8,
            None,
            Some(&source())
        )
        .is_err()
    );
    assert!(
        register_with_source(
            &registry,
            &[definition],
            runtime.handle(),
            1 << 20,
            8,
            None,
            Some(&source())
        )
        .is_ok()
    );
}
