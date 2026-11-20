use crate::cluster::ClusterEngine;
use crate::error::TernaryError;
use crate::graph::{EdgeType, MemoryGraph};
use crate::tier::{TierManager, TierState};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SleepReport {
    pub demoted_to_warm: usize,
    pub demoted_to_cold: usize,
    pub clusters_total: usize,
    pub synthesized_count: usize,
    pub timestamp_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SleepConsolidator {
    min_cluster_size_to_synthesize: usize,
}

impl SleepConsolidator {
    #[must_use]
    pub const fn new(min_cluster_size_to_synthesize: usize) -> Self {
        Self {
            min_cluster_size_to_synthesize,
        }
    }

    pub fn consolidate(
        &self,
        tier_mgr: &mut TierManager,
        cluster_engine: &mut ClusterEngine,
        graph: &mut MemoryGraph,
        timestamp_ms: u64,
    ) -> Result<SleepReport, TernaryError> {
        let transitions = tier_mgr.evaluate_and_prune(timestamp_ms);
        let mut demoted_to_warm: usize = 0;
        let mut demoted_to_cold: usize = 0;

        for (_, _, to_tier) in transitions {
            match to_tier {
                TierState::Warm => {
                    demoted_to_warm = demoted_to_warm.saturating_add(1);
                }
                TierState::Cold => {
                    demoted_to_cold = demoted_to_cold.saturating_add(1);
                }
                TierState::Hot => {}
            }
        }

        let existing_synthesized: Vec<u64> = cluster_engine
            .synthesis_nodes()
            .iter()
            .map(|node| node.cluster_id)
            .collect();

        let eligible_clusters: Vec<(u64, String, Vec<String>)> = cluster_engine
            .clusters()
            .iter()
            .filter(|c| {
                c.len() >= self.min_cluster_size_to_synthesize
                    && !existing_synthesized.contains(&c.id)
            })
            .map(|c| (c.id, c.domain.clone(), c.member_ids.clone()))
            .collect();

        let mut synthesized_count: usize = 0;
        for (cluster_id, domain, members) in eligible_clusters {
            let summary = format!("Synthesis for {} [members: {}]", domain, members.len());
            let node = cluster_engine.synthesize(cluster_id, summary, timestamp_ms)?;
            synthesized_count = synthesized_count.saturating_add(1);

            let node_id_str = format!("synthesis:{}", node.id);
            for member_id in &members {
                graph.add_edge(
                    node_id_str.clone(),
                    member_id.clone(),
                    EdgeType::Derivation,
                    1.0,
                    timestamp_ms,
                );
            }
        }

        Ok(SleepReport {
            demoted_to_warm,
            demoted_to_cold,
            clusters_total: cluster_engine.clusters().len(),
            synthesized_count,
            timestamp_ms,
        })
    }
}
