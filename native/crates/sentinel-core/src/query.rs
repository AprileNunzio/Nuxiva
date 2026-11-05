use serde::{Deserialize, Serialize};

use crate::error::SentinelError;
use crate::event::Event;
use crate::kind::Group;

pub const MAX_LIMIT: usize = 200;
pub const MAX_SPAN_MS: u64 = 31 * 86_400_000;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Query {
    pub from_ms: u64,
    pub to_ms: u64,
    #[serde(default)]
    pub groups: Vec<Group>,
    #[serde(default)]
    pub subject: Option<String>,
    #[serde(default = "default_limit")]
    pub limit: usize,
    #[serde(default)]
    pub before: Option<(u64, String)>,
}

const fn default_limit() -> usize {
    50
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Page {
    pub events: Vec<Event>,
    pub next: Option<(u64, String)>,
}

impl Query {
    pub fn validate(&self) -> Result<(), SentinelError> {
        if self.to_ms < self.from_ms {
            return Err(SentinelError::InvalidQuery("range"));
        }
        if self.to_ms.saturating_sub(self.from_ms) > MAX_SPAN_MS {
            return Err(SentinelError::InvalidQuery("span"));
        }
        if self.limit == 0 || self.limit > MAX_LIMIT {
            return Err(SentinelError::InvalidQuery("limit"));
        }
        if self.subject.as_ref().is_some_and(|s| s.len() > 128) || self.groups.len() > 12 {
            return Err(SentinelError::InvalidQuery("filter"));
        }
        Ok(())
    }

    fn matches(&self, e: &Event) -> bool {
        (self.from_ms..=self.to_ms).contains(&e.at_ms)
            && (self.groups.is_empty() || self.groups.contains(&e.kind.group()))
            && self.subject.as_ref().is_none_or(|s| *s == e.subject.key())
            && self
                .before
                .as_ref()
                .is_none_or(|(at, id)| (e.at_ms, &e.id) < (*at, id))
    }

    pub fn run(&self, events: impl IntoIterator<Item = Event>) -> Result<Page, SentinelError> {
        self.validate()?;
        let mut hits: Vec<Event> = events.into_iter().filter(|e| self.matches(e)).collect();
        hits.sort_by(|a, b| (b.at_ms, &b.id).cmp(&(a.at_ms, &a.id)));
        let more = hits.len() > self.limit;
        hits.truncate(self.limit);
        let next = if more {
            hits.last().map(|e| (e.at_ms, e.id.clone()))
        } else {
            None
        };
        Ok(Page { events: hits, next })
    }
}
