use std::sync::PoisonError;
use std::time::Instant;

use serde::Serialize;

use super::Hub;
use crate::critic::Remedy;
use crate::error::{McpError, McpResult};
use crate::payload::ErrorPayload;

#[derive(Debug, Clone, Serialize)]
pub struct HealReport {
    pub errors: Vec<ErrorPayload>,
    pub remedies: Vec<Remedy>,
    pub dropped: u64,
}

impl Hub {
    pub fn report(&self, component: &str, code: &str, context: &str) {
        self.errors.report(component, code, context);
    }

    pub fn restart_server(&self, id: &str) -> McpResult<()> {
        let mut servers = self.servers.lock().unwrap_or_else(PoisonError::into_inner);
        let running = servers.remove(id).ok_or(McpError::UnknownTool)?;
        let entry = running.entry.clone();
        running.handle.shutdown();
        let _ = self.registry.retire(id);
        servers.insert(id.to_owned(), self.start(&entry)?);
        Ok(())
    }

    pub fn quarantine_server(&self, id: &str) {
        self.quarantined
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .insert(id.to_owned());
        let mut servers = self.servers.lock().unwrap_or_else(PoisonError::into_inner);
        if let Some(running) = servers.remove(id) {
            running.handle.shutdown();
            let _ = self.registry.retire(id);
        }
    }

    pub fn release_quarantine(&self, id: &str) -> McpResult<()> {
        self.quarantined
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .remove(id);
        let catalog = self
            .catalog
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .clone();
        catalog.map_or(Ok(()), |c| self.apply_catalog(&c))
    }

    #[must_use]
    pub fn quarantined(&self) -> Vec<String> {
        let mut ids: Vec<String> = self
            .quarantined
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .iter()
            .cloned()
            .collect();
        ids.sort();
        ids
    }

    pub fn heal(&self) -> HealReport {
        let errors = self.errors.drain();
        let now = Instant::now();
        let mut remedies = Vec::new();
        {
            let mut critic = self.critic.lock().unwrap_or_else(PoisonError::into_inner);
            for payload in &errors {
                if let Some(remedy) = critic.advise(payload, now) {
                    remedies.push(remedy);
                }
            }
        }
        for remedy in &remedies {
            match remedy {
                Remedy::RestartServer(id) => {
                    let _ = self.restart_server(id);
                }
                Remedy::QuarantineServer(id) => self.quarantine_server(id),
                Remedy::RestartTask(_)
                | Remedy::RetryWithBackoff(_)
                | Remedy::EscalateToUser(_) => {}
            }
        }
        HealReport {
            errors,
            remedies,
            dropped: self.errors.dropped(),
        }
    }
}
