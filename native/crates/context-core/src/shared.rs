use std::collections::HashMap;
use std::sync::{Arc, Mutex, PoisonError, RwLock};

use crate::delta::Delta;
use crate::error::ContextResult;
use crate::render::{Request, render};
use crate::seal::Sealer;
use crate::settings::ContextSettings;
use crate::snapshot::Snapshot;

struct Inner {
    settings: ContextSettings,
    sealer: Sealer,
    current: RwLock<Arc<Snapshot>>,
    cache: Mutex<Cache>,
}

#[derive(Default)]
struct Cache {
    version: u64,
    entries: HashMap<String, Arc<str>>,
}

#[derive(Clone)]
pub struct SharedContext {
    inner: Arc<Inner>,
}

impl std::fmt::Debug for SharedContext {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("SharedContext(..)")
    }
}

impl SharedContext {
    pub fn new(settings: ContextSettings, sealer: Sealer) -> ContextResult<Self> {
        settings.validate()?;
        Ok(Self {
            inner: Arc::new(Inner {
                settings,
                sealer,
                current: RwLock::new(Arc::new(Snapshot::default())),
                cache: Mutex::new(Cache::default()),
            }),
        })
    }

    #[must_use]
    pub fn snapshot(&self) -> Arc<Snapshot> {
        let guard = self
            .inner
            .current
            .read()
            .unwrap_or_else(PoisonError::into_inner);
        Arc::clone(&guard)
    }

    #[must_use]
    pub fn settings(&self) -> &ContextSettings {
        &self.inner.settings
    }

    #[must_use]
    pub fn sealer(&self) -> &Sealer {
        &self.inner.sealer
    }

    pub fn apply(&self, delta: Delta) -> ContextResult<u64> {
        let mut guard = self
            .inner
            .current
            .write()
            .unwrap_or_else(PoisonError::into_inner);
        let next = Arc::new(guard.apply(delta, &self.inner.settings)?);
        let version = next.version();
        *guard = next;
        Ok(version)
    }

    pub fn apply_all(&self, deltas: Vec<Delta>) -> ContextResult<u64> {
        let mut guard = self
            .inner
            .current
            .write()
            .unwrap_or_else(PoisonError::into_inner);
        let mut working = Arc::clone(&guard);
        for delta in deltas {
            working = Arc::new(working.apply(delta, &self.inner.settings)?);
        }
        let version = working.version();
        *guard = working;
        Ok(version)
    }

    #[must_use]
    pub fn render(&self, request: &Request) -> Arc<str> {
        let snapshot = self.snapshot();
        let key = request.cache_key(self.inner.settings.cache_bucket_ms);
        {
            let mut cache = self
                .inner
                .cache
                .lock()
                .unwrap_or_else(PoisonError::into_inner);
            if cache.version != snapshot.version() {
                cache.entries.clear();
                cache.version = snapshot.version();
            }
            if let Some(hit) = cache.entries.get(&key) {
                return Arc::clone(hit);
            }
        }
        let text: Arc<str> =
            render(&snapshot, request, &self.inner.settings, &self.inner.sealer).into();
        let mut cache = self
            .inner
            .cache
            .lock()
            .unwrap_or_else(PoisonError::into_inner);
        if cache.version == snapshot.version() {
            if cache.entries.len() >= self.inner.settings.render_cache_entries {
                cache.entries.clear();
            }
            cache.entries.insert(key, Arc::clone(&text));
        }
        text
    }
}
