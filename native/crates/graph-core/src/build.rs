use std::collections::{BTreeSet, HashMap};

use sha2::{Digest, Sha256};

use crate::error::{GraphError, GraphResult};
use crate::extract::{extract, language};
use crate::graph::{Graph, RawEdge};
use crate::model::{EdgeKind, Facts, Language, Node, NodeKind, SymKind};
use crate::path::{parent, validate};
use crate::resolve::{Index, Target};
use crate::settings::GraphSettings;
use crate::source::FileSource;

struct Parsed {
    facts: Facts,
    digest: [u8; 32],
    language: Language,
}

fn load(source: &dyn FileSource, path: &str, settings: &GraphSettings) -> Option<Parsed> {
    let lang = language(path);
    if lang == Language::Other {
        return Some(Parsed {
            facts: Facts::default(),
            digest: [0; 32],
            language: lang,
        });
    }
    let bytes = source.read(path, settings.max_file_bytes).ok()?;
    let text = std::str::from_utf8(&bytes).ok()?;
    let digest: [u8; 32] = Sha256::digest(&bytes).into();
    Some(Parsed {
        facts: extract(lang, text, settings),
        digest,
        language: lang,
    })
}

fn node_id(value: usize) -> GraphResult<u32> {
    u32::try_from(value).map_err(|_| GraphError::Capacity)
}

struct Collected {
    paths: Vec<String>,
    parsed: Vec<Parsed>,
    skipped: usize,
}

fn collect(source: &dyn FileSource, settings: &GraphSettings) -> GraphResult<Collected> {
    let mut skipped = 0usize;
    let mut listed = BTreeSet::new();
    for entry in source.list()? {
        if validate(&entry.path, settings.max_path_chars).is_err() {
            skipped = skipped.saturating_add(1);
            continue;
        }
        listed.insert(entry.path);
    }
    skipped = skipped.saturating_add(listed.len().saturating_sub(settings.max_files));
    let mut paths = Vec::new();
    let mut parsed = Vec::new();
    for path in listed.into_iter().take(settings.max_files) {
        match load(source, &path, settings) {
            Some(item) => {
                paths.push(path);
                parsed.push(item);
            }
            None => skipped = skipped.saturating_add(1),
        }
    }
    Ok(Collected {
        paths,
        parsed,
        skipped,
    })
}

struct Layout {
    nodes: Vec<Node>,
    edges: Vec<RawEdge>,
    package_of_file: HashMap<usize, u32>,
    by_name: HashMap<String, u32>,
    cargo_dirs: HashMap<String, u32>,
}

fn layout(data: &Collected) -> GraphResult<Layout> {
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

fn link(index: &Index<'_>, data: &Collected, layout: &mut Layout) -> GraphResult<()> {
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

pub fn build(source: &dyn FileSource, settings: &GraphSettings) -> GraphResult<Graph> {
    settings.validate()?;
    let data = collect(source, settings)?;
    let mut shape = layout(&data)?;
    let index = Index::new(&data.paths, shape.by_name.clone());
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
