use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;

use serde_json::{Map, json};
use tokio::runtime::Handle;

use nuxiva_mcp_core::{
    CallRequest, Catalog, Hub, McpError, McpResult, MemorySink, PolicyConfig, Risk, Scope,
    ServerEntry, Settings, SharedSecrets, TransportSpec,
};

use super::support::{Scratch, config};
use crate::{ServerDefinition, register_all};

fn definition(scratch: &Scratch) -> ServerDefinition {
    ServerDefinition {
        id: "files".into(),
        kind: "filesystem".into(),
        config: serde_json::to_value(config(scratch)).unwrap_or_default(),
    }
}

fn catalog() -> Catalog {
    Catalog {
        version: 1,
        serial: 1,
        issued_at: 0,
        not_after: u64::MAX / 2,
        servers: vec![ServerEntry {
            id: "files".into(),
            enabled: true,
            max_risk: Risk::Critical,
            honor_read_only: true,
            transport: TransportSpec::Internal {
                name: "files".into(),
            },
        }],
    }
}

fn request(tool: &str, arguments: &serde_json::Value) -> CallRequest {
    CallRequest {
        tool: tool.into(),
        principal: "p".into(),
        agent: "butler".into(),
        operation: "op".into(),
        arguments: arguments.as_object().cloned().unwrap_or_else(Map::new),
        consent: None,
    }
}

#[tokio::test]
async fn internal_servers_go_through_the_same_gate_as_external_ones() -> McpResult<()> {
    let scratch = Scratch::new();
    let hub = Hub::new(
        Settings::default(),
        PolicyConfig::default(),
        Arc::new(SharedSecrets::default()),
        Box::new(MemorySink::default()),
        None,
    )?;
    register_all(
        hub.internal(),
        &[definition(&scratch)],
        &Handle::current(),
        1 << 20,
        8,
        None,
    )?;
    hub.set_scopes(HashMap::from([(
        "butler".to_owned(),
        Scope {
            servers: vec!["files".into()],
            tools: vec!["files.*".into()],
            max_risk: Risk::Critical,
        },
    )]));
    hub.apply_catalog(&catalog())?;
    for _ in 0..200 {
        if hub.tools().len() >= 9 {
            break;
        }
        tokio::time::sleep(Duration::from_millis(20)).await;
    }
    let tools = hub.tools();
    assert_eq!(tools.len(), 9);
    let risk = |name: &str| tools.iter().find(|t| t.name == name).map(|t| t.risk);
    assert_eq!(risk("read_file"), Some(Risk::Personal));
    assert_eq!(risk("file_info"), Some(Risk::Home));
    assert_eq!(risk("write_file"), Some(Risk::Home));
    assert_eq!(risk("delete"), Some(Risk::Critical));
    let written = hub
        .call(request(
            "files.write_file",
            &json!({"path": "a.txt", "content": "ciao"}),
        ))
        .await?;
    assert!(!written.external.is_error, "{}", written.external.text);
    let read = hub
        .call(request("files.read_file", &json!({"path": "a.txt"})))
        .await?;
    assert_eq!(read.external.text, "ciao");
    let after_read = hub
        .call(request(
            "files.write_file",
            &json!({"path": "b.txt", "content": "x"}),
        ))
        .await;
    assert_eq!(after_read.err(), Some(McpError::ConsentRequired));
    let escape = hub
        .call(request(
            "files.write_file",
            &json!({"path": "../x.txt", "content": "x"}),
        ))
        .await;
    assert!(escape.is_err() || escape.is_ok_and(|o| o.external.is_error));
    Ok(())
}

#[tokio::test]
async fn unknown_kinds_and_bad_definitions_are_rejected_before_anything_is_registered() {
    let scratch = Scratch::new();
    let registry = nuxiva_mcp_core::InternalRegistry::default();
    let mut unknown = definition(&scratch);
    unknown.kind = "ignoto".into();
    assert!(register_all(&registry, &[unknown], &Handle::current(), 1 << 20, 8, None).is_err());
    let mut bad_id = definition(&scratch);
    bad_id.id = "Non Valido".into();
    assert!(register_all(&registry, &[bad_id], &Handle::current(), 1 << 20, 8, None).is_err());
    assert!(registry.open("files").is_err());
}
