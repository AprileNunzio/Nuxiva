use std::collections::{BTreeMap, HashMap};
use std::sync::Arc;
use std::time::{Duration, Instant};

use serde_json::{Map, json};

use crate::{
    CallRequest, Catalog, Critic, ErrorBus, ErrorKind, ErrorPayload, Hub, Isolation, McpError,
    McpResult, MemorySink, PolicyConfig, Remedy, Risk, Scope, ServerEntry, Settings, SharedSecrets,
    ToolError, TransportSpec, Within, guarded,
};

const SERVER: &str = r"
import sys, json, time
TOOLS = [
  {'name': 'echo', 'description': 'echoes', 'annotations': {'readOnlyHint': True, 'openWorldHint': False},
   'inputSchema': {'type': 'object', 'properties': {'k': {'type': 'string'}}}},
  {'name': 'slow', 'description': 'waits', 'annotations': {'readOnlyHint': True, 'openWorldHint': False},
   'inputSchema': {'type': 'object', 'properties': {'seconds': {'type': 'number'}}}},
]
for line in sys.stdin:
    m = json.loads(line)
    if 'id' not in m:
        continue
    if m['method'] == 'initialize':
        r = {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 's', 'version': '1'}}
    elif m['method'] == 'tools/list':
        r = {'tools': TOOLS}
    elif m['method'] == 'tools/call':
        a = m['params']['arguments']
        if m['params']['name'] == 'slow':
            time.sleep(float(a.get('seconds', 0)))
        r = {'content': [{'type': 'text', 'text': m['params']['name']}]}
    else:
        r = {}
    sys.stdout.write(json.dumps({'jsonrpc': '2.0', 'id': m['id'], 'result': r}) + '\n')
    sys.stdout.flush()
";

fn entry() -> ServerEntry {
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

fn catalog() -> Catalog {
    Catalog {
        version: 1,
        serial: 1,
        issued_at: 0,
        not_after: u64::MAX / 2,
        servers: vec![entry()],
    }
}

fn hub_with(settings: Settings) -> McpResult<Arc<Hub>> {
    let hub = Hub::new(
        settings,
        PolicyConfig::default(),
        Arc::new(SharedSecrets::default()),
        Box::new(MemorySink::default()),
        None,
    )?;
    hub.set_scopes(HashMap::from([(
        "butler".to_owned(),
        Scope {
            servers: vec!["*".into()],
            tools: vec!["*".into()],
            max_risk: Risk::Critical,
        },
    )]));
    Ok(Arc::new(hub))
}

fn tuned() -> Settings {
    Settings {
        backoff_base_ms: 20,
        backoff_max_ms: 80,
        request_timeout_ms: 5_000,
        foreground_budget_ms: 300,
        ..Settings::default()
    }
}

fn request(tool: &str, agent: &str, seconds: f64) -> CallRequest {
    let mut arguments = Map::new();
    arguments.insert("seconds".into(), json!(seconds));
    CallRequest {
        tool: tool.into(),
        principal: "p".into(),
        agent: agent.into(),
        operation: format!("op-{tool}-{seconds}"),
        arguments,
        consent: None,
    }
}

async fn ready(hub: &Hub, count: usize) -> bool {
    for _ in 0..300 {
        if hub.tools().len() >= count {
            return true;
        }
        tokio::time::sleep(Duration::from_millis(20)).await;
    }
    false
}

fn payload(component: &str, code: &str) -> ErrorPayload {
    let bus = ErrorBus::new(4);
    bus.report(component, code, "ctx");
    bus.drain().remove(0)
}

#[test]
fn typed_errors_classify_and_round_trip() -> Result<(), serde_json::Error> {
    let timeout = ToolError::new(McpError::Timeout, "s.t");
    assert_eq!(
        (timeout.kind, timeout.retryable),
        (ErrorKind::Timeout, true)
    );
    let denied = ToolError::new(McpError::NotPermitted, "s.t");
    assert_eq!((denied.kind, denied.retryable), (ErrorKind::Denied, false));
    assert_eq!(
        ToolError::from_code("mcp.consent.required", "s.t").kind,
        ErrorKind::ConsentRequired
    );
    assert_eq!(
        ToolError::from_code("sconosciuto", "s.t").kind,
        ErrorKind::Internal
    );
    let text = serde_json::to_string(&timeout)?;
    assert_eq!(serde_json::from_str::<ToolError>(&text)?, timeout);
    let hostile = text.replace('{', "{\"extra\":1,");
    assert!(serde_json::from_str::<ToolError>(&hostile).is_err());
    Ok(())
}

#[test]
fn the_error_bus_is_bounded_and_hashes_without_secrets() {
    let bus = ErrorBus::new(2);
    for n in 0..5 {
        bus.report("call:srv", "mcp.timeout", &format!("tool{n}"));
    }
    let drained = bus.drain();
    assert_eq!(drained.len(), 2);
    assert_eq!(bus.dropped(), 3);
    assert_eq!(drained.first().map(|p| p.hash.len()), Some(64));
    assert_ne!(
        drained.first().map(|p| p.hash.clone()),
        drained.last().map(|p| p.hash.clone())
    );
    assert!(bus.drain().is_empty());
}

#[tokio::test]
async fn a_panicking_task_is_reported_and_an_aborted_one_stops() {
    let bus = Arc::new(ErrorBus::new(8));
    let handle = guarded(Arc::clone(&bus), "task:srv".into(), "boom".into(), async {
        std::panic::resume_unwind(Box::new("injected failure"));
    });
    let _ = handle.await;
    let reports = bus.drain();
    assert_eq!(reports.len(), 1);
    assert_eq!(reports.first().map(|p| p.code.as_str()), Some("panic"));
    let ticking = Arc::new(std::sync::atomic::AtomicU64::new(0));
    let counter = Arc::clone(&ticking);
    let long = guarded(
        Arc::clone(&bus),
        "task:srv".into(),
        String::new(),
        async move {
            loop {
                counter.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                tokio::time::sleep(Duration::from_millis(5)).await;
            }
        },
    );
    tokio::time::sleep(Duration::from_millis(30)).await;
    long.abort();
    let _ = long.await;
    tokio::time::sleep(Duration::from_millis(30)).await;
    let frozen = ticking.load(std::sync::atomic::Ordering::Relaxed);
    tokio::time::sleep(Duration::from_millis(60)).await;
    assert_eq!(ticking.load(std::sync::atomic::Ordering::Relaxed), frozen);
    assert!(bus.drain().is_empty());
}

#[test]
fn the_critic_only_proposes_remedies_from_the_closed_catalog() {
    let settings = Settings {
        critic_threshold: 3,
        critic_window_ms: 1_000,
        ..Settings::default()
    };
    let mut critic = Critic::new(&settings);
    let start = Instant::now();
    assert_eq!(
        critic.advise(&payload("task:srv", "panic"), start),
        Some(Remedy::RestartServer("srv".into()))
    );
    for n in 0..2 {
        assert_eq!(
            critic.advise(
                &payload("call:srv", "mcp.timeout"),
                start + Duration::from_millis(n)
            ),
            None
        );
    }
    assert_eq!(
        critic.advise(
            &payload("call:srv", "mcp.timeout"),
            start + Duration::from_millis(3)
        ),
        Some(Remedy::RestartServer("srv".into()))
    );
    for n in 0..2 {
        assert_eq!(
            critic.advise(
                &payload("call:srv", "mcp.output.invalid"),
                start + Duration::from_millis(n)
            ),
            None
        );
    }
    assert_eq!(
        critic.advise(
            &payload("call:srv", "mcp.output.invalid"),
            start + Duration::from_millis(5)
        ),
        Some(Remedy::QuarantineServer("srv".into()))
    );
    for n in 0..5 {
        assert_eq!(
            critic.advise(
                &payload("call:srv", "mcp.timeout"),
                start + Duration::from_secs(10).saturating_mul(n + 1)
            ),
            None
        );
    }
    assert_eq!(
        critic.advise(&payload("audit", "mcp.audit.chain_broken"), start),
        None
    );
    assert_eq!(critic.advise(&payload("server:", "panic"), start), None);
}

#[tokio::test]
async fn slow_calls_become_jobs_and_never_hold_the_caller_past_the_budget() -> McpResult<()> {
    let hub = hub_with(tuned())?;
    hub.apply_catalog(&catalog())?;
    assert!(ready(&hub, 2).await);
    let fast = hub.call_within(request("srv.echo", "butler", 0.0)).await?;
    assert!(matches!(fast, Within::Done(_)));
    let started = Instant::now();
    let slow = hub.call_within(request("srv.slow", "butler", 1.0)).await?;
    assert!(started.elapsed() < Duration::from_millis(900));
    let Within::Pending(id) = slow else {
        return Err(McpError::Closed);
    };
    assert_eq!(hub.poll(&id, "butler")?.state, "running");
    assert_eq!(
        hub.poll(&id, "intruder").err(),
        Some(McpError::NotPermitted)
    );
    assert_eq!(hub.running_jobs(), 1);
    let mut finished = None;
    for _ in 0..200 {
        let view = hub.poll(&id, "butler")?;
        if view.state != "running" {
            finished = Some(view);
            break;
        }
        tokio::time::sleep(Duration::from_millis(20)).await;
    }
    let view = finished.ok_or(McpError::Timeout)?;
    assert_eq!(view.state, "done");
    assert_eq!(
        view.output.map(|o| o.external.text),
        Some("slow".to_owned())
    );
    assert_eq!(hub.running_jobs(), 0);
    hub.shutdown();
    Ok(())
}

#[tokio::test]
async fn jobs_can_be_cancelled_are_bounded_and_expire() -> McpResult<()> {
    let settings = Settings {
        max_jobs: 1,
        job_ttl_ms: 100,
        ..tuned()
    };
    let hub = hub_with(settings)?;
    hub.apply_catalog(&catalog())?;
    assert!(ready(&hub, 2).await);
    let Within::Pending(first) = hub.call_within(request("srv.slow", "butler", 3.0)).await? else {
        return Err(McpError::Closed);
    };
    assert_eq!(
        hub.submit(request("srv.echo", "butler", 0.0)).err(),
        Some(McpError::Busy)
    );
    hub.cancel(&first, "butler")?;
    assert_eq!(hub.poll(&first, "butler")?.state, "cancelled");
    assert_eq!(hub.running_jobs(), 0);
    tokio::time::sleep(Duration::from_millis(200)).await;
    assert_eq!(
        hub.poll(&first, "butler").err(),
        Some(McpError::UnknownTool)
    );
    assert_eq!(
        hub.cancel("job-999", "butler").err(),
        Some(McpError::UnknownTool)
    );
    hub.shutdown();
    Ok(())
}

#[tokio::test]
async fn an_injected_error_reaches_the_critic_and_heals_within_a_second() -> McpResult<()> {
    let hub = hub_with(tuned())?;
    hub.apply_catalog(&catalog())?;
    assert!(ready(&hub, 2).await);
    let started = Instant::now();
    hub.report("task:srv", "panic", "injected");
    let report = hub.heal();
    assert!(started.elapsed() < Duration::from_secs(1));
    assert_eq!(report.errors.len(), 1);
    assert_eq!(report.remedies, vec![Remedy::RestartServer("srv".into())]);
    assert!(ready(&hub, 2).await);
    let after = hub.call_within(request("srv.echo", "butler", 0.0)).await?;
    assert!(matches!(after, Within::Done(_)));
    hub.shutdown();
    Ok(())
}

#[tokio::test]
async fn repeated_bad_output_quarantines_until_an_administrator_releases() -> McpResult<()> {
    let hub = hub_with(tuned())?;
    hub.apply_catalog(&catalog())?;
    assert!(ready(&hub, 2).await);
    for _ in 0..3 {
        hub.report("call:srv", "mcp.output.invalid", "srv.echo");
    }
    let report = hub.heal();
    assert_eq!(
        report.remedies,
        vec![Remedy::QuarantineServer("srv".into())]
    );
    assert_eq!(hub.quarantined(), vec!["srv".to_owned()]);
    assert!(hub.tools().is_empty());
    hub.apply_catalog(&catalog())?;
    assert!(hub.tools().is_empty());
    hub.release_quarantine("srv")?;
    assert!(ready(&hub, 2).await);
    assert!(hub.quarantined().is_empty());
    hub.shutdown();
    Ok(())
}

#[tokio::test]
async fn failing_calls_feed_the_error_bus() -> McpResult<()> {
    let settings = Settings {
        request_timeout_ms: 200,
        ..tuned()
    };
    let hub = hub_with(settings)?;
    hub.apply_catalog(&catalog())?;
    assert!(ready(&hub, 2).await);
    let outcome = hub.call(request("srv.slow", "butler", 1.5)).await;
    assert_eq!(outcome.err(), Some(McpError::Timeout));
    let report = hub.heal();
    assert!(
        report
            .errors
            .iter()
            .any(|p| p.component == "call:srv" && p.code == "mcp.timeout")
    );
    assert!(report.errors.iter().all(|p| !p.hash.is_empty()));
    hub.shutdown();
    Ok(())
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn chaos_a_flapping_server_never_hangs_callers_or_the_hub() -> McpResult<()> {
    let hub = hub_with(tuned())?;
    hub.apply_catalog(&catalog())?;
    assert!(ready(&hub, 2).await);
    let started = Instant::now();
    let mut calls = Vec::new();
    for index in 0..60 {
        let hub = Arc::clone(&hub);
        calls.push(tokio::spawn(async move {
            hub.call_within(request("srv.echo", "butler", f64::from(index)))
                .await
        }));
    }
    let chaos = {
        let hub = Arc::clone(&hub);
        tokio::spawn(async move {
            for _ in 0..8 {
                let _ = hub.restart_server("srv");
                tokio::time::sleep(Duration::from_millis(40)).await;
            }
        })
    };
    let mut finished = 0usize;
    for call in calls {
        tokio::time::timeout(Duration::from_secs(20), call)
            .await
            .map_err(|_| McpError::Timeout)?
            .map_err(|_| McpError::Closed)?
            .ok();
        finished += 1;
    }
    let _ = chaos.await;
    assert_eq!(finished, 60);
    assert!(started.elapsed() < Duration::from_secs(25));
    let metrics = hub.metrics();
    assert_eq!(metrics.servers, 1);
    assert!(hub.heal().errors.len() <= 256);
    for _ in 0..100 {
        if hub.metrics().healthy == 1 {
            break;
        }
        tokio::time::sleep(Duration::from_millis(100)).await;
    }
    assert_eq!(hub.metrics().healthy, 1);
    let mut after = hub.call_within(request("srv.echo", "butler", 0.0)).await;
    for _ in 0..100 {
        if !matches!(after, Err(McpError::RateLimited)) {
            break;
        }
        tokio::time::sleep(Duration::from_millis(100)).await;
        after = hub.call_within(request("srv.echo", "butler", 0.0)).await;
    }
    assert!(matches!(after?, Within::Done(_)));
    Ok(())
}
