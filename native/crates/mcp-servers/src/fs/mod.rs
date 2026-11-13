mod config;
mod io;
mod paths;
mod read;
mod spec;
mod write;

use std::sync::Mutex;

use serde_json::{Map, Value};

use nuxiva_mcp_core::{Implementation, McpError, McpResult, ToolOutput, ToolServer};

pub use config::{FsConfig, Mode, RootConfig};
use paths::{Boundary, Fault};
use read::ReadLimits;
use write::Budget;

pub struct FileServer {
    boundary: Boundary,
    limits: ReadLimits,
    entries: usize,
    taint_reads: bool,
    name: String,
    gate: Mutex<()>,
}

impl std::fmt::Debug for FileServer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("FileServer")
            .field("name", &self.name)
            .finish_non_exhaustive()
    }
}

fn text<'a>(args: &'a Map<String, Value>, key: &str) -> Option<&'a str> {
    args.get(key).and_then(Value::as_str)
}

fn flag(args: &Map<String, Value>, key: &str) -> bool {
    match args.get(key) {
        Some(Value::Bool(value)) => *value,
        Some(Value::String(value)) => value.eq_ignore_ascii_case("true"),
        _ => false,
    }
}

impl FileServer {
    pub fn new(name: &str, config: &FsConfig) -> McpResult<Self> {
        config.validate()?;
        let boundary = Boundary::new(config).map_err(|_| McpError::InvalidSettings)?;
        Ok(Self {
            boundary,
            limits: ReadLimits {
                text: config.text_limit,
                list: config.list_limit,
                find: config.find_limit,
                entries: config.max_entries,
            },
            entries: config.max_entries,
            taint_reads: config.taint_reads,
            name: name.to_owned(),
            gate: Mutex::new(()),
        })
    }

    fn run(&self, name: &str, args: &Map<String, Value>) -> Result<String, Fault> {
        let b = &self.boundary;
        let need = |key: &str| text(args, key).ok_or(Fault::Invalid);
        let mut budget = Budget {
            entries: self.entries,
        };
        match name {
            "list_dir" => read::list_dir(b, &self.limits, text(args, "path").unwrap_or("")),
            "read_file" => read::read_file(b, &self.limits, need("path")?),
            "file_info" => read::file_info(b, need("path")?),
            "find_files" => read::find_files(
                b,
                &self.limits,
                need("pattern")?,
                text(args, "root").unwrap_or(""),
            ),
            "write_file" => write::write_file(
                b,
                &mut budget,
                need("path")?,
                need("content")?,
                flag(args, "append"),
            ),
            "make_dir" => write::make_dir(b, need("path")?),
            "copy" => write::copy(b, &mut budget, need("src")?, need("dst")?),
            "move" => write::move_path(b, &mut budget, need("src")?, need("dst")?),
            "delete" => write::delete(b, &mut budget, need("path")?),
            _ => Err(Fault::Invalid),
        }
    }
}

impl ToolServer for FileServer {
    fn info(&self) -> Implementation {
        Implementation {
            name: self.name.clone(),
            version: env!("CARGO_PKG_VERSION").to_owned(),
            title: None,
        }
    }

    fn tools(&self) -> Vec<Value> {
        spec::tools(self.taint_reads)
    }

    fn call(&self, name: &str, arguments: &Map<String, Value>) -> ToolOutput {
        let _serial = self
            .gate
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        match self.run(name, arguments) {
            Ok(text) => ToolOutput::ok(text),
            Err(fault) => ToolOutput::fail(fault.message()),
        }
    }
}
