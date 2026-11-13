use std::collections::BTreeMap;

use crate::speaker::{dot, unit};

pub const MAX_FOREIGN: usize = 8;
pub const MAX_SESSIONS: usize = 16;
const MAX_WINDOWS: usize = 16;
const MAX_PROBE: usize = 1024;
const FOREIGN_JOIN: f32 = 0.6;
const FOREIGN_BLEND: f32 = 0.2;
const FOREIGN_BLOCK: f32 = 0.7;
const FOREIGN_FORGET_S: f64 = 1_800.0;
const SESSION_S: f64 = 20.0;
const SESSION_FLOOR: f32 = 0.5;
const SESSION_BLEND: f32 = 0.25;
const SCORE_CAP: f32 = 0.97;
const FOREIGN_RECURRING: u32 = 3;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct AttributionPolicy {
    pub min_seconds: f32,
    pub strict_bonus: f32,
    pub programme_bonus: f32,
    pub foreign_margin: f32,
    pub window_gap: f32,
    pub clear_gap: f32,
}

impl Default for AttributionPolicy {
    fn default() -> Self {
        Self {
            min_seconds: 1.2,
            strict_bonus: 0.05,
            programme_bonus: 0.08,
            foreign_margin: 0.1,
            window_gap: 0.04,
            clear_gap: 0.08,
        }
    }
}

impl AttributionPolicy {
    #[must_use]
    pub fn sanitized(self) -> Self {
        let pick =
            |v: f32, lo: f32, hi: f32, d: f32| if v.is_finite() { v.clamp(lo, hi) } else { d };
        Self {
            min_seconds: pick(self.min_seconds, 0.5, 10.0, 1.2),
            strict_bonus: pick(self.strict_bonus, 0.0, 0.3, 0.05),
            programme_bonus: pick(self.programme_bonus, 0.0, 0.3, 0.08),
            foreign_margin: pick(self.foreign_margin, 0.0, 0.5, 0.1),
            window_gap: pick(self.window_gap, 0.0, 0.3, 0.04),
            clear_gap: pick(self.clear_gap, 0.0, 0.4, 0.08),
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct WindowVerdict {
    pub slug: Option<String>,
    pub score: f32,
}

#[derive(Debug, Clone)]
pub struct Evidence<'a> {
    pub probe: &'a [f32],
    pub slug: Option<&'a str>,
    pub score: f32,
    pub limit: f32,
    pub seconds: f32,
    pub programme: bool,
    pub windows: &'a [WindowVerdict],
    pub now: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Attribution {
    pub slug: Option<String>,
    pub verified: bool,
    pub foreign: bool,
    pub score: f32,
    pub needed: f32,
    pub reason: &'static str,
}

#[derive(Debug, Clone)]
struct Foreign {
    centre: Vec<f32>,
    last_seen: f64,
    turns: u32,
}

#[derive(Debug, Clone)]
struct Session {
    centre: Vec<f32>,
    last_seen: f64,
}

#[derive(Debug, Clone, Default)]
pub struct Attributor {
    policy: AttributionPolicy,
    foreign: Vec<Foreign>,
    sessions: BTreeMap<String, Session>,
}

impl Attributor {
    #[must_use]
    pub fn new(policy: AttributionPolicy) -> Self {
        Self {
            policy: policy.sanitized(),
            ..Self::default()
        }
    }

    #[must_use]
    pub fn policy(&self) -> AttributionPolicy {
        self.policy
    }

    pub fn set_policy(&mut self, policy: AttributionPolicy) {
        self.policy = policy.sanitized();
    }

    pub fn clear(&mut self) {
        self.foreign.clear();
        self.sessions.clear();
    }

    #[must_use]
    pub fn foreign_count(&self) -> usize {
        self.foreign.len()
    }

    #[must_use]
    pub fn foreign_recent(&self, now: f64, within: f64) -> usize {
        self.foreign
            .iter()
            .filter(|f| f.turns >= FOREIGN_RECURRING && now - f.last_seen <= within)
            .count()
    }

    fn reject(score: f32, needed: f32, reason: &'static str, foreign: bool) -> Attribution {
        Attribution {
            slug: None,
            verified: false,
            foreign,
            score,
            needed,
            reason,
        }
    }

    fn forget(&mut self, now: f64) {
        self.foreign
            .retain(|f| now - f.last_seen <= FOREIGN_FORGET_S);
        self.sessions.retain(|_, s| now - s.last_seen <= SESSION_S);
    }

    fn note_foreign(&mut self, probe: &[f32], now: f64) {
        let found = self
            .foreign
            .iter()
            .enumerate()
            .filter(|(_, f)| f.centre.len() == probe.len())
            .map(|(i, f)| (i, dot(&f.centre, probe)))
            .filter(|(_, s)| *s >= FOREIGN_JOIN)
            .max_by(|a, b| a.1.total_cmp(&b.1));
        if let Some((index, _)) = found {
            if let Some(entry) = self.foreign.get_mut(index) {
                let blended: Vec<f32> = entry
                    .centre
                    .iter()
                    .zip(probe)
                    .map(|(c, p)| (1.0 - FOREIGN_BLEND) * c + FOREIGN_BLEND * p)
                    .collect();
                entry.centre = unit(&blended);
                entry.last_seen = now;
                entry.turns = entry.turns.saturating_add(1);
            }
            return;
        }
        self.foreign.push(Foreign {
            centre: probe.to_vec(),
            last_seen: now,
            turns: 1,
        });
        if self.foreign.len() > MAX_FOREIGN {
            self.foreign
                .sort_by(|a, b| b.last_seen.total_cmp(&a.last_seen));
            self.foreign.truncate(MAX_FOREIGN);
        }
    }

    fn foreign_best(&self, probe: &[f32]) -> f32 {
        self.foreign
            .iter()
            .filter(|f| f.centre.len() == probe.len() && f.turns >= 2)
            .map(|f| dot(&f.centre, probe))
            .fold(0.0_f32, f32::max)
    }

    fn windows_agree(&self, slug: &str, limit: f32, windows: &[WindowVerdict]) -> bool {
        let floor = limit - self.policy.window_gap;
        windows
            .iter()
            .all(|w| w.slug.as_deref() == Some(slug) && w.score >= floor)
    }

    pub fn judge(&mut self, ev: &Evidence<'_>) -> Attribution {
        let invalid = ev.probe.is_empty()
            || ev.probe.len() > MAX_PROBE
            || ev.probe.iter().any(|v| !v.is_finite())
            || !ev.score.is_finite()
            || !ev.limit.is_finite()
            || !ev.seconds.is_finite()
            || !ev.now.is_finite()
            || ev.windows.len() > MAX_WINDOWS;
        if invalid {
            return Self::reject(0.0, 0.0, "dati non validi", false);
        }
        self.forget(ev.now);
        let probe = unit(ev.probe);
        if ev.seconds < self.policy.min_seconds {
            return Self::reject(ev.score, 0.0, "troppo breve", false);
        }
        let Some(slug) = ev.slug else {
            if ev.score < ev.limit - self.policy.clear_gap || ev.score <= 0.0 {
                self.note_foreign(&probe, ev.now);
            }
            return Self::reject(ev.score, ev.limit, "voce non registrata", false);
        };
        let bonus = self.policy.strict_bonus
            + if ev.programme {
                self.policy.programme_bonus
            } else {
                0.0
            };
        let needed = (ev.limit + bonus).min(SCORE_CAP);
        if ev.score < needed {
            return Self::reject(ev.score, needed, "prova insufficiente", false);
        }
        if !self.windows_agree(slug, ev.limit, ev.windows) {
            return Self::reject(ev.score, needed, "voci miste o incerte", false);
        }
        let other = self.foreign_best(&probe);
        if other >= FOREIGN_BLOCK && other + self.policy.foreign_margin > ev.score {
            return Self::reject(ev.score, needed, "somiglia a una voce estranea", true);
        }
        if let Some(session) = self.sessions.get(slug) {
            if session.centre.len() == probe.len() && dot(&session.centre, &probe) < SESSION_FLOOR {
                self.sessions.remove(slug);
                return Self::reject(ev.score, needed, "cambio di voce nella sessione", false);
            }
        }
        self.remember(slug, &probe, ev.now);
        Attribution {
            slug: Some(slug.to_owned()),
            verified: true,
            foreign: false,
            score: ev.score,
            needed,
            reason: "ok",
        }
    }

    fn remember(&mut self, slug: &str, probe: &[f32], now: f64) {
        if !self.sessions.contains_key(slug) && self.sessions.len() >= MAX_SESSIONS {
            return;
        }
        let centre = match self.sessions.get(slug) {
            Some(s) if s.centre.len() == probe.len() => unit(
                &s.centre
                    .iter()
                    .zip(probe)
                    .map(|(c, p)| (1.0 - SESSION_BLEND) * c + SESSION_BLEND * p)
                    .collect::<Vec<_>>(),
            ),
            _ => probe.to_vec(),
        };
        self.sessions.insert(
            slug.to_owned(),
            Session {
                centre,
                last_seen: now,
            },
        );
    }
}
