use std::fs;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use agency_scheduler::HostProfile;
use serde_json::{Value, json};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixStream;

use crate::config::Config;
use crate::engine::Engine;
use crate::error::AgencyError;
use crate::protocol::Request;
use crate::server;

const HOST: HostProfile = HostProfile {
    cpu_cores: 8,
    ram_mb: 32_768,
    vram_mb: 12_288,
};

struct Sandbox {
    root: PathBuf,
}

impl Sandbox {
    fn new(tag: &str) -> Result<Self, AgencyError> {
        let mut nonce = [0u8; 8];
        getrandom::fill(&mut nonce).map_err(|e| std::io::Error::other(e.to_string()))?;
        let root =
            std::env::temp_dir().join(format!("nxa-{tag}-{:016x}", u64::from_le_bytes(nonce)));
        fs::create_dir_all(root.join("share"))?;
        Ok(Self { root })
    }

    fn config(&self) -> Config {
        Config {
            state_dir: self.root.join("state"),
            socket: self.root.join("run/agency.sock"),
            workspace_root: self.root.join("share"),
            allowed_uids: Vec::new(),
            vram_mb: None,
        }
    }
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.root);
    }
}

fn at(value: &Value, pointer: &str) -> Value {
    value.pointer(pointer).cloned().unwrap_or(Value::Null)
}

fn call(engine: &mut Engine, raw: Value) -> Result<Value, AgencyError> {
    let request: Request = serde_json::from_value(raw)?;
    engine.handle(request)
}

fn create(engine: &mut Engine) -> Result<Value, AgencyError> {
    call(
        engine,
        json!({"op": "project_create", "id": "shop", "title": "Negozio", "goal": "E-commerce di informatica",
               "workspace": "negozio", "budget": {"tokens": 100_000, "seconds": 3600, "parallel": 2}}),
    )
}

fn plan(engine: &mut Engine) -> Result<Value, AgencyError> {
    call(
        engine,
        json!({"op": "project_plan", "id": "shop", "tasks": [
            {"id": "design", "title": "Architettura", "role": "architect", "estimate_seconds": 30},
            {"id": "api", "title": "API catalogo", "role": "backend", "depends_on": ["design"]},
            {"id": "ui", "title": "Vetrina", "role": "frontend", "depends_on": ["design"]}
        ]}),
    )
}

fn task(engine: &mut Engine, id: &str, action: &str) -> Result<Value, AgencyError> {
    call(
        engine,
        json!({"op": "task_update", "project": "shop", "task": id, "action": action, "tokens": 10, "seconds": 1}),
    )
}

#[test]
fn full_project_lifecycle() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("life")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    create(&mut engine)?;
    assert!(sandbox.root.join("share/negozio").is_dir());
    plan(&mut engine)?;
    let started = call(&mut engine, json!({"op": "dispatch"}))?;
    assert_eq!(at(&started, "/started").as_array().map(Vec::len), Some(1));
    task(&mut engine, "design", "submit")?;
    task(&mut engine, "design", "approve")?;
    let started = call(&mut engine, json!({"op": "dispatch"}))?;
    assert_eq!(at(&started, "/started").as_array().map(Vec::len), Some(2));
    for id in ["api", "ui"] {
        task(&mut engine, id, "submit")?;
        task(&mut engine, id, "approve")?;
    }
    let detail = call(&mut engine, json!({"op": "project_get", "id": "shop"}))?;
    assert_eq!(at(&detail, "/project/status"), "completed");
    assert_eq!(at(&detail, "/progress/percent"), 100);
    Ok(())
}

#[test]
fn restart_interrupts_running_tasks() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("restart")?;
    {
        let mut engine = Engine::open(sandbox.config(), HOST)?;
        create(&mut engine)?;
        plan(&mut engine)?;
        call(&mut engine, json!({"op": "dispatch"}))?;
    }
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    let detail = call(&mut engine, json!({"op": "project_get", "id": "shop"}))?;
    let design = at(&detail, "/tasks")
        .as_array()
        .and_then(|tasks| tasks.iter().find(|t| at(t, "/id") == "design"))
        .map(|t| (at(t, "/status"), at(t, "/attempts")));
    assert_eq!(design, Some((json!("pending"), json!(0))));
    Ok(())
}

#[test]
fn rejects_traversal_duplicates_and_unknown_fields() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("reject")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    let escape = call(
        &mut engine,
        json!({"op": "project_create", "id": "x", "title": "x", "goal": "x",
               "workspace": "../etc", "budget": {"tokens": 1, "seconds": 1, "parallel": 1}}),
    );
    assert!(escape.is_err());
    assert!(!sandbox.root.join("etc").exists());
    create(&mut engine)?;
    assert!(matches!(create(&mut engine), Err(AgencyError::Exists)));
    assert!(serde_json::from_value::<Request>(json!({"op": "ping", "evil": 1})).is_err());
    Ok(())
}

#[test]
fn budget_exhaustion_pauses_the_project() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("budget")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    call(
        &mut engine,
        json!({"op": "project_create", "id": "shop", "title": "N", "goal": "G",
               "workspace": "n", "budget": {"tokens": 5, "seconds": 3600, "parallel": 1}}),
    )?;
    plan(&mut engine)?;
    call(&mut engine, json!({"op": "dispatch"}))?;
    let detail = task(&mut engine, "design", "submit")?;
    assert_eq!(at(&detail, "/project/status"), "paused");
    let started = call(&mut engine, json!({"op": "dispatch"}))?;
    assert_eq!(at(&started, "/started").as_array().map(Vec::len), Some(0));
    Ok(())
}

#[test]
fn cancel_closes_every_open_task() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("cancel")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    create(&mut engine)?;
    plan(&mut engine)?;
    let detail = call(
        &mut engine,
        json!({"op": "project_control", "id": "shop", "action": "cancel"}),
    )?;
    assert_eq!(at(&detail, "/project/status"), "cancelled");
    assert_eq!(at(&detail, "/progress/cancelled"), 3);
    assert!(plan(&mut engine).is_err());
    Ok(())
}

#[test]
fn settings_drive_capacity() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("settings")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    let manual = call(
        &mut engine,
        json!({"op": "settings_set",
               "scheduler": {"mode": "manual", "manual_parallel": 3, "max_parallel": 8, "reserve_ram_mb": 1024},
               "model": {"kind": "cloud", "requests_per_minute": 60}}),
    )?;
    assert_eq!(at(&manual, "/capacity/parallel_agents"), 3);
    let bad = call(
        &mut engine,
        json!({"op": "settings_set",
               "scheduler": {"mode": "auto", "manual_parallel": 0, "max_parallel": 8, "reserve_ram_mb": 0},
               "model": {"kind": "local", "size_mb": 100}}),
    );
    assert!(bad.is_err());
    drop(engine);
    let mut reopened = Engine::open(sandbox.config(), HOST)?;
    assert_eq!(
        at(
            &call(&mut reopened, json!({"op": "settings_get"}))?,
            "/scheduler/manual_parallel"
        ),
        3
    );
    Ok(())
}

#[test]
fn tampered_ledger_refuses_to_start() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("tamper")?;
    {
        let mut engine = Engine::open(sandbox.config(), HOST)?;
        create(&mut engine)?;
    }
    let ledger = sandbox.root.join("state/ledger.jsonl");
    let text = fs::read_to_string(&ledger)?.replace("shop", "shoq");
    fs::write(&ledger, text)?;
    assert!(Engine::open(sandbox.config(), HOST).is_err());
    Ok(())
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
