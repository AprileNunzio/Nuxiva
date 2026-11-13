use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use serde_json::{Map, Value, json};

use nuxiva_mcp_core::{ToolOutput, ToolServer};

use crate::{FileServer, FsConfig, Mode, RootConfig};

static COUNTER: AtomicU64 = AtomicU64::new(0);

pub struct Scratch {
    pub base: PathBuf,
}

impl Scratch {
    pub fn new() -> Self {
        let id = COUNTER.fetch_add(1, Ordering::Relaxed);
        let base = fs::canonicalize(std::env::temp_dir())
            .unwrap_or_else(|_| std::env::temp_dir())
            .join(format!("nuxiva-mcp-fs-{}-{id}", std::process::id()));
        let _ = fs::remove_dir_all(&base);
        let _ = fs::create_dir_all(&base);
        Self { base }
    }

    pub fn dir(&self, name: &str) -> PathBuf {
        let path = self.base.join(name);
        let _ = fs::create_dir_all(&path);
        path
    }
}

impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.base);
    }
}

pub fn root(name: &str, path: &Path, mode: Mode) -> RootConfig {
    RootConfig {
        name: name.to_owned(),
        path: path.to_string_lossy().into_owned(),
        mode,
        ..RootConfig::default()
    }
}

pub fn config(scratch: &Scratch) -> FsConfig {
    FsConfig {
        roots: vec![
            root("work", &scratch.dir("work"), Mode::Write),
            root("share", &scratch.dir("share"), Mode::Read),
        ],
        default_root: Some("work".into()),
        trash: Some(scratch.base.join("trash").to_string_lossy().into_owned()),
        ..FsConfig::default()
    }
}

pub fn server(config: &FsConfig) -> FileServer {
    match FileServer::new("files", config) {
        Ok(server) => server,
        Err(error) => unreachable!("{error:?}"),
    }
}

pub fn args(value: &Value) -> Map<String, Value> {
    value.as_object().cloned().unwrap_or_default()
}

pub fn call(server: &FileServer, tool: &str, value: &Value) -> ToolOutput {
    server.call(tool, &args(value))
}

pub fn ok(server: &FileServer, tool: &str, value: &Value) -> String {
    let out = call(server, tool, value);
    assert!(!out.is_error, "{tool}: {}", out.text);
    out.text
}

pub fn refused(server: &FileServer, tool: &str, value: &Value) -> String {
    let out = call(server, tool, value);
    assert!(out.is_error, "{tool} should be refused: {}", out.text);
    out.text
}

pub fn path_json(path: &Path) -> Value {
    json!({"path": path.to_string_lossy()})
}
