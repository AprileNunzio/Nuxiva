mod dir;
mod spec;

use std::sync::{Arc, Mutex, PoisonError};

use serde::Serialize;
use serde_json::{Map, Value};

use nuxiva_graph_core::{Cache, FileSource, Graph, GraphError, GraphSettings};
use nuxiva_mcp_core::{Implementation, McpError, McpResult, ToolOutput, ToolServer};

pub use dir::DirSource;

const MAX_TARGET: usize = 512;

struct State {
    cache: Cache,
    graph: Option<Arc<Graph>>,
}

pub struct GraphServer {
    name: String,
    settings: GraphSettings,
    source: Arc<dyn FileSource>,
    state: Mutex<State>,
}

impl std::fmt::Debug for GraphServer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("GraphServer")
            .field("name", &self.name)
            .finish_non_exhaustive()
    }
}

fn text<'a>(args: &'a Map<String, Value>, key: &str) -> Option<&'a str> {
    args.get(key)
        .and_then(Value::as_str)
        .filter(|v| !v.is_empty() && v.len() <= MAX_TARGET)
}

fn count(args: &Map<String, Value>, key: &str, default: usize) -> usize {
    args.get(key)
        .and_then(Value::as_u64)
        .and_then(|v| usize::try_from(v).ok())
        .unwrap_or(default)
}

fn render(value: &impl Serialize) -> ToolOutput {
    serde_json::to_string(value).map_or_else(
        |_| ToolOutput::fail(GraphError::Source.code()),
        ToolOutput::ok,
    )
}

fn failure(error: GraphError) -> ToolOutput {
    ToolOutput::fail(error.code())
}

impl GraphServer {
    pub fn new(
        name: &str,
        settings: &GraphSettings,
        source: Arc<dyn FileSource>,
    ) -> McpResult<Self> {
        settings.validate().map_err(|_| McpError::InvalidSettings)?;
        Ok(Self {
            name: name.to_owned(),
            settings: settings.clone(),
            source,
            state: Mutex::new(State {
                cache: Cache::new(),
                graph: None,
            }),
        })
    }

    fn current(&self) -> Result<Arc<Graph>, GraphError> {
        let mut state = self.state.lock().unwrap_or_else(PoisonError::into_inner);
        if let Some(graph) = &state.graph {
            return Ok(Arc::clone(graph));
        }
        Self::refresh(&mut state, self.source.as_ref(), &self.settings).map(|(graph, _)| graph)
    }

    fn refresh(
        state: &mut State,
        source: &dyn FileSource,
        settings: &GraphSettings,
    ) -> Result<(Arc<Graph>, nuxiva_graph_core::SyncReport), GraphError> {
        let report = state.cache.sync(source, settings)?;
        let graph = match (&state.graph, report.touched()) {
            (Some(existing), false) => Arc::clone(existing),
            _ => Arc::new(state.cache.graph()?),
        };
        state.graph = Some(Arc::clone(&graph));
        Ok((graph, report))
    }

    fn sync(&self) -> ToolOutput {
        let mut state = self.state.lock().unwrap_or_else(PoisonError::into_inner);
        match Self::refresh(&mut state, self.source.as_ref(), &self.settings) {
            Ok((graph, report)) => {
                let stats = graph.stats();
                render(&serde_json::json!({
                    "graph_ref": graph.reference(),
                    "files": stats.files,
                    "packages": stats.packages,
                    "symbols": stats.symbols,
                    "sections": stats.sections,
                    "edges": stats.edges,
                    "skipped": stats.skipped,
                    "added": report.added,
                    "changed": report.changed,
                    "removed": report.removed,
                    "unchanged": report.unchanged,
                }))
            }
            Err(error) => failure(error),
        }
    }

    fn run(&self, name: &str, args: &Map<String, Value>) -> ToolOutput {
        if name == "graph_sync" {
            return self.sync();
        }
        let graph = match self.current() {
            Ok(graph) => graph,
            Err(error) => return failure(error),
        };
        let s = &self.settings;
        let depth = count(args, "depth", 2);
        match name {
            "graph_locate" => text(args, "query").map_or_else(
                || ToolOutput::fail("richiesta non valida"),
                |q| render(&nuxiva_graph_core::locate(&graph, q, s)),
            ),
            "graph_neighbors" => text(args, "target").map_or_else(
                || ToolOutput::fail("richiesta non valida"),
                |t| {
                    nuxiva_graph_core::neighborhood(&graph, t, depth, s)
                        .map_or_else(failure, |r| render(&r))
                },
            ),
            "graph_impact" => text(args, "target").map_or_else(
                || ToolOutput::fail("richiesta non valida"),
                |t| {
                    nuxiva_graph_core::impact(&graph, t, depth, s)
                        .map_or_else(failure, |r| render(&r))
                },
            ),
            "graph_path" => match (text(args, "from"), text(args, "to")) {
                (Some(a), Some(b)) => {
                    nuxiva_graph_core::path(&graph, a, b, s).map_or_else(failure, |r| render(&r))
                }
                _ => ToolOutput::fail("richiesta non valida"),
            },
            "graph_pack" => {
                let targets: Vec<String> = args
                    .get("targets")
                    .and_then(Value::as_array)
                    .map(|list| {
                        list.iter()
                            .filter_map(Value::as_str)
                            .filter(|v| v.len() <= MAX_TARGET)
                            .map(str::to_owned)
                            .collect()
                    })
                    .unwrap_or_default();
                let budget = count(args, "budget", s.max_pack_chars);
                nuxiva_graph_core::pack(&graph, &targets, budget, s)
                    .map_or_else(failure, |r| render(&r))
            }
            _ => ToolOutput::fail("strumento sconosciuto"),
        }
    }
}

impl ToolServer for GraphServer {
    fn info(&self) -> Implementation {
        Implementation {
            name: self.name.clone(),
            version: env!("CARGO_PKG_VERSION").to_owned(),
            title: None,
        }
    }

    fn tools(&self) -> Vec<Value> {
        spec::tools()
    }

    fn call(&self, name: &str, arguments: &Map<String, Value>) -> ToolOutput {
        self.run(name, arguments)
    }
}
