use std::fs;
use std::sync::{Arc, Mutex};

use serde_json::{Value, json};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixStream;

use super::{HOST, Sandbox, at, call, create};
use crate::engine::Engine;
use crate::error::AgencyError;
use crate::server;

fn scenario() -> Value {
    let agents: Vec<Value> = (0..24)
        .map(|i| {
            json!({
                "key": format!("p{i}"),
                "name": format!("Persona {i}"),
                "role": if i % 2 == 0 { "resident" } else { "merchant" },
                "entity": if i % 2 == 0 { "riverside" } else { "market" },
                "traits": {
                    "stance": if i % 3 == 0 { 0.5 } else { -0.3 },
                    "openness": 0.6, "activity": 0.8, "influence": 0.4,
                    "stubbornness": 0.2, "forum": 0.3
                }
            })
        })
        .collect();
    json!({
        "title": "Bridge",
        "question": "Will the new bridge be welcomed?",
        "seed": 42,
        "rounds": 12,
        "entities": [
            {"key": "riverside", "name": "Riverside", "kind": "district"},
            {"key": "market", "name": "Market", "kind": "district"}
        ],
        "relations": [{"from": "riverside", "to": "market", "kind": "trade", "weight": 0.6}],
        "agents": agents,
        "events": [{"round": 3, "title": "Cost revealed", "shift": -0.8, "reach": 0.7}]
    })
}

#[tokio::test]
async fn socket_round_trip() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("sock")?;
    let config = sandbox.config();
    let socket = config.socket.clone();
    let engine = Arc::new(Mutex::new(Engine::open(config, HOST)?));
    let listener = server::bind(&socket)?;
    {
        use std::os::unix::fs::PermissionsExt;
        assert_eq!(fs::metadata(&socket)?.permissions().mode() & 0o777, 0o600);
    }
    let handle = tokio::spawn(server::serve(listener, engine, Arc::new(Vec::new())));
    let stream = UnixStream::connect(&socket).await?;
    let (read, mut write) = stream.into_split();
    let mut lines = BufReader::new(read).lines();
    write
        .write_all(b"{\"op\":\"ping\"}\n{\"op\":\"nope\"}\n")
        .await?;
    let first: Value = serde_json::from_str(&lines.next_line().await?.unwrap_or_default())?;
    let second: Value = serde_json::from_str(&lines.next_line().await?.unwrap_or_default())?;
    assert_eq!(at(&first, "/ok"), true);
    assert_eq!(at(&second, "/error/code"), "bad_request");
    handle.abort();
    Ok(())
}

#[test]
fn foresight_lifecycle_is_sealed_and_persistent() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("fs")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    let created = call(
        &mut engine,
        json!({"op": "foresight_create", "id": "bridge", "scenario": scenario()}),
    )?;
    assert_eq!(at(&created, "/round"), 0);
    assert!(
        call(
            &mut engine,
            json!({"op": "foresight_create", "id": "bridge", "scenario": scenario()})
        )
        .is_err()
    );
    let ran = call(
        &mut engine,
        json!({"op": "foresight_run", "id": "bridge", "rounds": 5}),
    )?;
    assert_eq!(at(&ran, "/advanced"), 5);
    call(
        &mut engine,
        json!({"op": "foresight_inject", "id": "bridge",
               "event": {"round": 8, "title": "Grant", "shift": 0.9, "reach": 0.8, "target": "market"}}),
    )?;
    let raw = fs::read(sandbox.root.join("state/foresight/bridge.bin"))?;
    assert!(raw.starts_with(b"NXF1"));
    assert!(!raw.windows(6).any(|w| w == b"Bridge"));
    drop(engine);
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    let ran = call(&mut engine, json!({"op": "foresight_run", "id": "bridge"}))?;
    assert_eq!(at(&ran, "/finished"), true);
    let report = call(
        &mut engine,
        json!({"op": "foresight_report", "id": "bridge"}),
    )?;
    assert_eq!(
        at(&report, "/report/events").as_array().map(Vec::len),
        Some(2)
    );
    let agent = call(
        &mut engine,
        json!({"op": "foresight_agent", "id": "bridge", "agent": "p1"}),
    )?;
    assert_eq!(at(&agent, "/name"), "Persona 1");
    let missing = call(
        &mut engine,
        json!({"op": "foresight_agent", "id": "bridge", "agent": "zz"}),
    );
    assert_eq!(missing.err().map(|e| e.code()), Some("not_found"));
    let batch = call(
        &mut engine,
        json!({"op": "foresight_ensemble", "id": "bridge", "runs": 4}),
    )?;
    assert_eq!(at(&batch, "/ensemble/runs"), 4);
    let list = call(&mut engine, json!({"op": "foresight_list"}))?;
    assert_eq!(list.as_array().map(Vec::len), Some(1));
    call(
        &mut engine,
        json!({"op": "foresight_delete", "id": "bridge"}),
    )?;
    assert!(!sandbox.root.join("state/foresight/bridge.bin").exists());
    let missing = call(
        &mut engine,
        json!({"op": "foresight_report", "id": "bridge"}),
    );
    assert_eq!(missing.err().map(|e| e.code()), Some("not_found"));
    Ok(())
}

#[test]
fn foresight_rejects_tampering_and_bad_input() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("ft")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    let mut bad = scenario();
    if let Some(title) = bad.pointer_mut("/title") {
        *title = json!("x\u{0007}");
    }
    let rejected = call(
        &mut engine,
        json!({"op": "foresight_create", "id": "bad", "scenario": bad}),
    );
    assert_eq!(rejected.err().map(|e| e.code()), Some("invalid"));
    assert!(
        call(
            &mut engine,
            json!({"op": "foresight_create", "id": "../x", "scenario": scenario()})
        )
        .is_err()
    );
    call(
        &mut engine,
        json!({"op": "foresight_create", "id": "bridge", "scenario": scenario()}),
    )?;
    let path = sandbox.root.join("state/foresight/bridge.bin");
    let mut raw = fs::read(&path)?;
    if let Some(byte) = raw.last_mut() {
        *byte ^= 0x01;
    }
    fs::write(&path, &raw)?;
    let tampered = call(&mut engine, json!({"op": "foresight_run", "id": "bridge"}));
    assert_eq!(tampered.err().map(|e| e.code()), Some("sealed"));
    Ok(())
}

#[tokio::test]
async fn foresight_ensemble_runs_outside_the_engine_lock() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("fe")?;
    let config = sandbox.config();
    let socket = config.socket.clone();
    let engine = Arc::new(Mutex::new(Engine::open(config, HOST)?));
    let listener = server::bind(&socket)?;
    let handle = tokio::spawn(server::serve(listener, engine, Arc::new(Vec::new())));
    let stream = UnixStream::connect(&socket).await?;
    let (read, mut write) = stream.into_split();
    let mut lines = BufReader::new(read).lines();
    let create = json!({"op": "foresight_create", "id": "bridge", "scenario": scenario()});
    let batch = json!({"op": "foresight_ensemble", "id": "bridge", "runs": 3});
    let payload = format!("{create}\n{batch}\n");
    write.write_all(payload.as_bytes()).await?;
    let first: Value = serde_json::from_str(&lines.next_line().await?.unwrap_or_default())?;
    let second: Value = serde_json::from_str(&lines.next_line().await?.unwrap_or_default())?;
    assert_eq!(at(&first, "/ok"), true);
    assert_eq!(at(&second, "/data/ensemble/runs"), 3);
    handle.abort();
    Ok(())
}

#[test]
fn tampered_ledger_refuses_to_start() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("tamper")?;
    {
        let mut engine = Engine::open(sandbox.config(), HOST)?;
        create(&mut engine)?;
    }
    let ledger_path = sandbox.root.join("state/ledger.jsonl");
    let raw = fs::read_to_string(&ledger_path)?;
    let mut tampered = String::new();
    for line in raw.lines() {
        if line.contains("project.created") {
            tampered.push_str(&line.replace("project.created", "project.evil"));
        } else {
            tampered.push_str(line);
        }
        tampered.push('\n');
    }
    fs::write(&ledger_path, tampered)?;
    let failed = Engine::open(sandbox.config(), HOST);
    assert!(failed.is_err());
    Ok(())
}
