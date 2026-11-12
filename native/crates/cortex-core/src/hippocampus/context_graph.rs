use serde::{Deserialize, Serialize};
use std::cmp::Ordering;
use std::collections::{BinaryHeap, HashMap, HashSet, VecDeque};

pub const MAX_GRAPH_NODES: usize = 100_000;
pub const MAX_GRAPH_EDGES: usize = 500_000;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ContextNode {
    pub id: String,
    pub node_type: String,
    pub label: String,
    pub properties_json: String,
    pub weight: f32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ContextEdge {
    pub source_id: String,
    pub target_id: String,
    pub relation_type: String,
    pub weight: f32,
    pub properties_json: String,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ContextGraph {
    nodes: HashMap<String, ContextNode>,
    outgoing: HashMap<String, Vec<ContextEdge>>,
    incoming: HashMap<String, Vec<ContextEdge>>,
}

#[derive(Copy, Clone, PartialEq)]
struct PathCandidate<'a> {
    cost: f32,
    node: &'a str,
}

impl Eq for PathCandidate<'_> {}

impl Ord for PathCandidate<'_> {
    fn cmp(&self, other: &Self) -> Ordering {
        other.cost.total_cmp(&self.cost)
    }
}

impl PartialOrd for PathCandidate<'_> {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl ContextGraph {
    #[must_use]
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            outgoing: HashMap::new(),
            incoming: HashMap::new(),
        }
    }

    pub fn upsert_node(
        &mut self,
        id: &str,
        node_type: &str,
        label: &str,
        properties_json: &str,
        weight: f32,
    ) -> bool {
        if self.nodes.len() >= MAX_GRAPH_NODES && !self.nodes.contains_key(id) {
            return false;
        }
        let clean_weight = if weight.is_finite() && weight >= 0.0 {
            weight
        } else {
            1.0
        };
        let node = ContextNode {
            id: id.to_string(),
            node_type: node_type.to_string(),
            label: label.to_string(),
            properties_json: properties_json.to_string(),
            weight: clean_weight,
        };
        self.nodes.insert(id.to_string(), node);
        true
    }

    #[must_use]
    pub fn get_node(&self, id: &str) -> Option<&ContextNode> {
        self.nodes.get(id)
    }

    pub fn remove_node(&mut self, id: &str) -> bool {
        if self.nodes.remove(id).is_none() {
            return false;
        }
        if let Some(out_edges) = self.outgoing.remove(id) {
            for e in out_edges {
                if let Some(inc) = self.incoming.get_mut(&e.target_id) {
                    inc.retain(|edge| edge.source_id != id);
                }
            }
        }
        if let Some(in_edges) = self.incoming.remove(id) {
            for e in in_edges {
                if let Some(out) = self.outgoing.get_mut(&e.source_id) {
                    out.retain(|edge| edge.target_id != id);
                }
            }
        }
        true
    }

    pub fn upsert_edge(
        &mut self,
        source_id: &str,
        target_id: &str,
        relation_type: &str,
        weight: f32,
        properties_json: &str,
    ) -> bool {
        if !self.nodes.contains_key(source_id) || !self.nodes.contains_key(target_id) {
            return false;
        }
        let total_edges = self.edge_count();
        if total_edges >= MAX_GRAPH_EDGES {
            return false;
        }
        let clean_weight = if weight.is_finite() && weight > 0.0 {
            weight
        } else {
            1.0
        };
        let edge = ContextEdge {
            source_id: source_id.to_string(),
            target_id: target_id.to_string(),
            relation_type: relation_type.to_string(),
            weight: clean_weight,
            properties_json: properties_json.to_string(),
        };

        let out_list = self.outgoing.entry(source_id.to_string()).or_default();
        if let Some(pos) = out_list
            .iter()
            .position(|e| e.target_id == target_id && e.relation_type == relation_type)
        {
            if let Some(item) = out_list.get_mut(pos) {
                *item = edge.clone();
            }
        } else {
            out_list.push(edge.clone());
        }

        let in_list = self.incoming.entry(target_id.to_string()).or_default();
        if let Some(pos) = in_list
            .iter()
            .position(|e| e.source_id == source_id && e.relation_type == relation_type)
        {
            if let Some(item) = in_list.get_mut(pos) {
                *item = edge;
            }
        } else {
            in_list.push(edge);
        }
        true
    }

    pub fn remove_edge(&mut self, source_id: &str, target_id: &str, relation_type: &str) -> bool {
        let mut removed = false;
        if let Some(out_list) = self.outgoing.get_mut(source_id) {
            let initial = out_list.len();
            out_list.retain(|e| !(e.target_id == target_id && e.relation_type == relation_type));
            if out_list.len() < initial {
                removed = true;
            }
        }
        if let Some(in_list) = self.incoming.get_mut(target_id) {
            in_list.retain(|e| !(e.source_id == source_id && e.relation_type == relation_type));
        }
        removed
    }

    #[must_use]
    pub fn get_neighbors(&self, id: &str, direction: &str) -> Vec<(String, String, f32)> {
        let mut results = Vec::new();
        match direction {
            "incoming" => {
                if let Some(in_edges) = self.incoming.get(id) {
                    for e in in_edges {
                        results.push((e.source_id.clone(), e.relation_type.clone(), e.weight));
                    }
                }
            }
            "both" => {
                if let Some(out_edges) = self.outgoing.get(id) {
                    for e in out_edges {
                        results.push((e.target_id.clone(), e.relation_type.clone(), e.weight));
                    }
                }
                if let Some(in_edges) = self.incoming.get(id) {
                    for e in in_edges {
                        results.push((e.source_id.clone(), e.relation_type.clone(), e.weight));
                    }
                }
            }
            _ => {
                if let Some(out_edges) = self.outgoing.get(id) {
                    for e in out_edges {
                        results.push((e.target_id.clone(), e.relation_type.clone(), e.weight));
                    }
                }
            }
        }
        results
    }

    #[must_use]
    pub fn shortest_path(&self, from_id: &str, to_id: &str) -> Option<Vec<String>> {
        if !self.nodes.contains_key(from_id) || !self.nodes.contains_key(to_id) {
            return None;
        }
        if from_id == to_id {
            return Some(vec![from_id.to_string()]);
        }

        let mut distances: HashMap<&str, f32> = HashMap::new();
        let mut previous: HashMap<&str, &str> = HashMap::new();
        let mut queue: BinaryHeap<PathCandidate<'_>> = BinaryHeap::new();

        distances.insert(from_id, 0.0);
        queue.push(PathCandidate {
            cost: 0.0,
            node: from_id,
        });

        while let Some(PathCandidate { cost, node }) = queue.pop() {
            if node == to_id {
                let mut path = Vec::new();
                let mut curr = to_id;
                path.push(curr.to_string());
                while let Some(&prev) = previous.get(curr) {
                    path.push(prev.to_string());
                    if prev == from_id {
                        break;
                    }
                    curr = prev;
                }
                path.reverse();
                return Some(path);
            }

            if let Some(&best) = distances.get(node) {
                if cost > best {
                    continue;
                }
            }

            if let Some(edges) = self.outgoing.get(node) {
                for edge in edges {
                    let next_node = edge.target_id.as_str();
                    let next_cost = cost + (1.0 / edge.weight.max(0.001));
                    let is_better = distances
                        .get(next_node)
                        .is_none_or(|&curr_cost| next_cost < curr_cost);

                    if is_better {
                        distances.insert(next_node, next_cost);
                        previous.insert(next_node, node);
                        queue.push(PathCandidate {
                            cost: next_cost,
                            node: next_node,
                        });
                    }
                }
            }
        }
        None
    }

    #[must_use]
    pub fn k_hop_subgraph(
        &self,
        start_id: &str,
        max_hops: usize,
        max_nodes: usize,
    ) -> (Vec<ContextNode>, Vec<ContextEdge>) {
        if !self.nodes.contains_key(start_id) {
            return (Vec::new(), Vec::new());
        }

        let mut visited: HashSet<String> = HashSet::new();
        let mut queue: VecDeque<(String, usize)> = VecDeque::new();
        let mut nodes = Vec::new();

        visited.insert(start_id.to_string());
        queue.push_back((start_id.to_string(), 0));

        while let Some((curr_id, hops)) = queue.pop_front() {
            if let Some(n) = self.nodes.get(&curr_id) {
                nodes.push(n.clone());
            }
            if nodes.len() >= max_nodes || hops >= max_hops {
                continue;
            }

            if let Some(out_edges) = self.outgoing.get(&curr_id) {
                for edge in out_edges {
                    if !visited.contains(&edge.target_id)
                        && nodes.len().saturating_add(queue.len()) < max_nodes
                    {
                        visited.insert(edge.target_id.clone());
                        queue.push_back((edge.target_id.clone(), hops.saturating_add(1)));
                    }
                }
            }
        }

        let mut edges = Vec::new();
        for node in &nodes {
            if let Some(out_edges) = self.outgoing.get(&node.id) {
                for edge in out_edges {
                    if visited.contains(&edge.target_id) {
                        edges.push(edge.clone());
                    }
                }
            }
        }

        (nodes, edges)
    }

    #[must_use]
    pub fn pagerank(&self, damping: f32, iterations: usize) -> Vec<(String, f32)> {
        let n = self.nodes.len();
        if n == 0 {
            return Vec::new();
        }

        let d = if (0.0..1.0).contains(&damping) {
            damping
        } else {
            0.85
        };
        let initial_score = 1.0 / (n as f32);
        let mut scores: HashMap<String, f32> = self
            .nodes
            .keys()
            .map(|k| (k.clone(), initial_score))
            .collect();

        for _ in 0..iterations {
            let mut next_scores = HashMap::new();
            let base = (1.0 - d) / (n as f32);

            for node_id in self.nodes.keys() {
                let mut sum = 0.0;
                if let Some(in_edges) = self.incoming.get(node_id) {
                    for edge in in_edges {
                        let out_degree = self
                            .outgoing
                            .get(&edge.source_id)
                            .map_or(0, std::vec::Vec::len);
                        if out_degree > 0 {
                            let source_score = scores.get(&edge.source_id).copied().unwrap_or(0.0);
                            sum += source_score / (out_degree as f32);
                        }
                    }
                }
                next_scores.insert(node_id.clone(), base + (d * sum));
            }
            scores = next_scores;
        }

        let mut ranked: Vec<(String, f32)> = scores.into_iter().collect();
        ranked.sort_by(|a, b| b.1.total_cmp(&a.1));
        ranked
    }

    #[must_use]
    pub fn node_count(&self) -> usize {
        self.nodes.len()
    }

    #[must_use]
    pub fn edge_count(&self) -> usize {
        self.outgoing.values().map(std::vec::Vec::len).sum()
    }

    pub fn clear(&mut self) {
        self.nodes.clear();
        self.outgoing.clear();
        self.incoming.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::ContextGraph;

    #[test]
    fn test_node_and_edge_lifecycle() {
        let mut graph = ContextGraph::new();
        assert!(graph.upsert_node("n1", "agent", "Orchestrator", "{}", 1.0));
        assert!(graph.upsert_node("n2", "tool", "MemoryTool", "{}", 1.0));
        assert_eq!(graph.node_count(), 2);

        assert!(graph.upsert_edge("n1", "n2", "USES", 2.0, "{}"));
        assert_eq!(graph.edge_count(), 1);

        let neighbors = graph.get_neighbors("n1", "outgoing");
        assert_eq!(neighbors.len(), 1);
        assert_eq!(neighbors.first().map(|n| n.0.as_str()), Some("n2"));

        assert!(graph.remove_edge("n1", "n2", "USES"));
        assert_eq!(graph.edge_count(), 0);

        assert!(graph.remove_node("n1"));
        assert_eq!(graph.node_count(), 1);
    }

    #[test]
    fn test_shortest_path_dijkstra() {
        let mut graph = ContextGraph::new();
        graph.upsert_node("a", "node", "A", "{}", 1.0);
        graph.upsert_node("b", "node", "B", "{}", 1.0);
        graph.upsert_node("c", "node", "C", "{}", 1.0);

        graph.upsert_edge("a", "b", "CONNECTS", 1.0, "{}");
        graph.upsert_edge("b", "c", "CONNECTS", 1.0, "{}");
        graph.upsert_edge("a", "c", "CONNECTS", 0.1, "{}");

        let path = graph.shortest_path("a", "c");
        assert!(path.is_some());
        assert_eq!(
            path.as_deref(),
            Some(&["a".to_string(), "b".to_string(), "c".to_string()][..])
        );
    }

    #[test]
    fn test_k_hop_subgraph() {
        let mut graph = ContextGraph::new();
        graph.upsert_node("root", "agent", "Root", "{}", 1.0);
        graph.upsert_node("c1", "child", "Child1", "{}", 1.0);
        graph.upsert_node("c2", "child", "Child2", "{}", 1.0);
        graph.upsert_node("gc1", "grandchild", "GC1", "{}", 1.0);

        graph.upsert_edge("root", "c1", "HAS", 1.0, "{}");
        graph.upsert_edge("root", "c2", "HAS", 1.0, "{}");
        graph.upsert_edge("c1", "gc1", "HAS", 1.0, "{}");

        let (nodes_1hop, _) = graph.k_hop_subgraph("root", 1, 10);
        assert_eq!(nodes_1hop.len(), 3);

        let (nodes_2hop, _) = graph.k_hop_subgraph("root", 2, 10);
        assert_eq!(nodes_2hop.len(), 4);
    }

    #[test]
    fn test_pagerank_convergence() {
        let mut graph = ContextGraph::new();
        graph.upsert_node("hub", "node", "Hub", "{}", 1.0);
        graph.upsert_node("p1", "node", "Page1", "{}", 1.0);
        graph.upsert_node("p2", "node", "Page2", "{}", 1.0);

        graph.upsert_edge("p1", "hub", "LINKS", 1.0, "{}");
        graph.upsert_edge("p2", "hub", "LINKS", 1.0, "{}");

        let ranked = graph.pagerank(0.85, 20);
        assert_eq!(ranked.len(), 3);
        assert_eq!(ranked.first().map(|r| r.0.as_str()), Some("hub"));
    }
}
