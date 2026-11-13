use std::collections::HashMap;

use crate::cache::{Cache, Parsed};
use crate::error::{GraphError, GraphResult};
use crate::graph::{Graph, RawEdge};
use crate::model::{EdgeKind, Language, Node, NodeKind, SymKind};
use crate::path::parent;
use crate::resolve::{Index, Target};
use crate::settings::GraphSettings;
use crate::source::FileSource;

fn node_id(value: usize) -> GraphResult<u32> {
    u32::try_from(value).map_err(|_| GraphError::Capacity)
}

struct Collected<'a> {
    paths: &'a [String],
    parsed: &'a [Parsed],
    skipped: usize,
}

struct Layout {
    nodes: Vec<Node>,
    edges: Vec<RawEdge>,
    package_of_file: HashMap<usize, u32>,
    by_name: HashMap<String, u32>,
    cargo_dirs: HashMap<String, u32>,
}

fn layout(data: &Collected<'_>) -> GraphResult<Layout> {
    let mut nodes = Vec::new();
    for (i, path) in data.paths.iter().enumerate() {
        nodes.push(Node {
            kind: NodeKind::File,
            sym: None,
            name: path.clone(),
            file: node_id(i)?,
            line: 0,
        });
    }
    let mut package_of_file = HashMap::new();
    let mut by_name = HashMap::new();
    let mut cargo_dirs = HashMap::new();
    for (i, item) in data.parsed.iter().enumerate() {
        let (Some(name), Some(path)) = (item.facts.package.as_ref(), data.paths.get(i)) else {
            continue;
        };
        if !Index::is_cargo(path) {
            continue;
        }
        let id = node_id(nodes.len())?;
        nodes.push(Node {
            kind: NodeKind::Package,
            sym: None,
            name: name.clone(),
            file: node_id(i)?,
            line: 1,
        });
        by_name.entry(name.clone()).or_insert(id);
        cargo_dirs.insert(parent(path).to_owned(), id);
        package_of_file.insert(i, id);
    }
    let mut edges = Vec::new();
    for (i, item) in data.parsed.iter().enumerate() {
        let owner = node_id(i)?;
        let kind = if item.language == Language::Markdown {
            NodeKind::Section
        } else {
            NodeKind::Symbol
        };
        for fact in &item.facts.symbols {
            let id = node_id(nodes.len())?;
            nodes.push(Node {
                kind,
                sym: Some(fact.kind),
                name: fact.name.clone(),
                file: owner,
                line: fact.line,
            });
            edges.push((owner, id, EdgeKind::Declares));
        }
    }
    Ok(Layout {
        nodes,
        edges,
        package_of_file,
        by_name,
        cargo_dirs,
    })
}

fn owning_package(cargo_dirs: &HashMap<String, u32>, path: &str) -> Option<u32> {
    let mut dir = parent(path).to_owned();
    loop {
        if let Some(id) = cargo_dirs.get(&dir) {
            return Some(*id);
        }
        if dir.is_empty() {
            return None;
        }
        let up = parent(&dir).to_owned();
        dir = up;
    }
}

fn link(index: &Index<'_>, data: &Collected<'_>, layout: &mut Layout) -> GraphResult<()> {
    for (i, path) in data.paths.iter().enumerate() {
        let (src, Some(item)) = (node_id(i)?, data.parsed.get(i)) else {
            continue;
        };
        let own_package = layout.package_of_file.get(&i).copied();
        for spec in &item.facts.imports {
            match index.resolve(path, spec) {
                Some(Target::File(dst)) if dst != src => {
                    let kind = if item.language == Language::Markdown {
                        EdgeKind::Documents
                    } else {
                        EdgeKind::Imports
                    };
                    layout.edges.push((src, dst, kind));
                }
                Some(Target::Package(dst)) => match (item.language, own_package) {
                    (Language::Cargo, Some(from)) if from != dst => {
                        layout.edges.push((from, dst, EdgeKind::DependsOn));
                    }
                    (Language::Cargo, _) => {}
                    _ => layout.edges.push((src, dst, EdgeKind::Imports)),
                },
                _ => {}
            }
        }
        for token in &item.facts.mentions {
            if let Some(dst) = index.mention(path, token).filter(|d| *d != src) {
                layout.edges.push((src, dst, EdgeKind::Documents));
            }
        }
        if let Some(package) = owning_package(&layout.cargo_dirs, path) {
            layout.edges.push((package, src, EdgeKind::Declares));
        }
    }
    Ok(())
}

pub fn assemble(paths: &[String], parsed: &[Parsed], skipped: usize) -> GraphResult<Graph> {
    let data = Collected {
        paths,
        parsed,
        skipped,
    };
    let mut shape = layout(&data)?;
    let index = Index::new(data.paths, shape.by_name.clone());
    link(&index, &data, &mut shape)?;
    let languages = data.parsed.iter().map(|p| p.language).collect();
    let digests = data.parsed.iter().map(|p| p.digest).collect();
    Graph::assemble(
        shape.nodes,
        data.paths.len(),
        languages,
        digests,
        shape.edges,
        data.skipped,
    )
}

pub fn build(source: &dyn FileSource, settings: &GraphSettings) -> GraphResult<Graph> {
    let mut cache = Cache::new();
    cache.sync(source, settings)?;
    cache.graph()
}

#[must_use]
pub const fn symbol_label(kind: SymKind) -> &'static str {
    match kind {
        SymKind::Function => "function",
        SymKind::Type => "type",
        SymKind::Trait => "trait",
        SymKind::Module => "module",
        SymKind::Constant => "constant",
        SymKind::Entity => "entity",
    }
}
