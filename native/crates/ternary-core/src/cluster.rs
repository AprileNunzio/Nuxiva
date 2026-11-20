use crate::error::TernaryError;
use crate::vector::TernaryVector;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MicroCluster {
    pub id: u64,
    pub project_id: Option<String>,
    pub domain: String,
    pub centroid: TernaryVector,
    pub accum: Vec<i32>,
    pub member_ids: Vec<String>,
    pub created_at_ms: u64,
    pub updated_at_ms: u64,
}

impl MicroCluster {
    pub fn new(
        id: u64,
        project_id: Option<String>,
        domain: String,
        initial_id: String,
        vector: TernaryVector,
        timestamp_ms: u64,
    ) -> Result<Self, TernaryError> {
        let dim = vector.dim();
        let mut accum = vec![0i32; dim];
        vector.accumulate_into(&mut accum)?;
        Ok(Self {
            id,
            project_id,
            domain,
            centroid: vector,
            accum,
            member_ids: vec![initial_id],
            created_at_ms: timestamp_ms,
            updated_at_ms: timestamp_ms,
        })
    }

    pub fn insert(
        &mut self,
        id: String,
        vector: &TernaryVector,
        timestamp_ms: u64,
    ) -> Result<(), TernaryError> {
        if vector.dim() != self.centroid.dim() {
            return Err(TernaryError::DimensionMismatch {
                expected: self.centroid.dim(),
                actual: vector.dim(),
            });
        }
        vector.accumulate_into(&mut self.accum)?;
        self.centroid = TernaryVector::from_accum(&self.accum)?;
        self.member_ids.push(id);
        self.updated_at_ms = timestamp_ms;
        Ok(())
    }

    pub fn similarity(&self, vector: &TernaryVector) -> Result<f32, TernaryError> {
        self.centroid.cosine_similarity(vector)
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.member_ids.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.member_ids.is_empty()
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SynthesisNode {
    pub id: u64,
    pub cluster_id: u64,
    pub project_id: Option<String>,
    pub domain: String,
    pub centroid: TernaryVector,
    pub summary: String,
    pub member_ids: Vec<String>,
    pub created_at_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClusterEngine {
    dim: usize,
    cluster_threshold: f32,
    max_cluster_size: usize,
    next_cluster_id: u64,
    next_synthesis_id: u64,
    clusters: Vec<MicroCluster>,
    synthesis_nodes: Vec<SynthesisNode>,
}

impl ClusterEngine {
    pub fn new(
        dim: usize,
        cluster_threshold: f32,
        max_cluster_size: usize,
    ) -> Result<Self, TernaryError> {
        if dim == 0 {
            return Err(TernaryError::EmptyVector);
        }
        Ok(Self {
            dim,
            cluster_threshold,
            max_cluster_size,
            next_cluster_id: 1,
            next_synthesis_id: 1,
            clusters: Vec::new(),
            synthesis_nodes: Vec::new(),
        })
    }

    #[must_use]
    pub fn dim(&self) -> usize {
        self.dim
    }

    #[must_use]
    pub fn clusters(&self) -> &[MicroCluster] {
        &self.clusters
    }

    #[must_use]
    pub fn synthesis_nodes(&self) -> &[SynthesisNode] {
        &self.synthesis_nodes
    }

    #[must_use]
    pub fn get_cluster(&self, cluster_id: u64) -> Option<&MicroCluster> {
        self.clusters.iter().find(|c| c.id == cluster_id)
    }

    pub fn ingest(
        &mut self,
        id: String,
        vector: TernaryVector,
        project_id: Option<String>,
        domain: String,
        timestamp_ms: u64,
    ) -> Result<u64, TernaryError> {
        if vector.dim() != self.dim {
            return Err(TernaryError::DimensionMismatch {
                expected: self.dim,
                actual: vector.dim(),
            });
        }

        let mut best_index: Option<usize> = None;
        let mut best_similarity: f32 = self.cluster_threshold;

        for (idx, cluster) in self.clusters.iter().enumerate() {
            if cluster.project_id == project_id
                && cluster.domain == domain
                && cluster.len() < self.max_cluster_size
            {
                let sim = cluster.similarity(&vector)?;
                if sim >= best_similarity {
                    best_similarity = sim;
                    best_index = Some(idx);
                }
            }
        }

        if let Some(idx) = best_index {
            if let Some(target_cluster) = self.clusters.get_mut(idx) {
                target_cluster.insert(id, &vector, timestamp_ms)?;
                return Ok(target_cluster.id);
            }
        }

        let cluster_id = self.next_cluster_id;
        self.next_cluster_id = self.next_cluster_id.saturating_add(1);
        let new_cluster =
            MicroCluster::new(cluster_id, project_id, domain, id, vector, timestamp_ms)?;
        self.clusters.push(new_cluster);
        Ok(cluster_id)
    }

    pub fn search_centroids(
        &self,
        query: &TernaryVector,
        top_k: usize,
    ) -> Result<Vec<(u64, f32)>, TernaryError> {
        if query.dim() != self.dim {
            return Err(TernaryError::DimensionMismatch {
                expected: self.dim,
                actual: query.dim(),
            });
        }
        let mut scored: Vec<(u64, f32)> = Vec::with_capacity(self.clusters.len());
        for cluster in &self.clusters {
            let sim = cluster.similarity(query)?;
            scored.push((cluster.id, sim));
        }
        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        scored.truncate(top_k);
        Ok(scored)
    }

    pub fn synthesize(
        &mut self,
        cluster_id: u64,
        summary: String,
        timestamp_ms: u64,
    ) -> Result<SynthesisNode, TernaryError> {
        let (project_id, domain, centroid, member_ids) = {
            let cluster = self
                .get_cluster(cluster_id)
                .ok_or(TernaryError::ClusterNotFound { id: cluster_id })?;
            (
                cluster.project_id.clone(),
                cluster.domain.clone(),
                cluster.centroid.clone(),
                cluster.member_ids.clone(),
            )
        };

        let synthesis_id = self.next_synthesis_id;
        self.next_synthesis_id = self.next_synthesis_id.saturating_add(1);

        let node = SynthesisNode {
            id: synthesis_id,
            cluster_id,
            project_id,
            domain,
            centroid,
            summary,
            member_ids,
            created_at_ms: timestamp_ms,
        };

        self.synthesis_nodes.push(node.clone());
        Ok(node)
    }
}
