mod call;
mod view;

use std::collections::HashMap;
use std::sync::atomic::AtomicU64;
use std::sync::{Arc, Mutex, PoisonError, RwLock};

use crate::audit::{AuditChain, AuditSink};
use crate::connect::connect_server;
use crate::error::McpResult;
use crate::internal::InternalRegistry;
use crate::keystore::SecretProvider;
use crate::policy::{Gate, PolicyConfig, Scope, classify};
use crate::protocol::Implementation;
use crate::registry::Registry;
use crate::runner::{Classifier, ServerHandle, SessionSlot, spawn_server};
use crate::settings::Settings;
use crate::transport::Link;
use crate::trust::{Catalog, ServerEntry};

pub use call::CallOutput;
pub use view::{ServerView, ToolView};

pub(super) struct Running {
    pub(super) entry: ServerEntry,
    pub(super) handle: ServerHandle,
    pub(super) slot: SessionSlot,
}

pub struct Hub {
    pub(super) settings: Settings,
    pub(super) policy: PolicyConfig,
    pub(super) registry: Arc<Registry>,
    pub(super) gate: Gate,
    pub(super) audit: Mutex<AuditChain<Box<dyn AuditSink>>>,
    secrets: Arc<dyn SecretProvider>,
    internal: Arc<InternalRegistry>,
    pub(super) servers: Mutex<HashMap<String, Running>>,
    pub(super) scopes: RwLock<HashMap<String, Scope>>,
    pub(super) counter: AtomicU64,
}

impl std::fmt::Debug for Hub {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Hub").finish_non_exhaustive()
    }
}

impl Hub {
    pub fn new(
        settings: Settings,
        policy: PolicyConfig,
        secrets: Arc<dyn SecretProvider>,
        sink: Box<dyn AuditSink>,
        resume: Option<(u64, String)>,
    ) -> McpResult<Self> {
        settings.validate()?;
        policy.validate()?;
        let chain = match resume {
            Some((seq, head)) => AuditChain::resume(sink, seq, head),
            None => AuditChain::new(sink),
        };
        Ok(Self {
            registry: Arc::new(Registry::new(settings.clone())),
            gate: Gate::new(policy.clone()),
            audit: Mutex::new(chain),
            secrets,
            internal: Arc::new(InternalRegistry::default()),
            servers: Mutex::new(HashMap::new()),
            scopes: RwLock::new(HashMap::new()),
            counter: AtomicU64::new(0),
            settings,
            policy,
        })
    }

    #[must_use]
    pub fn registry(&self) -> &Arc<Registry> {
        &self.registry
    }

    #[must_use]
    pub fn internal(&self) -> &Arc<InternalRegistry> {
        &self.internal
    }

    pub fn set_scopes(&self, scopes: HashMap<String, Scope>) {
        *self.scopes.write().unwrap_or_else(PoisonError::into_inner) = scopes;
    }

    pub fn approve(&self, tool_id: &str) -> McpResult<()> {
        self.registry.approve(tool_id)
    }

    pub fn apply_catalog(&self, catalog: &Catalog) -> McpResult<()> {
        catalog.validate()?;
        let mut servers = self.servers.lock().unwrap_or_else(PoisonError::into_inner);
        let wanted: HashMap<&str, &ServerEntry> = catalog
            .servers
            .iter()
            .filter(|e| e.enabled)
            .map(|e| (e.id.as_str(), e))
            .collect();
        let stale: Vec<String> = servers
            .iter()
            .filter(|(id, running)| wanted.get(id.as_str()).is_none_or(|e| **e != running.entry))
            .map(|(id, _)| id.clone())
            .collect();
        for id in stale {
            if let Some(running) = servers.remove(&id) {
                running.handle.shutdown();
                let _ = self.registry.retire(&id);
            }
        }
        for (id, entry) in wanted {
            if !servers.contains_key(id) {
                servers.insert(id.to_owned(), self.start(entry)?);
            }
        }
        Ok(())
    }

    fn start(&self, entry: &ServerEntry) -> McpResult<Running> {
        let slot: SessionSlot = Arc::default();
        let classifier: Classifier = {
            let policy = self.policy.clone();
            let honor = entry.honor_read_only;
            Arc::new(move |spec| classify(spec, honor, &policy))
        };
        let connect = {
            let entry = entry.clone();
            let secrets = Arc::clone(&self.secrets);
            let policy = self.policy.clone();
            let settings = self.settings.clone();
            let internal = Arc::clone(&self.internal);
            move || {
                let (entry, secrets, policy, settings, internal) = (
                    entry.clone(),
                    Arc::clone(&secrets),
                    policy.clone(),
                    settings.clone(),
                    Arc::clone(&internal),
                );
                async move { connect_link(&entry, &*secrets, &policy, &settings, &internal).await }
            }
        };
        let client = Implementation {
            name: "nuxiva".into(),
            version: env!("CARGO_PKG_VERSION").into(),
            title: None,
        };
        let handle = spawn_server(
            &entry.id,
            connect,
            Arc::clone(&self.registry),
            self.settings.clone(),
            client,
            classifier,
            Arc::clone(&slot),
        )?;
        Ok(Running {
            entry: entry.clone(),
            handle,
            slot,
        })
    }

    pub fn shutdown(&self) {
        let mut servers = self.servers.lock().unwrap_or_else(PoisonError::into_inner);
        for (id, running) in servers.drain() {
            running.handle.shutdown();
            let _ = self.registry.retire(&id);
        }
    }
}

async fn connect_link(
    entry: &ServerEntry,
    secrets: &dyn SecretProvider,
    policy: &PolicyConfig,
    settings: &Settings,
    internal: &InternalRegistry,
) -> McpResult<Link> {
    connect_server(entry, secrets, policy, settings, internal).await
}
