use std::time::Instant;

use super::report::QueryReport;
use crate::CodeIndex;

pub fn elapsed_micros(start: Instant) -> u64 {
    u64::try_from(start.elapsed().as_micros()).unwrap_or(u64::MAX)
}

pub fn elapsed_millis(start: Instant) -> u64 {
    u64::try_from(start.elapsed().as_millis()).unwrap_or(u64::MAX)
}

fn percentile(sorted: &[u64], numerator: usize) -> u64 {
    if sorted.is_empty() {
        return 0;
    }
    let last = sorted.len().saturating_sub(1);
    let rank = last.saturating_mul(numerator).div_ceil(100).min(last);
    sorted.get(rank).copied().unwrap_or(0)
}

pub fn measure_query(index: &CodeIndex, query: &str, limit: usize, rounds: usize) -> QueryReport {
    let mut samples = Vec::with_capacity(rounds);
    let mut hits = 0;
    for _ in 0..rounds {
        let start = Instant::now();
        hits = index.search(query, limit).len();
        samples.push(elapsed_micros(start));
    }
    samples.sort_unstable();
    QueryReport {
        query: query.to_owned(),
        hits,
        median_micros: percentile(&samples, 50),
        p95_micros: percentile(&samples, 95),
        max_micros: samples.last().copied().unwrap_or(0),
    }
}

#[must_use]
pub fn peak_rss_bytes() -> Option<u64> {
    let status = std::fs::read_to_string("/proc/self/status").ok()?;
    let line = status.lines().find(|l| l.starts_with("VmHWM:"))?;
    let kib: u64 = line.split_whitespace().nth(1)?.parse().ok()?;
    kib.checked_mul(1024)
}
