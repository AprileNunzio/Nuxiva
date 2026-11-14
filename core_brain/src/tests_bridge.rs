use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;

use futures_util::SinkExt;
use nuxiva_mcp_core::{
    Catalog as McpCatalog, Hub, MemorySink, PolicyConfig, Settings as McpSettings, SharedSecrets,
    generate_signing_key, sign_catalog,
};
use nuxiva_swarm_core::Settings;
use tokio::net::TcpListener;
use tokio_tungstenite::tungstenite::Message;

use crate::{
    BrainError, EarEndpoint, Event, apply_signed_catalog, load_agents, parse_ear, run_ear,
};

fn scratch(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("core_brain_{name}_{}", std::process::id()));
    std::fs::create_dir_all(&dir).expect("dir");
    dir
}

fn hub() -> Hub {
    Hub::new(
        McpSettings::default(),
        PolicyConfig::default(),
        Arc::new(SharedSecrets::default()),
        Box::new(MemorySink::default()),
        None,
    )
    .expect("hub")
}

fn write_catalog(dir: &Path, serial: u64, expired: bool) -> PathBuf {
    let key = generate_signing_key().expect("key");
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .expect("time")
        .as_secs();
    let catalog = McpCatalog {
        version: 1,
        serial,
        issued_at: now - 1_000,
        not_after: if expired { now - 10 } else { now + 3_600 },
        servers: Vec::new(),
    };
    let signed = sign_catalog(&catalog, &key).expect("sign");
    std::fs::write(
        dir.join("catalog.json"),
        serde_json::to_vec(&signed).expect("json"),
    )
    .expect("write");
    std::fs::write(
        dir.join("public.hex"),
        hex::encode(key.verifying_key().to_bytes()),
    )
    .expect("write");
    dir.join("catalog.json")
}

#[test]
fn ear_endpoint_must_be_loopback() {
    assert_eq!(
        EarEndpoint::loopback("127.0.0.1", 8093).expect("ok").url(),
        "ws://127.0.0.1:8093"
    );
    assert!(EarEndpoint::loopback("::1", 8093).is_ok());
    assert!(EarEndpoint::loopback("192.168.1.5", 8093).is_err());
    assert!(EarEndpoint::loopback("0.0.0.0", 8093).is_err());
    assert!(EarEndpoint::loopback("example.com", 8093).is_err());
    assert!(EarEndpoint::loopback("127.0.0.1", 0).is_err());
}

#[test]
fn parse_trusts_only_known_valid_speakers() {
    let known = r#"{"type":"transcript","text":"accendi la luce","speaker":"nunzio","speaker_score":0.91,"voice_known":true}"#;
    let Ok(Some(Event::Heard { speaker, score, .. })) = parse_ear(known, 5) else {
        panic!("heard");
    };
    assert_eq!(speaker.as_deref(), Some("nunzio"));
    assert!((score - 0.91).abs() < 1e-6);
    let unknown =
        r#"{"type":"transcript","text":"accendi","speaker":"nunzio","voice_known":false}"#;
    assert!(matches!(
        parse_ear(unknown, 5),
        Ok(Some(Event::Heard { speaker: None, .. }))
    ));
    let forged = r#"{"type":"transcript","text":"accendi","speaker":"../x","voice_known":true}"#;
    assert!(matches!(
        parse_ear(forged, 5),
        Ok(Some(Event::Heard { speaker: None, .. }))
    ));
    assert_eq!(parse_ear(r#"{"type":"mode","mode":"idle"}"#, 5), Ok(None));
    assert_eq!(parse_ear("not json", 5), Err(BrainError::Input("ear_json")));
    assert_eq!(
        parse_ear(r#"{"type":"transcript","text":""}"#, 5),
        Err(BrainError::Input("ear_text"))
    );
    assert_eq!(
        parse_ear("{\"type\":\"transcript\",\"text\":\"a\\u0000b\"}", 5),
        Err(BrainError::Input("ear_text"))
    );
    let huge = format!(r#"{{"type":"transcript","text":"{}"}}"#, "a".repeat(9_000));
    assert_eq!(parse_ear(&huge, 5), Err(BrainError::Input("ear_text")));
}

#[test]
fn signed_catalog_is_verified_and_replay_is_refused() {
    let dir = scratch("catalog");
    let catalog = write_catalog(&dir, 7, false);
    let key = dir.join("public.hex");
    let hub = hub();
    assert_eq!(apply_signed_catalog(&hub, &catalog, &key, 0), Ok(7));
    assert!(apply_signed_catalog(&hub, &catalog, &key, 8).is_err());
    std::fs::write(&key, "00".repeat(32)).expect("write");
    assert!(apply_signed_catalog(&hub, &catalog, &key, 0).is_err());
    std::fs::write(&key, "zz").expect("write");
    assert_eq!(
        apply_signed_catalog(&hub, &catalog, &key, 0),
        Err(BrainError::Input("catalog_key"))
    );
    assert_eq!(
        apply_signed_catalog(&hub, &dir.join("missing.json"), &key, 0),
        Err(BrainError::Input("catalog_missing"))
    );
}

#[test]
fn expired_catalog_is_refused() {
    let dir = scratch("expired");
    let catalog = write_catalog(&dir, 1, true);
    assert!(apply_signed_catalog(&hub(), &catalog, &dir.join("public.hex"), 0).is_err());
}

#[test]
fn agents_come_from_the_existing_registry() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../installer_wizard/agenti");
    let (catalog, _index) = load_agents(&root, &Settings::default()).expect("agents");
    assert!(!catalog.is_empty());
}

#[tokio::test]
async fn ear_link_turns_transcripts_into_events_and_stops() {
    let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
    let port = listener.local_addr().expect("addr").port();
    let server = tokio::spawn(async move {
        let (tcp, _) = listener.accept().await.expect("accept");
        let mut ws = tokio_tungstenite::accept_async(tcp)
            .await
            .expect("handshake");
        ws.send(Message::text(r#"{"type":"mode","mode":"idle"}"#))
            .await
            .expect("send");
        ws.send(Message::text(
            r#"{"type":"transcript","text":"spegni la luce","speaker":"nunzio","speaker_score":0.8,"voice_known":true}"#,
        ))
        .await
        .expect("send");
        tokio::time::sleep(Duration::from_millis(300)).await;
    });
    let (tx, mut rx) = tokio::sync::mpsc::channel(8);
    let (stop_tx, stop_rx) = tokio::sync::watch::channel(false);
    let endpoint = EarEndpoint::loopback("127.0.0.1", port).expect("endpoint");
    let link = tokio::spawn(run_ear(endpoint, tx, stop_rx));
    let event = tokio::time::timeout(Duration::from_secs(5), rx.recv())
        .await
        .expect("timeout")
        .expect("event");
    assert!(matches!(event, Event::Heard { speaker: Some(ref s), .. } if s == "nunzio"));
    stop_tx.send(true).expect("stop");
    tokio::time::timeout(Duration::from_secs(5), link)
        .await
        .expect("timeout")
        .expect("join");
    server.await.expect("server");
}
