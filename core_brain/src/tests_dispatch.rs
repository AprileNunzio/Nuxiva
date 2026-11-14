use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::sync::Arc;
use std::time::Duration;

use nuxiva_agent_core::ceo::{Card, Index};
use nuxiva_agent_core::manifest::validate;
use nuxiva_mcp_core::{
    Catalog as McpCatalog, Hub, Isolation, MemorySink, PolicyConfig, Risk, Scope, ServerEntry,
    Settings as McpSettings, SharedSecrets, TransportSpec,
};
use nuxiva_swarm_core::{Catalog, Settings};

use crate::{BrainError, Dispatched, Dispatcher};

const SERVER: &str = r"
import sys, json
TOOLS = [{'name': 'lavoro', 'description': 'does work', 'annotations': {'readOnlyHint': True, 'openWorldHint': False},
  'inputSchema': {'type': 'object', 'properties': {'goal': {'type': 'string'}}, 'required': ['goal']}}]
for line in sys.stdin:
    m = json.loads(line)
    if 'id' not in m:
        continue
    if m['method'] == 'initialize':
        r = {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {'listChanged': True}}, 'serverInfo': {'name': 's', 'version': '1'}}
    elif m['method'] == 'tools/list':
        r = {'tools': TOOLS}
    elif m['method'] == 'tools/call':
        r = {'content': [{'type': 'text', 'text': 'fatto'}]}
    else:
        r = {}
    sys.stdout.write(json.dumps({'jsonrpc': '2.0', 'id': m['id'], 'result': r}) + '\n')
    sys.stdout.flush()
";

fn server_entry() -> ServerEntry {
    ServerEntry {
        id: "srv".into(),
        enabled: true,
        max_risk: Risk::Critical,
        honor_read_only: true,
        transport: TransportSpec::Stdio {
            program: "/usr/bin/env".into(),
            args: vec!["python3".into(), "-I".into(), "-c".into(), SERVER.into()],
            env: BTreeMap::from([("PATH".to_owned(), std::env::var("PATH").unwrap_or_default())]),
            secret_env: BTreeMap::new(),
            isolation: Isolation::Internal,
        },
    }
}

fn hub(with_server: bool) -> Arc<Hub> {
    let settings = McpSettings {
        request_timeout_ms: 5_000,
        ..McpSettings::default()
    };
    let hub = Hub::new(
        settings,
        PolicyConfig::default(),
        Arc::new(SharedSecrets::default()),
        Box::new(MemorySink::default()),
        None,
    )
    .expect("hub");
    hub.set_scopes(HashMap::from([(
        "casa".to_owned(),
        Scope {
            servers: vec!["*".into()],
            tools: vec!["*".into()],
            max_risk: Risk::Critical,
        },
    )]));
    if with_server {
        hub.apply_catalog(&McpCatalog {
            version: 1,
            serial: 1,
            issued_at: 0,
            not_after: u64::MAX / 2,
            servers: vec![server_entry()],
        })
        .expect("catalog");
    }
    Arc::new(hub)
}

fn dispatcher(hub: Arc<Hub>) -> Dispatcher {
    let settings = Settings::default();
    let raw = r#"{"id":"casa","name":"casa","capabilities":["Lavoro"],"tools":["lavoro"],"worker":{"kind":"mcp","concurrency_max":2,"needs_graph":false}}"#;
    let manifest = validate(raw, "casa", None).manifest.expect("manifest");
    let catalog = Catalog::build(&[manifest], &settings).expect("catalog");
    let declared = BTreeMap::from([("casa".to_owned(), BTreeSet::from(["lavoro".to_owned()]))]);
    let card = Card {
        id: "casa".into(),
        name: "casa".into(),
        description: "lavoro in casa".into(),
        keywords: vec!["lavoro".into(), "avvia".into()],
        capabilities: vec!["Lavoro".into()],
        nouns: vec!["lavoro".into()],
        phrases: vec![r"\blavoro\b".into()],
        ..Card::default()
    };
    Dispatcher::new(catalog, settings, Index::new(vec![card]), hub, declared).expect("dispatcher")
}

async fn ready(hub: &Hub) {
    for _ in 0..300 {
        if !hub.tools().is_empty() {
            return;
        }
        tokio::time::sleep(Duration::from_millis(20)).await;
    }
}

#[tokio::test]
async fn conversation_is_not_dispatched() {
    let d = dispatcher(hub(false));
    assert_eq!(
        d.dispatch("ciao come stai", "nunzio", 1).await,
        Ok(Dispatched::Conversation)
    );
}

#[tokio::test]
async fn rejects_unsafe_text() {
    let d = dispatcher(hub(false));
    assert_eq!(
        d.dispatch("", "nunzio", 1).await,
        Err(BrainError::Input("text"))
    );
    assert_eq!(
        d.dispatch("avvia\u{0}lavoro", "nunzio", 1).await,
        Err(BrainError::Input("text"))
    );
    assert_eq!(
        d.dispatch(&"a".repeat(9_000), "nunzio", 1).await,
        Err(BrainError::Input("text"))
    );
}

#[tokio::test]
async fn task_runs_through_swarm_and_mcp() {
    let hub = hub(true);
    ready(&hub).await;
    let d = dispatcher(Arc::clone(&hub));
    let out = d.dispatch("avvia il lavoro adesso", "nunzio", 1).await;
    assert!(
        matches!(&out, Ok(Dispatched::Executed { succeeded: true, acted: true, steps: 1.., text, .. }) if text == "fatto"),
        "{out:?}"
    );
}

#[tokio::test]
async fn missing_tool_fails_the_step_without_panicking() {
    let hub = hub(false);
    let d = dispatcher(hub);
    let out = d.dispatch("avvia il lavoro adesso", "nunzio", 1).await;
    assert!(
        matches!(
            out,
            Ok(Dispatched::Executed {
                succeeded: false,
                ..
            }) | Err(BrainError::Dispatch(_))
        ),
        "{out:?}"
    );
}

#[tokio::test]
async fn router_turns_heard_events_into_outcomes() {
    use crate::{Event, Layer, Outcome, route};
    let hub = hub(true);
    ready(&hub).await;
    let d = Arc::new(dispatcher(hub));
    let (etx, erx) = tokio::sync::mpsc::channel(8);
    let (otx, mut orx) = tokio::sync::mpsc::channel(8);
    let task = tokio::spawn(route(erx, d, otx));
    etx.send(Event::Dropped {
        layer: Layer::Gatekeeper,
        reason: "not_addressed",
    })
    .await
    .expect("send");
    etx.send(Event::Heard {
        speaker: Some("nunzio".into()),
        text: "avvia il lavoro adesso".into(),
        score: 0.9,
        at_ms: 5,
    })
    .await
    .expect("send");
    etx.send(Event::Fault(BrainError::Deadline))
        .await
        .expect("send");
    drop(etx);
    let mut seen = Vec::new();
    while let Some(o) = orx.recv().await {
        seen.push(o);
    }
    task.await.expect("join");
    assert!(seen.iter().any(|o| matches!(o, Outcome::Dropped { .. })));
    assert!(
        seen.iter()
            .any(|o| matches!(o, Outcome::Failed(BrainError::Deadline)))
    );
    assert!(
        seen.iter().any(|o| matches!(
            o,
            Outcome::Done(Dispatched::Executed {
                succeeded: true,
                ..
            })
        )),
        "{seen:?}"
    );
}

#[test]
fn arguments_follow_the_tool_schema() {
    use crate::arguments_for;
    use serde_json::json;
    let goal = json!({"type":"object","properties":{"goal":{"type":"string"}},"required":["goal"]});
    assert_eq!(
        arguments_for(&goal, "x").expect("a").get("goal"),
        Some(&json!("x"))
    );
    let sole = json!({"type":"object","properties":{"cosa":{"type":"string"},"n":{"type":"integer"}},"required":["cosa"]});
    assert!(arguments_for(&sole, "x").expect("a").contains_key("cosa"));
    let two = json!({"type":"object","properties":{"a":{"type":"string"},"b":{"type":"string"}},"required":["a","b"]});
    assert!(arguments_for(&two, "x").is_none());
    let extra = json!({"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer"}},"required":["query","limit"]});
    assert!(arguments_for(&extra, "x").is_none());
    assert!(arguments_for(&json!({"type":"object"}), "x").is_none());
}

#[tokio::test]
async fn tools_of_other_agents_are_never_used() {
    let hub = hub(true);
    ready(&hub).await;
    let settings = Settings::default();
    let raw = r#"{"id":"altro","name":"altro","capabilities":["Lavoro"],"worker":{"kind":"mcp","concurrency_max":2,"needs_graph":false}}"#;
    let manifest = validate(raw, "altro", None).manifest.expect("manifest");
    let catalog = Catalog::build(&[manifest], &settings).expect("catalog");
    let card = Card {
        id: "altro".into(),
        name: "altro".into(),
        capabilities: vec!["Lavoro".into()],
        nouns: vec!["lavoro".into()],
        phrases: vec![r"\blavoro\b".into()],
        ..Card::default()
    };
    let d = Dispatcher::new(
        catalog,
        settings,
        Index::new(vec![card]),
        hub,
        BTreeMap::new(),
    )
    .expect("d");
    let out = d.dispatch("avvia il lavoro adesso", "nunzio", 1).await;
    assert!(
        matches!(
            out,
            Ok(Dispatched::Executed {
                succeeded: false,
                ..
            }) | Err(BrainError::Dispatch(_))
        ),
        "{out:?}"
    );
}
