use std::collections::HashMap;
use std::sync::{Mutex, PoisonError};

use crate::error::{SwarmError, SwarmResult};
use crate::settings::Settings;
use crate::wire::{Digest, Step, TaskEnvelope};

#[derive(Debug)]
pub struct GraphGate {
    ttl_ms: u64,
    capacity: usize,
    issued: Mutex<HashMap<Digest, u64>>,
}

impl GraphGate {
    #[must_use]
    pub fn new(settings: &Settings) -> Self {
        Self {
            ttl_ms: settings.graph_ref_ttl_ms,
            capacity: settings.max_graph_refs,
            issued: Mutex::new(HashMap::new()),
        }
    }

    pub fn issue(&self, reference: Digest, now_ms: u64) {
        let mut issued = self.issued.lock().unwrap_or_else(PoisonError::into_inner);
        issued.retain(|_, at| now_ms.saturating_sub(*at) <= self.ttl_ms);
        while issued.len() >= self.capacity {
            let oldest = issued
                .iter()
                .min_by_key(|(_, at)| **at)
                .map(|(k, _)| k.clone());
            match oldest {
                Some(key) => issued.remove(&key),
                None => break,
            };
        }
        issued.insert(reference, now_ms);
    }

    pub fn check(&self, step: &Step, task: &TaskEnvelope, now_ms: u64) -> SwarmResult<()> {
        if !step.needs_graph {
            return Ok(());
        }
        let reference = task
            .graph_ref
            .as_ref()
            .ok_or(SwarmError::GraphNotConsulted)?;
        let issued = self.issued.lock().unwrap_or_else(PoisonError::into_inner);
        let at = issued.get(reference).ok_or(SwarmError::GraphNotConsulted)?;
        if now_ms.saturating_sub(*at) > self.ttl_ms {
            return Err(SwarmError::GraphStale);
        }
        Ok(())
    }

    pub fn check_plan(
        &self,
        plan: &crate::wire::Plan,
        task: &TaskEnvelope,
        now_ms: u64,
    ) -> SwarmResult<()> {
        plan.steps
            .iter()
            .try_for_each(|step| self.check(step, task, now_ms))
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.issued
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}
