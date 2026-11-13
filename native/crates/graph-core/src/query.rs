use std::collections::VecDeque;
use std::fmt::Write;

use serde::Serialize;

use crate::error::{GraphError, GraphResult};
use crate::graph::Graph;
use crate::model::{EdgeKind, Language, NodeKind, SymKind};
use crate::settings::GraphSettings;

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Hit {
    pub id: u32,
    pub kind: NodeKind,
    pub sym: Option<SymKind>,
    pub name: String,
    pub path: String,
    pub line: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Reach {
    pub hit: Hit,
    pub depth: u32,
    pub via: EdgeKind,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Reached {
    pub graph_ref: String,
    pub items: Vec<Reach>,
    pub truncated: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Step {
    pub hit: Hit,
    pub via: Option<EdgeKind>,
    pub forward: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Pack {
    pub graph_ref: String,
    pub text: String,
    pub truncated: bool,
}

fn hit(graph: &Graph, id: u32) -> Option<Hit> {
    let node = graph.node(id)?;
    let path = graph.path(node.file).unwrap_or_default().to_owned();
    Some(Hit {
        id,
        kind: node.kind,
        sym: node.sym,
        name: node.name.clone(),
        path,
        line: node.line,
    })
}

pub fn resolve(graph: &Graph, target: &str) -> GraphResult<u32> {
    if let Some(id) = graph.file_id(target) {
        return Ok(id);
    }
    let mut found: Option<u32> = None;
    for (index, node) in graph.nodes().iter().enumerate() {
        if node.name == target && node.kind != NodeKind::File {
            let id = u32::try_from(index).map_err(|_| GraphError::Capacity)?;
            if found.is_some() {
                return Err(GraphError::Unknown);
            }
            found = Some(id);
        }
    }
    found.ok_or(GraphError::Unknown)
}

fn rank(name: &str, query: &str) -> Option<u8> {
    let lower = name.to_lowercase();
    if lower == query {
        Some(0)
    } else if lower.starts_with(query) {
        Some(1)
    } else {
        lower.contains(query).then_some(2)
    }
}

#[must_use]
pub fn locate(graph: &Graph, text: &str, settings: &GraphSettings) -> Vec<Hit> {
    let query = text.trim().to_lowercase();
    if query.is_empty() || query.chars().count() > settings.max_name_chars {
        return Vec::new();
    }
    let mut scored: Vec<(u8, usize, u32)> = Vec::new();
    for (index, node) in graph.nodes().iter().enumerate() {
        let Ok(id) = u32::try_from(index) else { break };
        if let Some(score) = rank(&node.name, &query) {
            scored.push((score, node.name.len(), id));
        }
    }
    scored.sort_unstable();
    scored
        .into_iter()
        .take(settings.max_results)
        .filter_map(|(_, _, id)| hit(graph, id))
        .collect()
}

fn walk(
    graph: &Graph,
    start: u32,
    depth: usize,
    limit: usize,
    visit_cap: usize,
    step: &dyn Fn(u32) -> Vec<(u32, EdgeKind)>,
) -> (Vec<Reach>, bool) {
    let mut seen = vec![false; graph.node_count()];
    if let Some(slot) = usize::try_from(start).ok().and_then(|i| seen.get_mut(i)) {
        *slot = true;
    }
    let mut queue = VecDeque::from([(start, 0u32)]);
    let mut out = Vec::new();
    let mut visited = 0usize;
    let mut truncated = false;
    while let Some((id, level)) = queue.pop_front() {
        if usize::try_from(level).unwrap_or(usize::MAX) >= depth {
            continue;
        }
        let mut next = step(id);
        next.sort_unstable();
        for (peer, kind) in next {
            let Some(slot) = usize::try_from(peer).ok().and_then(|i| seen.get_mut(i)) else {
                continue;
            };
            if *slot {
                continue;
            }
            *slot = true;
            visited = visited.saturating_add(1);
            if visited > visit_cap || out.len() >= limit {
                truncated = true;
                return (out, truncated);
            }
            let reached = level.saturating_add(1);
            if let Some(found) = hit(graph, peer) {
                out.push(Reach {
                    hit: found,
                    depth: reached,
                    via: kind,
                });
            }
            queue.push_back((peer, reached));
        }
    }
    (out, truncated)
}

fn clamp(depth: usize, settings: &GraphSettings) -> usize {
    depth.clamp(1, settings.max_depth)
}

pub fn neighborhood(
    graph: &Graph,
    target: &str,
    depth: usize,
    settings: &GraphSettings,
) -> GraphResult<Reached> {
    let start = resolve(graph, target)?;
    let step = |id: u32| graph.out_edges(id).chain(graph.in_edges(id)).collect();
    let (items, truncated) = walk(
        graph,
        start,
        clamp(depth, settings),
        settings.max_results,
        settings.max_visited,
        &step,
    );
    Ok(Reached {
        graph_ref: graph.reference(),
        items,
        truncated,
    })
}

pub fn impact(
    graph: &Graph,
    target: &str,
    depth: usize,
    settings: &GraphSettings,
) -> GraphResult<Reached> {
    let resolved = resolve(graph, target)?;
    let start = match graph.node(resolved) {
        Some(node) if node.kind == NodeKind::Symbol || node.kind == NodeKind::Section => node.file,
        _ => resolved,
    };
    let step = |id: u32| {
        graph
            .in_edges(id)
            .filter(|(_, kind)| *kind != EdgeKind::Declares)
            .collect()
    };
    let (items, truncated) = walk(
        graph,
        start,
        clamp(depth, settings),
        settings.max_results,
        settings.max_visited,
        &step,
    );
    Ok(Reached {
        graph_ref: graph.reference(),
        items,
        truncated,
    })
}

pub fn path(
    graph: &Graph,
    from: &str,
    to: &str,
    settings: &GraphSettings,
) -> GraphResult<Vec<Step>> {
    let (start, goal) = (resolve(graph, from)?, resolve(graph, to)?);
    let mut parent: Vec<Option<(u32, EdgeKind, bool)>> = vec![None; graph.node_count()];
    let mut seen = vec![false; graph.node_count()];
    if let Some(slot) = usize::try_from(start).ok().and_then(|i| seen.get_mut(i)) {
        *slot = true;
    }
    let mut queue = VecDeque::from([(start, 0usize)]);
    let mut visited = 0usize;
    let mut reached = start == goal;
    while let Some((id, level)) = queue.pop_front() {
        if reached || level >= settings.max_depth.saturating_mul(2) {
            break;
        }
        let mut next: Vec<(u32, EdgeKind, bool)> = graph
            .out_edges(id)
            .map(|(p, k)| (p, k, true))
            .chain(graph.in_edges(id).map(|(p, k)| (p, k, false)))
            .collect();
        next.sort_unstable();
        for (peer, kind, forward) in next {
            let Some(slot) = usize::try_from(peer).ok().and_then(|i| seen.get_mut(i)) else {
                continue;
            };
            if *slot {
                continue;
            }
            *slot = true;
            visited = visited.saturating_add(1);
            if visited > settings.max_visited {
                return Err(GraphError::Capacity);
            }
            if let Some(cell) = usize::try_from(peer).ok().and_then(|i| parent.get_mut(i)) {
                *cell = Some((id, kind, forward));
            }
            if peer == goal {
                reached = true;
                break;
            }
            queue.push_back((peer, level.saturating_add(1)));
        }
    }
    if !reached {
        return Err(GraphError::Unknown);
    }
    let mut steps = Vec::new();
    let mut cursor = goal;
    for _ in 0..=graph.node_count() {
        let link = usize::try_from(cursor)
            .ok()
            .and_then(|i| parent.get(i))
            .copied()
            .flatten();
        let Some(found) = hit(graph, cursor) else {
            break;
        };
        if let Some((previous, kind, forward)) = link {
            steps.push(Step {
                hit: found,
                via: Some(kind),
                forward,
            });
            cursor = previous;
        } else {
            steps.push(Step {
                hit: found,
                via: None,
                forward: true,
            });
            break;
        }
    }
    steps.reverse();
    Ok(steps)
}

fn names(graph: &Graph, ids: impl Iterator<Item = u32>, cap: usize) -> String {
    let mut list: Vec<String> = ids
        .filter_map(|id| graph.node(id).map(|n| n.name.clone()))
        .collect();
    list.sort_unstable();
    list.dedup();
    let extra = list.len().saturating_sub(cap);
    let mut text = list.into_iter().take(cap).collect::<Vec<_>>().join(", ");
    if extra > 0 {
        let _ = write!(text, ", +{extra}");
    }
    text
}

pub fn pack(
    graph: &Graph,
    targets: &[String],
    budget: usize,
    settings: &GraphSettings,
) -> GraphResult<Pack> {
    let limit = budget.clamp(1, settings.max_pack_chars);
    let mut text = format!(
        "graph_ref={} files={}\n",
        graph.reference(),
        graph.file_count()
    );
    let mut truncated = false;
    for target in targets.iter().take(settings.max_results) {
        let id = resolve(graph, target)?;
        let node = graph.node(id).ok_or(GraphError::Unknown)?;
        let file = if node.kind == NodeKind::File || node.kind == NodeKind::Package {
            id
        } else {
            node.file
        };
        let label = graph.node(file).map_or("", |n| n.name.as_str());
        let lang = graph.language(file).map_or("other", Language::label);
        let symbols: Vec<u32> = graph
            .out_edges(file)
            .filter(|(_, k)| *k == EdgeKind::Declares)
            .map(|(d, _)| d)
            .collect();
        let uses: Vec<u32> = graph
            .out_edges(file)
            .filter(|(_, k)| *k == EdgeKind::Imports)
            .map(|(d, _)| d)
            .collect();
        let used_by: Vec<u32> = graph
            .in_edges(file)
            .filter(|(_, k)| *k != EdgeKind::Declares)
            .map(|(s, _)| s)
            .collect();
        let block = format!(
            "## {label} ({lang})\nsymbols: {}\nuses: {}\nused_by: {}\n",
            names(graph, symbols.into_iter(), 40),
            names(graph, uses.into_iter(), 30),
            names(graph, used_by.into_iter(), 30),
        );
        if text.chars().count().saturating_add(block.chars().count()) > limit {
            truncated = true;
            break;
        }
        text.push_str(&block);
    }
    Ok(Pack {
        graph_ref: graph.reference(),
        text,
        truncated,
    })
}
