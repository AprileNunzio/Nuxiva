use std::path::Path;
use std::time::Instant;

use super::config::BenchConfig;
use super::corpus::{generate, remove_file, write_file};
use super::error::BenchError;
use super::measure::{elapsed_millis, measure_query, peak_rss_bytes};
use super::report::{BenchReport, Environment, IncrementalReport, SyncReport};
use crate::{CodeIndex, Limits, SyncStats};

fn limits(config: &BenchConfig) -> Limits {
    Limits {
        max_files: config.total_capacity(),
        max_depth: 16,
        max_file_bytes: 1024 * 1024,
    }
}

fn timed_sync(
    index: &mut CodeIndex,
    root: &Path,
    config: &BenchConfig,
) -> Result<SyncReport, BenchError> {
    let start = Instant::now();
    let stats = index.sync_incremental(root, limits(config))?;
    Ok(SyncReport {
        stats,
        millis: elapsed_millis(start),
    })
}

fn apply_mutations(root: &Path, config: &BenchConfig) -> Result<(), BenchError> {
    for offset in 0..config.updated_files {
        write_file(root, config, offset, 1)?;
    }
    for offset in 0..config.removed_files {
        let target = config.files.saturating_sub(1).saturating_sub(offset);
        remove_file(root, config, target)?;
    }
    for offset in 0..config.added_files {
        write_file(root, config, config.files.saturating_add(offset), 0)?;
    }
    Ok(())
}

fn expected(config: &BenchConfig, before: usize) -> (SyncStats, usize) {
    let stats = SyncStats {
        added: config.added_files,
        updated: config.updated_files,
        removed: config.removed_files,
        unchanged: before
            .saturating_sub(config.updated_files)
            .saturating_sub(config.removed_files),
    };
    let total = before
        .saturating_add(config.added_files)
        .saturating_sub(config.removed_files);
    (stats, total)
}

pub fn run(root: &Path, config: &BenchConfig) -> Result<BenchReport, BenchError> {
    config.validate()?;
    let start = Instant::now();
    generate(root, config)?;
    let generate_millis = elapsed_millis(start);

    let mut index = CodeIndex::new(
        config.total_capacity().saturating_add(1_000),
        config.max_memory_bytes,
    );
    let cold_sync = timed_sync(&mut index, root, config)?;
    let indexed_files = index.file_count();
    let estimated_memory_bytes = index.estimated_memory_bytes();

    let search = config
        .search_queries
        .iter()
        .map(|query| measure_query(&index, query, config.search_limit, config.search_rounds))
        .collect();

    apply_mutations(root, config)?;
    let sync = timed_sync(&mut index, root, config)?;
    let (expected_stats, expected_total) = expected(config, indexed_files);
    let incremental = IncrementalReport {
        consistent: sync.stats == expected_stats && index.file_count() == expected_total,
        indexed_files: index.file_count(),
        sync,
    };

    let noop_sync = timed_sync(&mut index, root, config)?;

    Ok(BenchReport {
        config: config.clone(),
        environment: Environment {
            os: std::env::consts::OS,
            arch: std::env::consts::ARCH,
            cpus: std::thread::available_parallelism().map_or(1, usize::from),
        },
        generate_millis,
        cold_sync,
        indexed_files,
        estimated_memory_bytes,
        peak_rss_bytes: peak_rss_bytes(),
        search,
        incremental,
        noop_sync,
    })
}
