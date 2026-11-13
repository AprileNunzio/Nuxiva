use std::collections::HashSet;

use crate::error::McpResult;
use crate::policy::Risk;
use crate::registry::{Diff, Registry, ToolEntry};
use crate::session::Session;
use crate::settings::Settings;

#[must_use]
pub fn build_entries(
    server: &str,
    specs: Vec<crate::protocol::ToolSpec>,
    settings: &Settings,
    classify: &dyn Fn(&crate::protocol::ToolSpec) -> Risk,
) -> (Vec<ToolEntry>, usize) {
    let mut seen: HashSet<String> = HashSet::new();
    let mut entries = Vec::new();
    let mut rejected = 0usize;
    for spec in specs {
        let risk = classify(&spec);
        match ToolEntry::build(server, spec, settings).map(|entry| entry.with_risk(risk)) {
            Ok(entry) if seen.insert(entry.id.clone()) => entries.push(entry),
            _ => rejected = rejected.saturating_add(1),
        }
    }
    (entries, rejected)
}

pub async fn discover(
    session: &Session,
    server: &str,
    registry: &Registry,
    settings: &Settings,
    classify: &(dyn Fn(&crate::protocol::ToolSpec) -> Risk + Sync),
) -> McpResult<Diff> {
    let listing = session.list_tools().await?;
    let (entries, rejected) = build_entries(server, listing.tools, settings, classify);
    let mut diff = registry.apply(server, entries)?;
    diff.rejected = diff
        .rejected
        .saturating_add(rejected)
        .saturating_add(listing.rejected);
    Ok(diff)
}
