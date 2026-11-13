use std::collections::{BTreeMap, HashSet};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, PoisonError, RwLock};

use super::compat::compatible;
use super::entry::{ToolEntry, ToolState};
use crate::error::{McpError, McpResult};
use crate::normalize::valid_server_id;
use crate::settings::{ChangePolicy, Settings};

#[derive(Debug, Clone, Default)]
pub struct Snapshot {
    tools: BTreeMap<String, Arc<ToolEntry>>,
}

impl Snapshot {
    #[must_use]
    pub fn len(&self) -> usize {
        self.tools.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.tools.is_empty()
    }

    #[must_use]
    pub fn get(&self, id: &str) -> Option<&Arc<ToolEntry>> {
        self.tools.get(id)
    }

    #[must_use]
    pub fn callable(&self, id: &str) -> Option<&Arc<ToolEntry>> {
        self.tools.get(id).filter(|entry| entry.callable())
    }

    pub fn iter(&self) -> impl Iterator<Item = &Arc<ToolEntry>> {
        self.tools.values()
    }

    pub fn server_tools<'a>(&'a self, server: &'a str) -> impl Iterator<Item = &'a Arc<ToolEntry>> {
        self.tools
            .values()
            .filter(move |entry| entry.server == server)
    }
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Diff {
    pub added: Vec<String>,
    pub removed: Vec<String>,
    pub modified: Vec<String>,
    pub quarantined: Vec<String>,
    pub rejected: usize,
}

impl Diff {
    #[must_use]
    pub fn changed(&self) -> bool {
        !(self.added.is_empty()
            && self.removed.is_empty()
            && self.modified.is_empty()
            && self.quarantined.is_empty())
    }
}

#[derive(Debug)]
pub struct Registry {
    current: RwLock<Arc<Snapshot>>,
    settings: Settings,
    version: AtomicU64,
}

impl Registry {
    #[must_use]
    pub fn new(settings: Settings) -> Self {
        Self {
            current: RwLock::new(Arc::new(Snapshot::default())),
            settings,
            version: AtomicU64::new(0),
        }
    }

    #[must_use]
    pub fn version(&self) -> u64 {
        self.version.load(Ordering::Acquire)
    }

    #[must_use]
    pub fn snapshot(&self) -> Arc<Snapshot> {
        Arc::clone(&self.current.read().unwrap_or_else(PoisonError::into_inner))
    }

    fn replace(
        &self,
        build: impl FnOnce(&Snapshot) -> McpResult<(Snapshot, Diff)>,
    ) -> McpResult<Diff> {
        let mut guard = self.current.write().unwrap_or_else(PoisonError::into_inner);
        let (next, diff) = build(&guard)?;
        *guard = Arc::new(next);
        self.version.fetch_add(1, Ordering::AcqRel);
        Ok(diff)
    }

    pub fn apply(&self, server: &str, candidates: Vec<ToolEntry>) -> McpResult<Diff> {
        if !valid_server_id(server) {
            return Err(McpError::InvalidName);
        }
        self.replace(|old| {
            let mut tools = old.tools.clone();
            let mut diff = Diff::default();
            let fresh: HashSet<String> = candidates.iter().map(|c| c.id.clone()).collect();
            for stale in old.server_tools(server).filter(|e| !fresh.contains(&e.id)) {
                tools.remove(&stale.id);
                diff.removed.push(stale.id.clone());
            }
            for candidate in candidates {
                if candidate.server != server {
                    diff.rejected = diff.rejected.saturating_add(1);
                    continue;
                }
                self.merge(&mut tools, old, candidate, &mut diff);
            }
            Ok((Snapshot { tools }, diff))
        })
    }

    fn merge(
        &self,
        tools: &mut BTreeMap<String, Arc<ToolEntry>>,
        old: &Snapshot,
        candidate: ToolEntry,
        diff: &mut Diff,
    ) {
        let Some(existing) = old.get(&candidate.id) else {
            if tools.len() >= self.settings.max_tools_total {
                diff.rejected = diff.rejected.saturating_add(1);
                return;
            }
            diff.added.push(candidate.id.clone());
            tools.insert(candidate.id.clone(), Arc::new(candidate));
            return;
        };
        if existing.hash == candidate.hash {
            if existing.state == ToolState::Stale {
                tools.insert(
                    existing.id.clone(),
                    Arc::new(existing.with_state(ToolState::Active)),
                );
            }
            return;
        }
        let accept = match self.settings.change_policy {
            ChangePolicy::Accept => true,
            ChangePolicy::Quarantine => false,
            ChangePolicy::Compatible => {
                existing.state != ToolState::Quarantined
                    && compatible(&existing.spec, &candidate.spec)
            }
        };
        let id = candidate.id.clone();
        if accept {
            diff.modified.push(id.clone());
            tools.insert(id, Arc::new(candidate));
        } else {
            diff.quarantined.push(id.clone());
            tools.insert(id, Arc::new(candidate.with_state(ToolState::Quarantined)));
        }
    }

    pub fn approve(&self, id: &str) -> McpResult<()> {
        self.replace(|old| {
            let entry = old.get(id).ok_or(McpError::UnknownTool)?;
            if entry.state != ToolState::Quarantined {
                return Err(McpError::NotCallable);
            }
            let mut tools = old.tools.clone();
            tools.insert(id.to_owned(), Arc::new(entry.with_state(ToolState::Active)));
            Ok((Snapshot { tools }, Diff::default()))
        })
        .map(|_| ())
    }

    pub fn mark_stale(&self, server: &str) -> McpResult<usize> {
        let mut count = 0usize;
        self.replace(|old| {
            let mut tools = old.tools.clone();
            for entry in old
                .server_tools(server)
                .filter(|e| e.state == ToolState::Active)
            {
                tools.insert(
                    entry.id.clone(),
                    Arc::new(entry.with_state(ToolState::Stale)),
                );
                count = count.saturating_add(1);
            }
            Ok((Snapshot { tools }, Diff::default()))
        })?;
        Ok(count)
    }

    pub fn retire(&self, server: &str) -> McpResult<Diff> {
        self.apply(server, Vec::new())
    }
}
