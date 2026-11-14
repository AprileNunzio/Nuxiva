use std::sync::Arc;

use nuxiva_context_core::{Delta, PersonId, SharedContext, Snapshot};
use tokio::sync::RwLock;

use crate::error::BrainResult;

#[derive(Debug, Clone)]
pub struct UserContext {
    shared: SharedContext,
    active: Option<PersonId>,
    last_utterance_ms: u64,
    listening: bool,
    turns: u64,
}

impl UserContext {
    #[must_use]
    pub fn new(shared: SharedContext) -> Self {
        Self {
            shared,
            active: None,
            last_utterance_ms: 0,
            listening: true,
            turns: 0,
        }
    }

    #[must_use]
    pub fn snapshot(&self) -> Arc<Snapshot> {
        self.shared.snapshot()
    }

    #[must_use]
    pub fn active(&self) -> Option<&PersonId> {
        self.active.as_ref()
    }

    #[must_use]
    pub fn last_utterance_ms(&self) -> u64 {
        self.last_utterance_ms
    }

    #[must_use]
    pub fn listening(&self) -> bool {
        self.listening
    }

    #[must_use]
    pub fn turns(&self) -> u64 {
        self.turns
    }

    #[must_use]
    pub fn shared(&self) -> &SharedContext {
        &self.shared
    }
}

#[derive(Debug, Clone)]
pub struct HotMemory {
    inner: Arc<RwLock<UserContext>>,
}

impl HotMemory {
    #[must_use]
    pub fn new(shared: SharedContext) -> Self {
        Self {
            inner: Arc::new(RwLock::new(UserContext::new(shared))),
        }
    }

    pub async fn snapshot(&self) -> Arc<Snapshot> {
        self.inner.read().await.snapshot()
    }

    pub async fn active(&self) -> Option<PersonId> {
        self.inner.read().await.active.clone()
    }

    pub async fn listening(&self) -> bool {
        self.inner.read().await.listening
    }

    pub async fn turns(&self) -> u64 {
        self.inner.read().await.turns
    }

    pub async fn last_utterance_ms(&self) -> u64 {
        self.inner.read().await.last_utterance_ms
    }

    pub async fn set_listening(&self, listening: bool) {
        self.inner.write().await.listening = listening;
    }

    pub async fn register_turn(&self, speaker: Option<PersonId>, at_ms: u64) {
        let mut guard = self.inner.write().await;
        guard.active = speaker;
        guard.last_utterance_ms = guard.last_utterance_ms.max(at_ms);
        guard.turns = guard.turns.saturating_add(1);
    }

    pub async fn apply(&self, delta: Delta) -> BrainResult<u64> {
        let shared = self.inner.read().await.shared.clone();
        shared.apply(delta).map_err(Into::into)
    }
}
