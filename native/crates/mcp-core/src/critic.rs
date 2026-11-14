use std::collections::{HashMap, VecDeque};
use std::time::{Duration, Instant};

use serde::Serialize;

use crate::limits::Ceilings;
use crate::payload::ErrorPayload;
use crate::settings::Settings;

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(tag = "action", content = "server", rename_all = "snake_case")]
pub enum Remedy {
    RestartServer(String),
    QuarantineServer(String),
    RestartTask(String),
    RetryWithBackoff(String),
    EscalateToUser(String),
}

#[derive(Debug)]
pub struct Critic {
    threshold: usize,
    window: Duration,
    seen: HashMap<(String, String), VecDeque<Instant>>,
}

const BAD_OUTPUT: [&str; 2] = ["mcp.output.invalid", "mcp.tool.invalid"];
const UNRESPONSIVE: [&str; 2] = ["mcp.timeout", "mcp.closed"];

fn queue_of(component: &str) -> Option<&str> {
    component.strip_prefix("queue:").filter(|id| !id.is_empty())
}

fn server_of(component: &str) -> Option<&str> {
    component
        .split_once(':')
        .filter(|(kind, _)| matches!(*kind, "task" | "call" | "server"))
        .map(|(_, id)| id)
        .filter(|id| !id.is_empty())
}

impl Critic {
    #[must_use]
    pub fn new(settings: &Settings) -> Self {
        Self {
            threshold: settings.critic_threshold,
            window: Duration::from_millis(
                u64::try_from(settings.critic_window_ms).unwrap_or(u64::MAX),
            ),
            seen: HashMap::new(),
        }
    }

    fn count(&mut self, server: &str, code: &str, now: Instant) -> usize {
        if self.seen.len() >= Ceilings::CRITIC_KEYS {
            self.seen.clear();
        }
        let times = self
            .seen
            .entry((server.to_owned(), code.to_owned()))
            .or_default();
        times.push_back(now);
        while times
            .front()
            .is_some_and(|t| now.saturating_duration_since(*t) > self.window)
        {
            times.pop_front();
        }
        times.len()
    }

    fn forget(&mut self, server: &str) {
        self.seen.retain(|(s, _), _| s != server);
    }

    fn advise_task(&mut self, task: &str, code: &str, now: Instant) -> Option<Remedy> {
        let count = self.count(task, code, now);
        let remedy = match code {
            "queue.crashed" => Some(Remedy::RestartTask(task.to_owned())),
            "queue.transient" if count >= self.threshold => {
                Some(Remedy::EscalateToUser(task.to_owned()))
            }
            "queue.transient" => Some(Remedy::RetryWithBackoff(task.to_owned())),
            "queue.fatal" | "queue.policy" => Some(Remedy::EscalateToUser(task.to_owned())),
            _ => None,
        };
        if matches!(remedy, Some(Remedy::EscalateToUser(_))) {
            self.forget(task);
        }
        remedy
    }

    pub fn advise(&mut self, payload: &ErrorPayload, now: Instant) -> Option<Remedy> {
        if let Some(task) = queue_of(&payload.component) {
            let task = task.to_owned();
            return self.advise_task(&task, payload.code.as_str(), now);
        }
        let server = server_of(&payload.component)?.to_owned();
        let code = payload.code.as_str();
        let count = self.count(&server, code, now);
        let remedy = if code == "panic" {
            Some(Remedy::RestartServer(server.clone()))
        } else if BAD_OUTPUT.contains(&code) && count >= self.threshold {
            Some(Remedy::QuarantineServer(server.clone()))
        } else if UNRESPONSIVE.contains(&code)
            && payload.component.starts_with("call:")
            && count >= self.threshold
        {
            Some(Remedy::RestartServer(server.clone()))
        } else {
            None
        };
        if remedy.is_some() {
            self.forget(&server);
        }
        remedy
    }
}
