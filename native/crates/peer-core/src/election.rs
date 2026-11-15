use crate::registry::Registry;
use nuxiva_node_core::hexutil;
use sha2::{Digest, Sha256};

fn weight(job: u64, node: &str) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(b"nuxiva-peer-election-v1");
    hasher.update(job.to_be_bytes());
    hasher.update(node.as_bytes());
    hasher.finalize().into()
}

#[must_use]
pub fn ranking(job: u64, registry: &Registry, limit: usize) -> Vec<String> {
    let mut ranked: Vec<([u8; 32], &String)> = registry
        .alive()
        .filter(|(_, e)| e.caps.roles.coordinate)
        .map(|(id, _)| (weight(job, id), id))
        .collect();
    ranked.sort_by(|a, b| b.0.cmp(&a.0).then(a.1.cmp(b.1)));
    ranked
        .into_iter()
        .take(limit)
        .map(|(_, id)| id.clone())
        .collect()
}

#[must_use]
pub fn coordinator_for(job: u64, registry: &Registry) -> Option<String> {
    ranking(job, registry, 1).into_iter().next()
}

#[must_use]
pub fn digest_hex(job: u64, node: &str) -> String {
    hexutil::encode(&weight(job, node))
}

#[must_use]
pub fn authorized(job: u64, sender: &str, registry: &Registry, depth: usize) -> bool {
    ranking(job, registry, depth).iter().any(|id| id == sender)
}
