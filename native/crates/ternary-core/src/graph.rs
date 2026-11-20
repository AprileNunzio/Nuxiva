use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet, VecDeque};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EdgeType {
    Causal,
    Dependency,
    Derivation,
    Associative,
    Precedes,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GraphEdge {
    pub source_id: String,
    pub target_id: String,
    pub edge_type: EdgeType,
    pub weight: f32,
    pub created_at_ms: u64,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct MemoryGraph {
    edges: Vec<GraphEdge>,
    outgoing: HashMap<String, Vec<usize>>,
    incoming: HashMap<String, Vec<usize>>,
}

impl MemoryGraph {
    #[must_use]
    pub fn new() -> Self {
        Self {
            edges: Vec::new(),
            outgoing: HashMap::new(),
            incoming: HashMap::new(),
        }
    }

    #[must_use]
    pub fn edge_count(&self) -> usize {
        self.edges.len()
    }

    pub fn add_edge(
        &mut self,
        source_id: String,
        target_id: String,
        edge_type: EdgeType,
        weight: f32,
        created_at_ms: u64,
    ) {
        let edge_idx = self.edges.len();
        let edge = GraphEdge {
            source_id: source_id.clone(),
            target_id: target_id.clone(),
            edge_type,
            weight,
            created_at_ms,
        };
        self.edges.push(edge);
        self.outgoing.entry(source_id).or_default().push(edge_idx);
        self.incoming.entry(target_id).or_default().push(edge_idx);
    }

    #[must_use]
    pub fn get_outgoing(&self, node_id: &str) -> Vec<GraphEdge> {
        let mut result = Vec::new();
        if let Some(indices) = self.outgoing.get(node_id) {
            for &idx in indices {
                if let Some(edge) = self.edges.get(idx) {
                    result.push(edge.clone());
                }
            }
        }
        result
    }

    #[must_use]
    pub fn get_incoming(&self, node_id: &str) -> Vec<GraphEdge> {
        let mut result = Vec::new();
        if let Some(indices) = self.incoming.get(node_id) {
            for &idx in indices {
                if let Some(edge) = self.edges.get(idx) {
                    result.push(edge.clone());
                }
            }
        }
        result
    }

    #[must_use]
    pub fn expand_context(
        &self,
        seeds: &[String],
        max_hops: usize,
        max_nodes: usize,
    ) -> Vec<String> {
        let mut visited: HashSet<String> = HashSet::new();
        let mut queue: VecDeque<(String, usize)> = VecDeque::new();
        let mut ordered_results: Vec<String> = Vec::new();

        for seed in seeds {
            if visited.insert(seed.clone()) {
                queue.push_back((seed.clone(), 0));
                ordered_results.push(seed.clone());
            }
        }

        while let Some((curr, hop)) = queue.pop_front() {
            if ordered_results.len() >= max_nodes {
                break;
            }
            if hop >= max_hops {
                continue;
            }

            if let Some(indices) = self.outgoing.get(&curr) {
                for &idx in indices {
                    if let Some(edge) = self.edges.get(idx) {
                        if visited.insert(edge.target_id.clone()) {
                            ordered_results.push(edge.target_id.clone());
                            queue.push_back((edge.target_id.clone(), hop.saturating_add(1)));
                            if ordered_results.len() >= max_nodes {
                                break;
                            }
                        }
                    }
                }
            }

            if ordered_results.len() >= max_nodes {
                break;
            }

            if let Some(indices) = self.incoming.get(&curr) {
                for &idx in indices {
                    if let Some(edge) = self.edges.get(idx) {
                        if visited.insert(edge.source_id.clone()) {
                            ordered_results.push(edge.source_id.clone());
                            queue.push_back((edge.source_id.clone(), hop.saturating_add(1)));
                            if ordered_results.len() >= max_nodes {
                                break;
                            }
                        }
                    }
                }
            }
        }

        ordered_results
    }
}
