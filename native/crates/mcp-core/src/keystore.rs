use std::collections::HashMap;
use std::sync::{PoisonError, RwLock};

use zeroize::Zeroizing;

use crate::error::{McpError, McpResult};

pub struct Secret(Zeroizing<String>);

impl Secret {
    #[must_use]
    pub fn new(value: String) -> Self {
        Self(Zeroizing::new(value))
    }

    #[must_use]
    pub fn expose(&self) -> &str {
        self.0.as_str()
    }
}

impl std::fmt::Debug for Secret {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Secret(***)")
    }
}

pub trait SecretProvider: Send + Sync {
    fn get(&self, id: &str) -> McpResult<Secret>;
}

#[derive(Default)]
pub struct MemorySecrets(HashMap<String, String>);

impl std::fmt::Debug for MemorySecrets {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MemorySecrets")
            .field("entries", &self.0.len())
            .finish()
    }
}

impl MemorySecrets {
    pub fn insert(&mut self, id: &str, value: &str) {
        self.0.insert(id.to_owned(), value.to_owned());
    }
}

impl SecretProvider for MemorySecrets {
    fn get(&self, id: &str) -> McpResult<Secret> {
        self.0
            .get(id)
            .map(|v| Secret::new(v.clone()))
            .ok_or(McpError::SecretMissing)
    }
}

#[must_use]
pub fn bearer_header(secret: &Secret) -> (String, String) {
    (
        "authorization".to_owned(),
        format!("Bearer {}", secret.expose()),
    )
}

#[derive(Default)]
pub struct SharedSecrets(RwLock<HashMap<String, String>>);

impl std::fmt::Debug for SharedSecrets {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("SharedSecrets")
    }
}

impl SharedSecrets {
    pub fn set(&self, id: &str, value: &str) {
        self.0
            .write()
            .unwrap_or_else(PoisonError::into_inner)
            .insert(id.to_owned(), value.to_owned());
    }

    pub fn remove(&self, id: &str) {
        self.0
            .write()
            .unwrap_or_else(PoisonError::into_inner)
            .remove(id);
    }
}

impl SecretProvider for SharedSecrets {
    fn get(&self, id: &str) -> McpResult<Secret> {
        self.0
            .read()
            .unwrap_or_else(PoisonError::into_inner)
            .get(id)
            .map(|v| Secret::new(v.clone()))
            .ok_or(McpError::SecretMissing)
    }
}
