use std::collections::{BTreeMap, VecDeque};

#[derive(Debug, Default)]
pub struct Health {
    errors: BTreeMap<String, VecDeque<u64>>,
    quarantine: BTreeMap<String, u64>,
}

impl Health {
    pub fn record(
        &mut self,
        widget: &str,
        now_ms: u64,
        window_ms: u64,
        limit: usize,
        quarantine_ms: u64,
    ) -> bool {
        let list = self.errors.entry(widget.to_owned()).or_default();
        list.push_back(now_ms);
        while list
            .front()
            .is_some_and(|t| now_ms.saturating_sub(*t) > window_ms)
        {
            list.pop_front();
        }
        if list.len() >= limit {
            list.clear();
            self.quarantine
                .insert(widget.to_owned(), now_ms.saturating_add(quarantine_ms));
            return true;
        }
        false
    }

    #[must_use]
    pub fn blocked(&self, widget: &str, now_ms: u64) -> bool {
        self.quarantine
            .get(widget)
            .is_some_and(|until| *until > now_ms)
    }

    pub fn expire(&mut self, now_ms: u64) {
        self.quarantine.retain(|_, until| *until > now_ms);
    }

    #[must_use]
    pub fn quarantined(&self, now_ms: u64) -> Vec<String> {
        self.quarantine
            .iter()
            .filter(|(_, until)| **until > now_ms)
            .map(|(w, _)| w.clone())
            .collect()
    }
}
