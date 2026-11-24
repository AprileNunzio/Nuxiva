use std::collections::BTreeSet;

use crate::plan::Plan;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Agreement {
    pub shared: usize,
    pub only_new: usize,
    pub only_old: usize,
}

impl Agreement {
    #[must_use]
    pub fn matches(&self) -> bool {
        self.only_new == 0 && self.only_old == 0
    }
}

#[must_use]
pub fn compare(plan: &Plan, legacy_tools: &[&str]) -> Agreement {
    let new: BTreeSet<&str> = plan
        .steps
        .iter()
        .filter_map(|s| s.capability.as_deref())
        .collect();
    let old: BTreeSet<&str> = legacy_tools.iter().copied().collect();
    Agreement {
        shared: new.intersection(&old).count(),
        only_new: new.difference(&old).count(),
        only_old: old.difference(&new).count(),
    }
}
