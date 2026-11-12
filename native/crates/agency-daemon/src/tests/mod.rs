mod cognition;
mod foresight;
mod lifecycle;
mod planning;
mod reliability;

use std::fs;
use std::path::PathBuf;

use agency_scheduler::HostProfile;
use serde_json::{Value, json};

use crate::config::Config;
use crate::engine::Engine;
use crate::error::AgencyError;
use crate::protocol::Request;

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
