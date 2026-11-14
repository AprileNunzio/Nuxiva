use std::collections::{HashMap, VecDeque};

use nuxiva_taskq_core::CancelToken;
use serde::Serialize;

use crate::error::{DuplexError, DuplexResult};
use crate::settings::Settings;
use crate::state::{State, Trigger};

const MILLI: u64 = 1_000;
const SEQ_WINDOW: u32 = 8;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum EventKind {
    Transition,
    Timeout,
    Cut,
    Stale,
    RateLimited,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Event {
    pub at_ms: u64,
    pub kind: EventKind,
    #[serde(rename = "gen")]
    pub epoch: u32,
    pub state: State,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Interruption {
    #[serde(rename = "gen")]
    pub epoch: u32,
    pub spoken_chars: u32,
    pub at_ms: u64,
    pub fade_ms: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct CutReport {
    #[serde(rename = "gen")]
    pub epoch: u32,
    pub cancelled: usize,
    pub state: State,
    pub interruption: Option<Interruption>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Snapshot {
    pub state: State,
    #[serde(rename = "gen")]
    pub epoch: u32,
    pub cut_upto: u32,
    pub bound_tokens: usize,
    pub spoken_chars: u32,
}

#[derive(Debug)]
pub struct Session {
    settings: Settings,
    state: State,
    entered_ms: u64,
    epoch: u32,
    cut_upto: u32,
    out_seq: u32,
    spoken: u32,
    last_seq: HashMap<u32, u32>,
    tokens: Vec<(u32, CancelToken)>,
    interruption: Option<Interruption>,
    events: VecDeque<Event>,
    bucket: u64,
    refilled_ms: u64,
}

impl Session {
    pub fn new(settings: Settings, now_ms: u64) -> DuplexResult<Self> {
        settings.validate()?;
        let bucket = u64::from(settings.rate_burst).saturating_mul(MILLI);
        Ok(Self {
            settings,
            state: State::Idle,
            entered_ms: now_ms,
            epoch: 0,
            cut_upto: 0,
            out_seq: 0,
            spoken: 0,
            last_seq: HashMap::new(),
            tokens: Vec::new(),
            interruption: None,
            events: VecDeque::new(),
            bucket,
            refilled_ms: now_ms,
        })
    }

    #[must_use]
    pub const fn state(&self) -> State {
        self.state
    }

    #[must_use]
    pub const fn epoch(&self) -> u32 {
        self.epoch
    }

    #[must_use]
    pub const fn is_live(&self, epoch: u32) -> bool {
        epoch > self.cut_upto
    }

    #[must_use]
    pub fn snapshot(&self) -> Snapshot {
        Snapshot {
            state: self.state,
            epoch: self.epoch,
            cut_upto: self.cut_upto,
            bound_tokens: self.tokens.len(),
            spoken_chars: self.spoken,
        }
    }

    #[must_use]
    pub const fn interruption(&self) -> Option<&Interruption> {
        self.interruption.as_ref()
    }

    pub fn drain_events(&mut self) -> Vec<Event> {
        self.events.drain(..).collect()
    }

    fn record(&mut self, at_ms: u64, kind: EventKind, epoch: u32) {
        if self.events.len() >= self.settings.event_cap {
            self.events.pop_front();
        }
        self.events.push_back(Event {
            at_ms,
            kind,
            epoch,
            state: self.state,
        });
    }

    fn enter(&mut self, next: State, now_ms: u64, kind: EventKind) {
        self.state = next;
        self.entered_ms = now_ms;
        self.record(now_ms, kind, self.epoch);
    }

    pub fn trigger(&mut self, trigger: Trigger, now_ms: u64) -> DuplexResult<State> {
        if trigger == Trigger::Interrupt {
            if self.state != State::Speaking {
                return Err(DuplexError::Transition);
            }
            return self.cut(0, now_ms).map(|report| report.state);
        }
        let next = self.state.next(trigger).ok_or(DuplexError::Transition)?;
        if trigger == Trigger::Reset {
            self.release_all();
        }
        self.enter(next, now_ms, EventKind::Transition);
        Ok(next)
    }

    pub fn begin_reply(&mut self, now_ms: u64) -> DuplexResult<u32> {
        let next = self
            .state
            .next(Trigger::ReplyStart)
            .ok_or(DuplexError::Transition)?;
        let epoch = self.epoch.checked_add(1).ok_or(DuplexError::Capacity)?;
        self.epoch = epoch;
        self.out_seq = 0;
        self.spoken = 0;
        self.interruption = None;
        self.enter(next, now_ms, EventKind::Transition);
        Ok(epoch)
    }

    pub fn next_out_seq(&mut self, epoch: u32) -> DuplexResult<u32> {
        if epoch != self.epoch || !self.is_live(epoch) {
            return Err(DuplexError::Stale);
        }
        self.out_seq = self.out_seq.checked_add(1).ok_or(DuplexError::Capacity)?;
        Ok(self.out_seq)
    }

    pub fn bind(&mut self, epoch: u32, token: CancelToken) -> DuplexResult<()> {
        if !self.is_live(epoch) || epoch > self.epoch {
            token.cancel();
            return Err(DuplexError::Stale);
        }
        if self.tokens.len() >= self.settings.max_cancel_tokens {
            return Err(DuplexError::Capacity);
        }
        self.tokens.push((epoch, token));
        Ok(())
    }

    pub fn mark_spoken(&mut self, epoch: u32, chars: u32) -> DuplexResult<()> {
        if epoch != self.epoch || !self.is_live(epoch) {
            return Err(DuplexError::Stale);
        }
        self.spoken = self.spoken.saturating_add(chars);
        Ok(())
    }

    fn refill(&mut self, now_ms: u64) {
        let elapsed = now_ms.saturating_sub(self.refilled_ms);
        self.refilled_ms = self.refilled_ms.max(now_ms);
        let add = elapsed.saturating_mul(u64::from(self.settings.rate_per_second));
        let cap = u64::from(self.settings.rate_burst).saturating_mul(MILLI);
        self.bucket = self.bucket.saturating_add(add).min(cap);
    }

    pub fn admit(&mut self, epoch: u32, seq: u32, now_ms: u64) -> DuplexResult<()> {
        self.refill(now_ms);
        if self.bucket < MILLI {
            self.record(now_ms, EventKind::RateLimited, epoch);
            return Err(DuplexError::RateLimited);
        }
        self.bucket = self.bucket.saturating_sub(MILLI);
        if epoch != 0 && !self.is_live(epoch) {
            self.record(now_ms, EventKind::Stale, epoch);
            return Err(DuplexError::Stale);
        }
        if let Some(last) = self.last_seq.get(&epoch)
            && seq <= *last
        {
            return Err(DuplexError::Sequence);
        }
        let floor = self.epoch.saturating_sub(SEQ_WINDOW);
        self.last_seq.retain(|g, _| *g == 0 || *g >= floor);
        self.last_seq.insert(epoch, seq);
        Ok(())
    }

    fn release_all(&mut self) {
        for (_, token) in self.tokens.drain(..) {
            token.cancel();
        }
        self.cut_upto = self.epoch;
    }

    pub fn cut(&mut self, epoch: u32, now_ms: u64) -> DuplexResult<CutReport> {
        let target = if epoch == 0 { self.epoch } else { epoch };
        if target > self.epoch {
            return Err(DuplexError::Invalid);
        }
        self.cut_upto = self.cut_upto.max(target);
        let before = self.tokens.len();
        let cut_upto = self.cut_upto;
        self.tokens.retain(|(g, token)| {
            if *g <= cut_upto {
                token.cancel();
                false
            } else {
                true
            }
        });
        let cancelled = before.saturating_sub(self.tokens.len());
        let mut interruption = None;
        if self.state == State::Speaking && target == self.epoch {
            let next = State::Interrupted;
            let note = Interruption {
                epoch: target,
                spoken_chars: self.spoken,
                at_ms: now_ms,
                fade_ms: self.settings.fade_ms,
            };
            self.interruption = Some(note.clone());
            interruption = Some(note);
            self.enter(next, now_ms, EventKind::Cut);
        } else {
            self.record(now_ms, EventKind::Cut, target);
        }
        Ok(CutReport {
            epoch: target,
            cancelled,
            state: self.state,
            interruption,
        })
    }

    pub fn finish_reply(&mut self, epoch: u32, now_ms: u64) -> DuplexResult<State> {
        if epoch != self.epoch || !self.is_live(epoch) {
            return Err(DuplexError::Stale);
        }
        self.tokens.retain(|(g, _)| *g != epoch);
        self.trigger(Trigger::ReplyEnd, now_ms)
    }

    pub fn tick(&mut self, now_ms: u64) -> Option<State> {
        let limit = self.settings.limit_ms(self.state)?;
        if now_ms.saturating_sub(self.entered_ms) < limit {
            return None;
        }
        let next = self.state.on_timeout()?;
        if self.state == State::Speaking || self.state == State::Thinking {
            self.release_all();
        }
        self.enter(next, now_ms, EventKind::Timeout);
        Some(next)
    }
}
