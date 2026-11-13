use std::sync::Arc;

use serde_json::{Map, json};
use tokio::sync::mpsc;

use super::fake;
use crate::{Implementation, Link, McpError, McpResult, Message, Session, Settings, pair};

fn client() -> Implementation {
    Implementation {
        name: "nuxiva".into(),
        version: "1".into(),
        title: None,
    }
}

async fn open(settings: Settings) -> McpResult<(Session, mpsc::UnboundedReceiver<String>, Link)> {
    let (client_link, server_link) = pair();
    let (seen_tx, seen_rx) = mpsc::unbounded_channel();
    let (spy_tx, spy_rx) = pair();
    let _ = spy_rx;
    fake::serve(server_link, seen_tx);
    let (session, init, profile) = Session::connect(client_link, settings, &client()).await?;
    assert_eq!(init.server_info.name, "fake");
    assert_eq!(profile.name, "2025-06-18");
    Ok((session, seen_rx, spy_tx))
}

#[tokio::test]
async fn connect_lists_paged_tools_and_counts_rejected() -> McpResult<()> {
    let (session, mut seen, _spy) = open(Settings::default()).await?;
    let listing = session.list_tools().await?;
    let names: Vec<&str> = listing.tools.iter().map(|t| t.name.as_str()).collect();
    assert_eq!(names, ["a", "b", "c"]);
    assert_eq!(listing.rejected, 1);
    assert_eq!(seen.recv().await.as_deref(), Some("initialize"));
    assert_eq!(
        seen.recv().await.as_deref(),
        Some("notifications/initialized")
    );
    Ok(())
}

#[tokio::test]
async fn call_returns_content() -> McpResult<()> {
    let (session, _seen, _spy) = open(Settings::default()).await?;
    let result = session.call_tool("echo", Map::new()).await?;
    assert!(!result.is_error);
    assert_eq!(result.content.len(), 1);
    Ok(())
}

#[tokio::test]
async fn silent_server_times_out_and_is_cancelled() -> McpResult<()> {
    let settings = Settings {
        request_timeout_ms: 80,
        ..Settings::default()
    };
    let (session, mut seen, _spy) = open(settings).await?;
    assert_eq!(
        session.call_tool("silent", Map::new()).await.err(),
        Some(McpError::Timeout)
    );
    let mut methods = Vec::new();
    while methods.last().map(String::as_str) != Some("notifications/cancelled") {
        match tokio::time::timeout(std::time::Duration::from_secs(2), seen.recv()).await {
            Ok(Some(method)) => methods.push(method),
            _ => break,
        }
    }
    assert_eq!(
        methods.last().map(String::as_str),
        Some("notifications/cancelled")
    );
    Ok(())
}

#[tokio::test]
async fn concurrent_calls_do_not_interfere() -> McpResult<()> {
    let (session, _seen, _spy) = open(Settings::default()).await?;
    let session = Arc::new(session);
    let mut tasks = Vec::new();
    for _ in 0..40 {
        let session = Arc::clone(&session);
        tasks.push(tokio::spawn(async move {
            session.call_tool("x", Map::new()).await
        }));
    }
    for task in tasks {
        assert!(task.await.map_err(|_| McpError::Closed)?.is_ok());
    }
    Ok(())
}

#[tokio::test]
async fn too_many_in_flight_is_rejected() -> McpResult<()> {
    let settings = Settings {
        max_in_flight: 1,
        request_timeout_ms: 300,
        ..Settings::default()
    };
    let (session, _seen, _spy) = open(settings).await?;
    let session = Arc::new(session);
    let slow = Arc::clone(&session);
    let first = tokio::spawn(async move { slow.call_tool("silent", Map::new()).await });
    tokio::time::sleep(std::time::Duration::from_millis(50)).await;
    assert_eq!(
        session.call_tool("x", Map::new()).await.err(),
        Some(McpError::Busy)
    );
    assert_eq!(
        first.await.map_err(|_| McpError::Closed)?.err(),
        Some(McpError::Timeout)
    );
    Ok(())
}

#[tokio::test]
async fn closed_peer_fails_requests_with_closed() -> McpResult<()> {
    let (client_link, mut server_link) = pair();
    let task = tokio::spawn(async move {
        let bytes = server_link.rx.recv().await.unwrap_or_default();
        let Ok(Message::Request(request)) = Message::parse(&bytes, fake::MAX) else {
            return;
        };
        let init = fake::answer("initialize", None).unwrap_or_default();
        let _ = server_link.tx.send(fake::reply(request.id, init)).await;
        let _ = server_link.rx.recv().await;
    });
    let (session, _, _) = Session::connect(client_link, Settings::default(), &client()).await?;
    task.await.map_err(|_| McpError::Closed)?;
    tokio::time::sleep(std::time::Duration::from_millis(50)).await;
    assert!(session.is_closed());
    assert_eq!(session.list_tools().await.err(), Some(McpError::Closed));
    Ok(())
}

#[tokio::test]
async fn server_notifications_and_pings_are_handled() -> McpResult<()> {
    let (client_link, mut server_link) = pair();
    let task = tokio::spawn(async move {
        let bytes = server_link.rx.recv().await.unwrap_or_default();
        let Ok(Message::Request(request)) = Message::parse(&bytes, fake::MAX) else {
            return None;
        };
        let init = fake::answer("initialize", None).unwrap_or_default();
        let _ = server_link.tx.send(fake::reply(request.id, init)).await;
        let _ = server_link.rx.recv().await;
        let ping = json!({"jsonrpc":"2.0","id":"p","method":"ping"}).to_string();
        let changed =
            json!({"jsonrpc":"2.0","method":"notifications/tools/list_changed"}).to_string();
        let _ = server_link.tx.send(changed.into_bytes()).await;
        let _ = server_link.tx.send(ping.into_bytes()).await;
        server_link.rx.recv().await
    });
    let (session, _, _) = Session::connect(client_link, Settings::default(), &client()).await?;
    let event = session.next_event().await;
    assert_eq!(
        event.map(|e| e.method).as_deref(),
        Some("notifications/tools/list_changed")
    );
    let pong = task
        .await
        .map_err(|_| McpError::Closed)?
        .unwrap_or_default();
    assert!(matches!(
        Message::parse(&pong, fake::MAX),
        Ok(Message::Response(_))
    ));
    Ok(())
}
