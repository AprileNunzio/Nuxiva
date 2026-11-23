use serde::Serialize;

use super::config::BenchConfig;
use crate::SyncStats;

#[derive(Debug, Clone, Serialize)]
pub struct Environment {
    pub os: &'static str,
    pub arch: &'static str,
    pub cpus: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct SyncReport {
    pub stats: SyncStats,
    pub millis: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct QueryReport {
    pub query: String,
    pub hits: usize,
    pub median_micros: u64,
    pub p95_micros: u64,
    pub max_micros: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct IncrementalReport {
    pub sync: SyncReport,
    pub consistent: bool,
    pub indexed_files: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct BenchReport {
    pub config: BenchConfig,
    pub environment: Environment,
    pub generate_millis: u64,
    pub cold_sync: SyncReport,
    pub indexed_files: usize,
    pub estimated_memory_bytes: usize,
    pub peak_rss_bytes: Option<u64>,
    pub search: Vec<QueryReport>,
    pub incremental: IncrementalReport,
    pub noop_sync: SyncReport,
}
