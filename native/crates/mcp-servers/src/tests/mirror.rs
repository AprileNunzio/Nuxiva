use std::collections::HashMap;
use std::sync::Arc;
use std::sync::Mutex;
use std::time::Duration;

use serde_json::{Map, Value, json};
use tokio::runtime::Handle;

use nuxiva_mcp_core::{
    CallRequest, Catalog, Hub, McpError, MemorySink, PolicyConfig, Risk, Scope, ServerEntry,
    Settings, SharedSecrets, ToolOutput, TransportSpec,
};

use crate::{Dispatch, MirrorConfig, ServerDefinition, register_all};

type Seen = (String, String, Value, Option<String>);

#[derive(Debug, Default)]
struct Recorder {
    seen: Mutex<Vec<Seen>>,
}

impl Dispatch for Recorder {
    fn call(
        &self,
        server: &str,
        tool: &str,
        arguments: &Map<String, Value>,
        context: Option<&str>,
    ) -> ToolOutput {
        if let Ok(mut seen) = self.seen.lock() {
            seen.push((
                server.to_owned(),
                tool.to_owned(),
                Value::Object(arguments.clone()),
                context.map(str::to_owned),
            ));
        }
        ToolOutput::ok(format!("{tool}:{}", Value::Object(arguments.clone())))
    }
}

fn config() -> Value {
    json!({"tools": [
        {"name": "now", "description": "ora", "read_only": true},
        {"name": "greet", "description": "saluta", "read_only": true,
         "input_schema": {"type": "object", "properties": {"who": {"type": "string"}}, "required": ["who"], "additionalProperties": false}},
        {"name": "toggle", "description": "cambia", "destructive": false},
        {"name": "erase", "description": "cancella", "destructive": true}
    ]})
}

fn catalog() -> Catalog {
    Catalog {
        version: 1,
        serial: 1,
        issued_at: 0,
        not_after: u64::MAX / 2,
        servers: vec![ServerEntry {
            id: "mirror".into(),
            enabled: true,
            max_risk: Risk::Critical,
            honor_read_only: true,
            transport: TransportSpec::Internal {
                name: "mirror".into(),
            },
        }],
    }
}

fn request(tool: &str, arguments: &Value) -> CallRequest {
    CallRequest {
        tool: tool.into(),
        principal: "p".into(),
        agent: "butler".into(),
        operation: "op".into(),
        arguments: arguments.as_object().cloned().unwrap_or_default(),
        consent: None,
    }
}

async fn ready() -> Result<(Hub, Arc<Recorder>), McpError> {
    let recorder = Arc::new(Recorder::default());
    let hub = Hub::new(
        Settings::default(),
        PolicyConfig::default(),
        Arc::new(SharedSecrets::default()),
        Box::new(MemorySink::default()),
        None,
    )?;
    register_all(
        hub.internal(),
        &[ServerDefinition {
            id: "mirror".into(),
            kind: "mirror".into(),
            config: config(),
        }],
        &Handle::current(),
        1 << 20,
        8,
        Some(&(Arc::clone(&recorder) as Arc<dyn Dispatch>)),
    )?;
    hub.set_scopes(HashMap::from([(
        "butler".to_owned(),
        Scope {
            servers: vec!["mirror".into()],
            tools: vec!["mirror.*".into()],
            max_risk: Risk::Critical,
        },
    )]));
    hub.apply_catalog(&catalog())?;
    for _ in 0..200 {
        if hub.tools().len() >= 4 {
            break;
        }
        tokio::time::sleep(Duration::from_millis(20)).await;
    }
    Ok((hub, recorder))
}

#[tokio::test]
async fn mirrored_tools_are_listed_gated_and_dispatched() -> Result<(), McpError> {
    let (hub, recorder) = ready().await?;
    assert_eq!(hub.tools().len(), 4);
    let now = hub.call(request("mirror.now", &json!({}))).await?;
    assert_eq!(now.external.text, "now:{}");
    let greeted = hub
        .call(request("mirror.greet", &json!({"who": "Ada"})))
        .await?;
    assert_eq!(greeted.external.text, "greet:{\"who\":\"Ada\"}");
    let invalid = hub.call(request("mirror.greet", &json!({"who": 3}))).await;
    assert!(invalid.is_err());
    let extra = hub
        .call(request("mirror.greet", &json!({"who": "a", "x": 1})))
        .await;
    assert!(extra.is_err());
    assert_eq!(recorder.seen.lock().map_or(0, |s| s.len()), 2);
    let tagged = hub
        .call(request("mirror.now", &json!({"_context": "abc"})))
        .await?;
    assert_eq!(tagged.external.text, "now:{}");
    let last = recorder.seen.lock().ok().and_then(|s| s.last().cloned());
    assert_eq!(last.and_then(|l| l.3), Some("abc".to_owned()));
    assert!(
        hub.call(request("mirror.now", &json!({"_context": 5})))
            .await
            .is_err()
    );
    Ok(())
}

#[tokio::test]
async fn destructive_tools_need_consent_and_unknown_tools_are_refused() -> Result<(), McpError> {
    let (hub, recorder) = ready().await?;
    let erased = hub.call(request("mirror.erase", &json!({}))).await;
    assert_eq!(erased.err(), Some(McpError::ConsentRequired));
    assert!(hub.call(request("mirror.ghost", &json!({}))).await.is_err());
    assert_eq!(recorder.seen.lock().map_or(1, |s| s.len()), 0);
    Ok(())
}

#[test]
fn configuration_is_validated() {
    let parse = |v: Value| serde_json::from_value::<MirrorConfig>(v);
    assert!(parse(config()).is_ok_and(|c| c.validate().is_ok()));
    for bad in [
        json!({"tools": []}),
        json!({"tools": [{"name": "bad name"}]}),
        json!({"tools": [{"name": "a"}, {"name": "a"}]}),
        json!({"tools": [{"name": "a", "read_only": true, "destructive": true}]}),
        json!({"tools": [{"name": "a", "input_schema": {"type": "string"}}]}),
        json!({"tools": [{"name": "a", "input_schema": {"type": "object", "properties": {"_context": {"type": "string"}}}}]}),
    ] {
        assert!(parse(bad).is_ok_and(|c| c.validate().is_err()));
    }
    assert!(parse(json!({"tools": [{"name": "a", "unknown": 1}]})).is_err());
}

#[tokio::test]
async fn a_mirror_without_a_dispatcher_is_rejected() {
    let registry = nuxiva_mcp_core::InternalRegistry::default();
    let definition = ServerDefinition {
        id: "mirror".into(),
        kind: "mirror".into(),
        config: config(),
    };
    assert!(
        register_all(
            &registry,
            &[definition],
            &Handle::current(),
            1 << 20,
            8,
            None
        )
        .is_err()
    );
}
