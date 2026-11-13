use std::collections::HashMap;
use std::sync::{Arc, PoisonError, RwLock};

use crate::error::{McpError, McpResult};
use crate::normalize::valid_server_id;
use crate::transport::Link;

pub type Factory = Arc<dyn Fn() -> McpResult<Link> + Send + Sync>;

#[derive(Default)]
pub struct InternalRegistry {
    factories: RwLock<HashMap<String, Factory>>,
}

impl std::fmt::Debug for InternalRegistry {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("InternalRegistry").finish_non_exhaustive()
    }
}

impl InternalRegistry {
    pub fn register(&self, name: &str, factory: Factory) -> McpResult<()> {
        if !valid_server_id(name) {
            return Err(McpError::InvalidName);
        }
        self.factories
            .write()
            .unwrap_or_else(PoisonError::into_inner)
            .insert(name.to_owned(), factory);
        Ok(())
    }

    pub fn remove(&self, name: &str) {
        self.factories
            .write()
            .unwrap_or_else(PoisonError::into_inner)
            .remove(name);
    }

    pub fn clear(&self) {
        self.factories
            .write()
            .unwrap_or_else(PoisonError::into_inner)
            .clear();
    }

    pub fn open(&self, name: &str) -> McpResult<Link> {
        let factory = self
            .factories
            .read()
            .unwrap_or_else(PoisonError::into_inner)
            .get(name)
            .cloned()
            .ok_or(McpError::InvalidName)?;
        factory()
    }
}
