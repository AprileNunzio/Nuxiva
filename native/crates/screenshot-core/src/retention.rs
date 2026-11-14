use crate::config::Retention;
use crate::sink::{Entry, Sink};

#[must_use]
pub fn plan(entries: &[Entry], retention: &Retention, now: u64) -> Vec<String> {
    let mut sorted: Vec<&Entry> = entries.iter().collect();
    sorted.sort_by_key(|e| (e.stamp, e.name.clone()));
    let mut doomed: Vec<String> = Vec::new();
    let horizon = u64::from(retention.days).saturating_mul(86_400);
    let mut kept: Vec<&Entry> = Vec::new();
    for entry in sorted {
        if retention.days > 0 && now.saturating_sub(entry.stamp) > horizon {
            doomed.push(entry.name.clone());
        } else {
            kept.push(entry);
        }
    }
    let max_files = usize::try_from(retention.max_files).unwrap_or(usize::MAX);
    let mut total: u64 = kept.iter().map(|e| e.size).sum();
    let mut index = 0usize;
    while let Some(entry) = kept.get(index) {
        let over_count = kept.len().saturating_sub(index) > max_files;
        if !over_count && total <= retention.max_bytes {
            break;
        }
        doomed.push(entry.name.clone());
        total = total.saturating_sub(entry.size);
        index = index.saturating_add(1);
    }
    doomed
}

pub fn prune(sink: &dyn Sink, retention: &Retention, now: u64) -> usize {
    let Ok(entries) = sink.list() else {
        return 0;
    };
    plan(&entries, retention, now)
        .iter()
        .filter(|name| sink.remove(name).is_ok())
        .count()
}
