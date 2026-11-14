use std::collections::{BTreeMap, VecDeque};
use std::sync::Mutex;

use crate::envelope::{Domain, Envelope, Level, RawEvent, SCHEMA};
use crate::error::CollaudoError;
use crate::redact::Redactor;
use crate::store::{Integrity, Query, Store, StoreConfig};
use crate::token::random_id;

const RING: usize = 2048;
const PER_SECOND: u32 = 200;
const FLUSH_EVERY: u64 = 64;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    Normal,
    Collaudo,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, serde::Serialize)]
pub struct Stats {
    pub emitted: u64,
    pub dropped_verbose: u64,
    pub dropped_rate: u64,
    pub rejected: u64,
}

#[derive(Debug)]
struct Inner {
    store: Store,
    ring: VecDeque<Envelope>,
    mode: Mode,
    stats: Stats,
    window: BTreeMap<String, (u64, u32)>,
    since_flush: u64,
}

#[derive(Debug)]
pub struct Hub {
    redactor: Redactor,
    inner: Mutex<Inner>,
}

fn now_ms() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |d| u64::try_from(d.as_millis()).unwrap_or(u64::MAX))
}

impl Hub {
    pub fn open(cfg: StoreConfig) -> Result<Self, CollaudoError> {
        let redactor = Redactor::new(cfg.key);
        let store = Store::open(cfg)?;
        Ok(Self {
            redactor,
            inner: Mutex::new(Inner {
                store,
                ring: VecDeque::with_capacity(RING),
                mode: Mode::Normal,
                stats: Stats::default(),
                window: BTreeMap::new(),
                since_flush: 0,
            }),
        })
    }

    fn lock(&self) -> Result<std::sync::MutexGuard<'_, Inner>, CollaudoError> {
        self.inner.lock().map_err(|_| CollaudoError::Poisoned)
    }

    pub fn set_mode(&self, mode: Mode) -> Result<(), CollaudoError> {
        self.lock()?.mode = mode;
        Ok(())
    }

    pub fn mode(&self) -> Result<Mode, CollaudoError> {
        Ok(self.lock()?.mode)
    }

    pub fn stats(&self) -> Result<Stats, CollaudoError> {
        Ok(self.lock()?.stats)
    }

    #[must_use]
    pub fn anon(&self, scope: &str, value: &str) -> String {
        self.redactor.anon(scope, value)
    }

    pub fn emit(&self, raw: RawEvent) -> Result<Option<u64>, CollaudoError> {
        let allow_free =
            matches!(raw.domain, Domain::Error | Domain::System) && raw.level >= Level::Warn;
        let fields = self.redactor.fields(raw.fields, allow_free);
        let at_ms = raw.at_ms.unwrap_or_else(now_ms);
        let id = random_id()?;
        let mut guard = self.lock()?;
        if raw.level <= Level::Debug && guard.mode == Mode::Normal {
            guard.stats.dropped_verbose = guard.stats.dropped_verbose.saturating_add(1);
            return Ok(None);
        }
        let bucket = format!("{}:{}", raw.domain.as_str(), raw.kind);
        let second = at_ms / 1000;
        let entry = guard.window.entry(bucket).or_insert((second, 0));
        if entry.0 != second {
            *entry = (second, 0);
        }
        entry.1 = entry.1.saturating_add(1);
        if entry.1 > PER_SECOND && raw.level < Level::Error {
            guard.stats.dropped_rate = guard.stats.dropped_rate.saturating_add(1);
            return Ok(None);
        }
        if guard.window.len() > 512 {
            guard.window.retain(|_, (s, _)| *s == second);
        }
        let seq = guard.store.next_seq();
        let env = Envelope {
            v: SCHEMA,
            seq,
            id,
            at_ms,
            domain: raw.domain,
            level: raw.level,
            kind: raw.kind,
            corr: raw.corr,
            src: raw.src,
            fields,
        };
        if let Err(e) = guard.store.append(&env) {
            guard.stats.rejected = guard.stats.rejected.saturating_add(1);
            return Err(e);
        }
        guard.stats.emitted = guard.stats.emitted.saturating_add(1);
        guard.since_flush = guard.since_flush.saturating_add(1);
        if guard.since_flush >= FLUSH_EVERY {
            guard.since_flush = 0;
            guard.store.flush_index()?;
        }
        if guard.ring.len() >= RING {
            guard.ring.pop_front();
        }
        guard.ring.push_back(env);
        Ok(Some(seq))
    }

    pub fn emit_json(&self, raw: &str) -> Result<Option<u64>, CollaudoError> {
        if raw.len() > 16 * 1024 {
            return Err(CollaudoError::Invalid("size"));
        }
        let parsed: RawEvent = serde_json::from_str(raw)?;
        self.emit(parsed)
    }

    pub fn query(&self, q: &Query) -> Result<Vec<Envelope>, CollaudoError> {
        let guard = self.lock()?;
        let from_ring = guard
            .ring
            .front()
            .is_some_and(|first| q.since_seq >= first.seq.saturating_sub(1))
            && q.from_ms.is_none()
            && q.to_ms.is_none();
        if from_ring {
            let limit = if q.limit == 0 { 500 } else { q.limit.min(5000) };
            let items = guard
                .ring
                .iter()
                .filter(|e| {
                    e.seq > q.since_seq
                        && q.domain.is_none_or(|d| e.domain == d)
                        && q.min_level.is_none_or(|l| e.level >= l)
                        && q.corr.as_ref().is_none_or(|c| e.corr.as_ref() == Some(c))
                        && q.kind_prefix
                            .as_ref()
                            .is_none_or(|p| e.kind.starts_with(p.as_str()))
                })
                .take(limit)
                .cloned()
                .collect();
            return Ok(items);
        }
        guard.store.query(q)
    }

    pub fn verify(&self) -> Result<Integrity, CollaudoError> {
        self.lock()?.store.verify()
    }

    pub fn flush(&self) -> Result<(), CollaudoError> {
        self.lock()?.store.flush_index()
    }
}
