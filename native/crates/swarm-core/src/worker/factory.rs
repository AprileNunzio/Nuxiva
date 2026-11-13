use std::collections::BTreeMap;
use std::future::Future;
use std::pin::Pin;
use std::sync::Arc;

use serde_json::Value;

use super::context::StepContext;
use crate::wire::{Ident, WorkerError};

pub type BoxFuture<'a, T> = Pin<Box<dyn Future<Output = T> + Send + 'a>>;

#[derive(Debug, Clone, PartialEq)]
pub struct Output {
    pub value: Value,
    pub evidence: Vec<Ident>,
}

pub trait Worker: Send + Sync {
    fn run(&self, context: StepContext) -> BoxFuture<'_, Result<Output, WorkerError>>;
}

#[derive(Clone, Default)]
pub struct Factory {
    kinds: BTreeMap<String, Arc<dyn Worker>>,
}

impl std::fmt::Debug for Factory {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Factory")
            .field("kinds", &self.kinds.keys().collect::<Vec<_>>())
            .finish()
    }
}

impl Factory {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn register(&mut self, kind: &str, worker: Arc<dyn Worker>) {
        self.kinds.insert(kind.to_owned(), worker);
    }

    #[must_use]
    pub fn get(&self, kind: &str) -> Option<Arc<dyn Worker>> {
        self.kinds.get(kind).map(Arc::clone)
    }

    #[must_use]
    pub fn kinds(&self) -> Vec<&str> {
        self.kinds.keys().map(String::as_str).collect()
    }
}
