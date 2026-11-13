use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;

use serde_json::json;
use tokio::sync::{Mutex, mpsc};

use super::dynamic::{Control, Tools, serve, tool_with};
use crate::{
    Health, Implementation, Link, McpError, McpResult, Registry, Risk, ServerHandle, Settings,
    pair, spawn_server,
};

fn client() -> Implementation {
    Implementation {
        name: "nuxiva".into(),
        version: "1".into(),
        title: None,
    }
}

fn fast() -> Settings {
    Settings {
        backoff_base_ms: 20,
        backoff_max_ms: 80,
        backoff_jitter_pct: 0,
        refresh_debounce_ms: 10,
        refresh_interval_ms: 60_000,
        stale_retire_ms: 60_000,
        breaker_failures: 1_000,
        request_timeout_ms: 500,
        ..Settings::default()
    }
}

fn schema() -> serde_json::Value {
    json!({"type":"object"})
}

async fn until<F: Fn() -> bool>(limit: Duration, check: F) -> bool {
    let Some(end) = tokio::time::Instant::now().checked_add(limit) else {
        return check();
    };
    while tokio::time::Instant::now() < end {
        if check() {
            return true;
        }
        tokio::time::sleep(Duration::from_millis(10)).await;
    }
    check()
}

struct Rig {
    registry: Arc<Registry>,
    handle: ServerHandle,
    tools: Tools,
    controls: Arc<Mutex<Vec<mpsc::Sender<Control>>>>,
    connects: Arc<AtomicUsize>,
}

fn rig(settings: Settings, fail_first: usize) -> McpResult<Rig> {
    let registry = Arc::new(Registry::new(settings.clone()));
    let tools = Tools::default();
    tools.set(vec![tool_with("a", schema()), tool_with("b", schema())]);
    let controls: Arc<Mutex<Vec<mpsc::Sender<Control>>>> = Arc::new(Mutex::new(Vec::new()));
    let connects = Arc::new(AtomicUsize::new(0));
    let (tools_c, controls_c, connects_c) =
        (tools.clone(), Arc::clone(&controls), Arc::clone(&connects));
    let connect = move || {
        let (tools, controls, connects) = (
            tools_c.clone(),
            Arc::clone(&controls_c),
            Arc::clone(&connects_c),
        );
        async move {
            let attempt = connects.fetch_add(1, Ordering::SeqCst);
            if attempt < fail_first {
                return Err::<Link, McpError>(McpError::Io);
            }
            let (client_link, server_link) = pair();
            controls.lock().await.push(serve(server_link, tools));
            Ok(client_link)
        }
    };
    let handle = spawn_server(
        "srv",
        connect,
        Arc::clone(&registry),
        settings,
        client(),
        Arc::new(|_| Risk::Home),
    )?;
    Ok(Rig {
        registry,
        handle,
        tools,
        controls,
        connects,
    })
}

#[tokio::test]
async fn server_becomes_ready_and_publishes_tools() -> McpResult<()> {
    let rig = rig(fast(), 0)?;
    let registry = Arc::clone(&rig.registry);
    assert!(until(Duration::from_secs(2), || registry.snapshot().len() == 2).await);
    assert!(
        until(Duration::from_secs(2), || rig.handle.status.borrow().health
            == Health::Ready)
        .await
    );
    assert_eq!(rig.handle.status.borrow().tools, 2);
    Ok(())
}

#[tokio::test]
async fn list_changed_updates_the_registry_quickly() -> McpResult<()> {
    let rig = rig(fast(), 0)?;
    let registry = Arc::clone(&rig.registry);
    assert!(until(Duration::from_secs(2), || registry.snapshot().len() == 2).await);
    rig.tools.set(vec![
        tool_with("a", schema()),
        tool_with("c", schema()),
        tool_with("d", schema()),
    ]);
    let control = rig
        .controls
        .lock()
        .await
        .first()
        .cloned()
        .ok_or(McpError::Closed)?;
    control
        .send(Control::Changed)
        .await
        .map_err(|_| McpError::Closed)?;
    assert!(
        until(Duration::from_secs(1), || {
            let snapshot = registry.snapshot();
            snapshot.get("srv.c").is_some() && snapshot.get("srv.b").is_none()
        })
        .await
    );
    Ok(())
}

#[tokio::test]
async fn dropped_server_goes_stale_then_reconnects() -> McpResult<()> {
    let rig = rig(fast(), 0)?;
    let registry = Arc::clone(&rig.registry);
    assert!(
        until(Duration::from_secs(2), || registry
            .snapshot()
            .callable("srv.a")
            .is_some())
        .await
    );
    let control = rig
        .controls
        .lock()
        .await
        .first()
        .cloned()
        .ok_or(McpError::Closed)?;
    control
        .send(Control::Kill)
        .await
        .map_err(|_| McpError::Closed)?;
    assert!(
        until(Duration::from_secs(2), || rig
            .connects
            .load(Ordering::SeqCst)
            >= 2)
        .await
    );
    assert!(
        until(Duration::from_secs(2), || registry
            .snapshot()
            .callable("srv.a")
            .is_some())
        .await
    );
    assert!(
        until(Duration::from_secs(2), || rig.handle.status.borrow().health
            == Health::Ready)
        .await
    );
    Ok(())
}

#[tokio::test]
async fn connect_failures_back_off_then_recover() -> McpResult<()> {
    let rig = rig(fast(), 3)?;
    let registry = Arc::clone(&rig.registry);
    assert!(until(Duration::from_secs(3), || registry.snapshot().len() == 2).await);
    assert!(rig.connects.load(Ordering::SeqCst) >= 4);
    Ok(())
}

#[tokio::test]
async fn repeated_failures_trip_the_breaker() -> McpResult<()> {
    let settings = Settings {
        breaker_failures: 2,
        breaker_window_ms: 60_000,
        backoff_max_ms: 200,
        ..fast()
    };
    let rig = rig(settings, usize::MAX)?;
    assert!(
        until(Duration::from_secs(3), || rig.handle.status.borrow().health
            == Health::Quarantined)
        .await
    );
    assert_eq!(rig.handle.status.borrow().last_error, Some(McpError::Io));
    assert!(rig.registry.snapshot().is_empty());
    Ok(())
}

#[tokio::test]
async fn invalid_server_id_is_refused() {
    let registry = Arc::new(Registry::new(fast()));
    let connect = || async { Err::<Link, McpError>(McpError::Io) };
    let outcome = spawn_server(
        "Bad Id",
        connect,
        registry,
        fast(),
        client(),
        Arc::new(|_| Risk::Home),
    );
    assert_eq!(outcome.err(), Some(McpError::InvalidName));
}
