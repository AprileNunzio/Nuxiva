use std::time::{SystemTime, UNIX_EPOCH};

use nuxiva_display_scheduler::{Policy, Scheduler};
use serde_json::{Value, json};

use crate::error::DisplayError;
use crate::protocol::{MAX_PLAN, Request};

pub trait Clock: Send {
    fn now_ms(&self) -> u64;
}

#[derive(Debug, Default, Clone, Copy)]
pub struct SystemClock;

impl Clock for SystemClock {
    fn now_ms(&self) -> u64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_or(0, |d| u64::try_from(d.as_millis()).unwrap_or(u64::MAX))
    }
}

#[derive(Debug)]
pub struct Engine<C: Clock> {
    scheduler: Scheduler,
    clock: C,
}

impl<C: Clock> Engine<C> {
    pub fn new(policy: Policy, clock: C) -> Self {
        Self {
            scheduler: Scheduler::new(policy),
            clock,
        }
    }

    pub fn handle(&mut self, request: Request) -> Result<Value, DisplayError> {
        let now = self.clock.now_ms();
        let s = &mut self.scheduler;
        let value = match request {
            Request::Ping {} => json!({"pong": true, "version": env!("CARGO_PKG_VERSION")}),
            Request::Admit { screen, widgets } => {
                if widgets.len() > MAX_PLAN {
                    return Err(DisplayError::BadRequest("plan too large".to_owned()));
                }
                json!({"transitions": s.admit(screen, &widgets, now)?})
            }
            Request::Visibility { instance, visible } => {
                json!({"transitions": s.visibility(&instance, visible, now)?})
            }
            Request::Observe { instance, cost_mb } => {
                s.observe(&instance, cost_mb)?;
                json!({})
            }
            Request::Error { instance } => json!({"transitions": s.error(&instance, now)?}),
            Request::Pressure { screen, budget_mb } => {
                json!({"transitions": s.pressure(screen, budget_mb, now)})
            }
            Request::Audience {
                screen,
                nucleus_only,
            } => json!({"transitions": s.audience(screen, nucleus_only, now)}),
            Request::Tick {} => {
                let (due, transitions) = s.tick(now);
                json!({"due": due, "transitions": transitions})
            }
            Request::Status { screen } => {
                json!({"cost_mb": s.screen_cost(screen), "quarantined": s.quarantined(now)})
            }
            Request::Diff { old, new } => match nuxiva_display_stream::diff(&old, &new) {
                Some(ops) => json!({"ops": ops}),
                None => json!({"ops": Value::Null}),
            },
        };
        Ok(value)
    }
}
