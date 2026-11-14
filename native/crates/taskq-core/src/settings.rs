use serde::{Deserialize, Serialize};

use crate::error::{TaskqError, TaskqResult};
use crate::limits::Ceilings;
use crate::spec::Class;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ClassLimits {
    pub capacity: usize,
    pub concurrency: usize,
    pub threads: usize,
    pub ttl_ms: u64,
    pub max_retries: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Settings {
    pub voice: ClassLimits,
    pub interactive: ClassLimits,
    pub background: ClassLimits,
    pub maintenance: ClassLimits,
    pub backoff_base_ms: u64,
    pub backoff_cap_ms: u64,
    pub aging_ms: u64,
    pub retain_terminal: usize,
    pub event_log: usize,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            voice: ClassLimits {
                capacity: 64,
                concurrency: 2,
                threads: 1,
                ttl_ms: 5_000,
                max_retries: 0,
            },
            interactive: ClassLimits {
                capacity: 512,
                concurrency: 4,
                threads: 2,
                ttl_ms: 300_000,
                max_retries: 2,
            },
            background: ClassLimits {
                capacity: 4_096,
                concurrency: 4,
                threads: 2,
                ttl_ms: 86_400_000,
                max_retries: 4,
            },
            maintenance: ClassLimits {
                capacity: 1_024,
                concurrency: 1,
                threads: 1,
                ttl_ms: 86_400_000,
                max_retries: 4,
            },
            backoff_base_ms: 500,
            backoff_cap_ms: 60_000,
            aging_ms: 1_000,
            retain_terminal: 4_096,
            event_log: 8_192,
        }
    }
}

impl Settings {
    #[must_use]
    pub const fn limits(&self, class: Class) -> &ClassLimits {
        match class {
            Class::Voice => &self.voice,
            Class::Interactive => &self.interactive,
            Class::Background => &self.background,
            Class::Maintenance => &self.maintenance,
        }
    }

    pub fn validate(&self) -> TaskqResult<()> {
        let classes_ok = Class::ALL.iter().all(|c| {
            let l = self.limits(*c);
            (1..=Ceilings::QUEUE).contains(&l.capacity)
                && (1..=l.capacity).contains(&l.concurrency)
                && (1..=Ceilings::THREADS).contains(&l.threads)
                && (1..=Ceilings::TIME_MS).contains(&l.ttl_ms)
                && l.max_retries <= Ceilings::RETRIES
        });
        let rest_ok = (1..=self.backoff_cap_ms).contains(&self.backoff_base_ms)
            && self.backoff_cap_ms <= Ceilings::TIME_MS
            && (1..=Ceilings::TIME_MS).contains(&self.aging_ms)
            && (1..=Ceilings::RETAIN).contains(&self.retain_terminal)
            && (1..=Ceilings::EVENT_LOG).contains(&self.event_log);
        if classes_ok && rest_ok {
            Ok(())
        } else {
            Err(TaskqError::Settings)
        }
    }

    pub fn from_json(text: &str) -> TaskqResult<Self> {
        if text.len() > Ceilings::PAYLOAD_BYTES {
            return Err(TaskqError::TooLarge);
        }
        let settings: Self = serde_json::from_str(text).map_err(|_| TaskqError::Settings)?;
        settings.validate()?;
        Ok(settings)
    }
}
