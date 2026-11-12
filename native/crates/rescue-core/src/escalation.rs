use std::collections::BTreeSet;

use crate::action::{Action, Entry, Stage, Step, Tone};
use crate::fusion::{Assessment, assess};
use crate::policy::Policy;
use crate::signal::{Evidence, EvidenceError, Hazard, Kind, MAX_EVIDENCE};

pub const MAX_TIMELINE: usize = 128;
pub const PERSON: &str = "person";
pub const HYSTERESIS: f64 = 0.8;

#[derive(Debug, Clone)]
pub struct Engine {
    policy: Policy,
    evidence: Vec<Evidence>,
    stage: Stage,
    hazard: Option<Hazard>,
    raised: BTreeSet<Hazard>,
    deadline: f64,
    tiers: u8,
    round: u8,
    explicit: bool,
    cooled: Option<Hazard>,
    cooldown_until: f64,
    incident: u64,
    timeline: Vec<Entry>,
}

const fn tone_of(hazard: Hazard) -> Tone {
    match hazard {
        Hazard::Medical | Hazard::Fire => Tone::Spoken,
        Hazard::Intrusion | Hazard::Violence => Tone::Discreet,
    }
}

const PRIORITY: [Hazard; 4] = [
    Hazard::Fire,
    Hazard::Violence,
    Hazard::Intrusion,
    Hazard::Medical,
];

impl Engine {
    #[must_use]
    pub fn new(policy: Policy) -> Self {
        Self {
            policy,
            evidence: Vec::new(),
            stage: Stage::Calm,
            hazard: None,
            raised: BTreeSet::new(),
            deadline: 0.0,
            tiers: 0,
            round: 0,
            explicit: false,
            cooled: None,
            cooldown_until: 0.0,
            incident: 0,
            timeline: Vec::new(),
        }
    }

    #[must_use]
    pub const fn policy(&self) -> &Policy {
        &self.policy
    }

    #[must_use]
    pub const fn stage(&self) -> Stage {
        self.stage
    }

    #[must_use]
    pub fn timeline(&self) -> &[Entry] {
        &self.timeline
    }

    #[must_use]
    pub fn evidence_count(&self) -> usize {
        self.evidence.len()
    }

    pub fn observe(&mut self, evidence: Evidence, now: f64) -> Result<(), EvidenceError> {
        evidence.validate(now)?;
        self.evidence.push(evidence);
        self.prune(now);
        Ok(())
    }

    fn prune(&mut self, now: f64) {
        self.evidence.retain(|e| !e.expired(now));
        let excess = self.evidence.len().saturating_sub(MAX_EVIDENCE);
        if excess > 0 {
            self.evidence.sort_by(|a, b| a.at.total_cmp(&b.at));
            self.evidence.drain(..excess);
        }
    }

    fn record(&mut self, at: f64, action: Option<Action>) {
        if self.timeline.len() >= MAX_TIMELINE {
            self.timeline.remove(0);
        }
        self.timeline.push(Entry {
            at,
            stage: self.stage,
            action,
        });
    }

    fn emit(&mut self, out: &mut Vec<Action>, at: f64, action: Action) {
        self.record(at, Some(action.clone()));
        out.push(action);
    }

    fn open(&mut self, hazard: Hazard) {
        if !self.stage.active() {
            self.incident = self.incident.saturating_add(1);
            self.timeline.clear();
            self.raised.clear();
            self.tiers = 0;
            self.round = 0;
            self.explicit = false;
        }
        self.hazard = Some(hazard);
    }

    fn check_in(&mut self, hazard: Hazard, wait: f64, now: f64, out: &mut Vec<Action>) {
        self.open(hazard);
        self.stage = Stage::CheckIn;
        self.deadline = now + wait;
        self.emit(
            out,
            now,
            Action::AskPerson {
                hazard,
                tone: tone_of(hazard),
            },
        );
    }

    fn raise(&mut self, hazard: Hazard, now: f64, out: &mut Vec<Action>) {
        self.open(hazard);
        self.raised.insert(hazard);
        if hazard == Hazard::Fire {
            self.emit(out, now, Action::HomeAlarm { hazard });
        }
        if hazard == Hazard::Medical && self.stage != Stage::CheckIn {
            self.emit(
                out,
                now,
                Action::AskPerson {
                    hazard,
                    tone: Tone::Spoken,
                },
            );
        }
        if matches!(
            self.stage,
            Stage::Alerting | Stage::Acknowledged | Stage::Emergency
        ) {
            self.emit(
                out,
                now,
                Action::AlertFamily {
                    hazard,
                    tier: 0,
                    tone: tone_of(hazard),
                },
            );
        } else {
            self.stage = Stage::Alerting;
            self.tiers = 1;
            self.deadline = now + self.policy.family_ack_s;
            self.emit(
                out,
                now,
                Action::AlertFamily {
                    hazard,
                    tier: 0,
                    tone: tone_of(hazard),
                },
            );
        }
        self.emit(out, now, Action::RemindEmergencyNumber { hazard });
    }

    fn urgent(&self, hazard: Hazard, risk: f64) -> bool {
        match hazard {
            Hazard::Fire => risk >= self.policy.check_at(),
            Hazard::Intrusion | Hazard::Violence => risk >= self.policy.alert_at(),
            Hazard::Medical => risk >= self.policy.critical_at(),
        }
    }

    fn cooling(&self, hazard: Hazard, now: f64) -> bool {
        self.cooled == Some(hazard) && now < self.cooldown_until
    }

    fn start(&mut self, a: &Assessment, now: f64, out: &mut Vec<Action>) {
        for hazard in PRIORITY {
            let risk = a.risk(hazard);
            if self.urgent(hazard, risk) {
                self.raise(hazard, now, out);
                return;
            }
            if self.cooling(hazard, now) {
                continue;
            }
            if hazard == Hazard::Medical && risk >= self.policy.alert_at() {
                self.check_in(hazard, self.policy.alert_grace_s, now, out);
                return;
            }
            if hazard != Hazard::Fire && risk >= self.policy.check_at() {
                self.check_in(hazard, self.policy.check_in_s, now, out);
                return;
            }
        }
        let peak = a.top().map_or(0.0, |h| h.risk);
        if peak >= self.policy.watch_at() {
            if self.stage != Stage::Watching {
                self.stage = Stage::Watching;
                self.record(now, None);
            }
        } else if self.stage == Stage::Watching && peak < self.policy.watch_at() * HYSTERESIS {
            self.stage = Stage::Calm;
            self.record(now, None);
        } else if self.stage == Stage::Cooldown && now >= self.cooldown_until {
            self.stage = Stage::Calm;
            self.cooled = None;
        }
    }

    fn others(&mut self, a: &Assessment, now: f64, out: &mut Vec<Action>) {
        for hazard in PRIORITY {
            if Some(hazard) != self.hazard
                && !self.raised.contains(&hazard)
                && self.urgent(hazard, a.risk(hazard))
            {
                let current = self.hazard;
                self.raise(hazard, now, out);
                if hazard != Hazard::Fire {
                    self.hazard = current.or(Some(hazard));
                }
            }
        }
    }

    fn timeouts(&mut self, a: &Assessment, now: f64, out: &mut Vec<Action>) {
        let Some(hazard) = self.hazard else { return };
        match self.stage {
            Stage::CheckIn => {
                let risk = a.risk(hazard);
                if self.urgent(hazard, risk) {
                    self.raise(hazard, now, out);
                } else if now >= self.deadline {
                    if risk < self.policy.watch_at() && !self.explicit {
                        self.stand_down(now, out);
                    } else {
                        self.raise(hazard, now, out);
                    }
                }
            }
            Stage::Alerting if now >= self.deadline => {
                if self.tiers < self.policy.family_tiers {
                    let tier = self.tiers;
                    self.tiers = self.tiers.saturating_add(1);
                    self.deadline = now + self.policy.family_ack_s;
                    self.emit(
                        out,
                        now,
                        Action::AlertFamily {
                            hazard,
                            tier,
                            tone: tone_of(hazard),
                        },
                    );
                } else {
                    self.stage = Stage::Emergency;
                    self.round = 1;
                    self.deadline = now + self.policy.emergency_repeat_s;
                    self.emit(
                        out,
                        now,
                        Action::AlertEmergencyContacts { hazard, round: 1 },
                    );
                    self.emit(out, now, Action::RemindEmergencyNumber { hazard });
                }
            }
            Stage::Emergency
                if now >= self.deadline && self.round < self.policy.emergency_rounds =>
            {
                self.round = self.round.saturating_add(1);
                self.deadline = now + self.policy.emergency_repeat_s;
                let round = self.round;
                self.emit(out, now, Action::AlertEmergencyContacts { hazard, round });
            }
            _ => {}
        }
    }

    fn stand_down(&mut self, now: f64, out: &mut Vec<Action>) {
        let Some(hazard) = self.hazard else { return };
        let notified_tiers = self.tiers;
        let emergency = self.round > 0;
        self.stage = Stage::Cooldown;
        self.cooled = Some(hazard);
        self.cooldown_until = now + self.policy.cooldown_s;
        self.emit(
            out,
            now,
            Action::StandDown {
                hazard,
                notified_tiers,
                emergency,
            },
        );
        self.hazard = None;
        self.raised.clear();
        self.tiers = 0;
        self.round = 0;
        self.explicit = false;
    }

    fn step(&self, now: f64, actions: Vec<Action>, assessment: Assessment) -> Step {
        Step {
            at: now,
            stage: self.stage,
            hazard: self.hazard,
            incident: self.incident,
            deadline: matches!(
                self.stage,
                Stage::CheckIn | Stage::Alerting | Stage::Emergency
            )
            .then_some(self.deadline),
            actions,
            assessment,
        }
    }

    pub fn update(&mut self, now: f64) -> Step {
        self.prune(now);
        let a = assess(&self.evidence, &self.policy, now);
        let mut out = Vec::new();
        if self.stage.active() {
            self.others(&a, now, &mut out);
            self.timeouts(&a, now, &mut out);
        } else {
            self.start(&a, now, &mut out);
        }
        self.step(now, out, a)
    }

    pub fn person_ok(&mut self, now: f64) -> Step {
        self.evidence
            .retain(|e| !matches!(e.kind.hazards(), [Hazard::Medical, ..]) || e.at > now);
        self.evidence.push(Evidence {
            kind: Kind::AllClear,
            probability: 0.95,
            confidence: 1.0,
            source: PERSON.to_owned(),
            room: None,
            at: now,
        });
        let mut out = Vec::new();
        if self.stage.active() && matches!(self.hazard, Some(Hazard::Medical | Hazard::Violence)) {
            self.stand_down(now, &mut out);
        }
        let a = assess(&self.evidence, &self.policy, now);
        self.step(now, out, a)
    }

    pub fn need_help(&mut self, now: f64) -> Step {
        let mut out = Vec::new();
        let hazard = self.hazard.unwrap_or(Hazard::Medical);
        match self.stage {
            Stage::Alerting => {
                self.deadline = now;
                self.explicit = true;
                let a = assess(&self.evidence, &self.policy, now);
                self.timeouts(&a, now, &mut out);
            }
            Stage::Emergency | Stage::Acknowledged => {
                self.explicit = true;
                self.emit(&mut out, now, Action::RemindEmergencyNumber { hazard });
            }
            _ => {
                self.raise(hazard, now, &mut out);
                self.explicit = true;
            }
        }
        let a = assess(&self.evidence, &self.policy, now);
        self.step(now, out, a)
    }

    pub fn acknowledge(&mut self, tier: u8, now: f64) -> Step {
        let mut out = Vec::new();
        if matches!(self.stage, Stage::Alerting | Stage::Emergency) {
            self.stage = Stage::Acknowledged;
            self.emit(&mut out, now, Action::Acknowledged { tier });
        }
        let a = assess(&self.evidence, &self.policy, now);
        self.step(now, out, a)
    }

    pub fn dismiss(&mut self, now: f64) -> Step {
        let mut out = Vec::new();
        if let Some(hazard) = self.hazard {
            self.evidence
                .retain(|e| !e.kind.hazards().contains(&hazard) || e.at > now);
            if self.stage.active() {
                self.stand_down(now, &mut out);
            }
        }
        let a = assess(&self.evidence, &self.policy, now);
        self.step(now, out, a)
    }
}
