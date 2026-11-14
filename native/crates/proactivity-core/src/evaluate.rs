use nuxiva_taskq_core::Risk;

use crate::clock::{in_span, local};
use crate::engine::{Deferred, Engine, Origin, Request, fact_key, push_capped};
use crate::gate::{Gate, effective, gate};
use crate::learn::key;
use crate::model::{Context, Decision, Explanation, Level, Mode, Reason, Situation, Urgency};
use crate::rules::Rule;

struct Eval {
    k: String,
    critical: bool,
    confidence: u32,
    origin: &'static str,
    verdict: Gate,
    cost: u32,
    score: i64,
    quiet: bool,
    muted_person: bool,
}

enum Outcome {
    Silent(Reason),
    Defer(Reason),
    Surface,
}

impl Engine {
    fn conditions_hold(&self, rule: &Rule, person: Option<&str>, now: u64) -> bool {
        let ttl = self.settings.signal_ttl_ms;
        rule.when.iter().all(|c| {
            let who = if c.same_person { person } else { None };
            let value = self
                .facts
                .get(&fact_key(c.domain.name(), &c.key, who))
                .filter(|f| now.saturating_sub(f.at) <= ttl)
                .map(|f| f.value);
            c.test(value)
        })
    }

    fn confidence(
        &self,
        request: &Request,
        now: u64,
        rule: &Rule,
        k: &str,
        at: &crate::clock::Local,
        reasons: &mut Vec<Reason>,
    ) -> (u32, &'static str) {
        let habit_p = self
            .habits
            .get(k)
            .zip(rule.habit)
            .and_then(|(h, s)| h.probability(at, s.min_days));
        let (base, origin) = match request.origin {
            Origin::Signal => {
                reasons.push(
                    Reason::new("proactive.why.signal")
                        .with("domain", rule.trigger.domain.name())
                        .with("key", &rule.trigger.key)
                        .with("subject", &request.subject),
                );
                match habit_p {
                    Some(p) => {
                        reasons
                            .push(Reason::new("proactive.why.habit_support").with("permille", p));
                        (rule.base_confidence.saturating_add(p) / 2, "signal")
                    }
                    None => (rule.base_confidence, "signal"),
                }
            }
            Origin::Habit(p) => {
                reasons.push(Reason::new("proactive.why.habit").with("permille", p));
                (p.saturating_mul(rule.base_confidence) / 1_000, "habit")
            }
            Origin::Forecast(p) => {
                reasons.push(Reason::new("proactive.why.forecast").with("permille", p));
                (p, "forecast")
            }
        };
        let mult = self.learner.multiplier(k, now);
        if mult >= 1_100 {
            reasons.push(Reason::new("proactive.why.learned_up").with("multiplier", mult));
        } else if mult <= 900 {
            reasons.push(Reason::new("proactive.why.learned_down").with("multiplier", mult));
        }
        (
            base.saturating_mul(mult).saturating_div(1_000).min(1_000),
            origin,
        )
    }

    fn assess(
        &self,
        request: &Request,
        rule: &Rule,
        ctx: &Context,
        now: u64,
        reasons: &mut Vec<Reason>,
    ) -> Option<Eval> {
        let at = local(now, ctx.tz_offset_min);
        if rule.window.is_some_and(|w| !w.contains(&at))
            || !self.conditions_hold(rule, request.person.as_deref(), now)
        {
            return None;
        }
        let k = key(&request.rule, request.person.as_deref());
        let critical = rule.urgency == Urgency::Critical;
        if rule.window.is_some() {
            reasons.push(Reason::new("proactive.why.window"));
        }
        if !rule.when.is_empty() {
            reasons.push(Reason::new("proactive.why.conditions").with("count", rule.when.len()));
        }
        if critical {
            reasons.push(Reason::new("proactive.why.critical"));
        }
        let (confidence, origin) = self.confidence(request, now, rule, &k, &at, reasons);
        let person = request.person.as_deref();
        let policy = person.and_then(|p| self.policies.get(p));
        let verdict = gate(effective(rule.privacy, rule.domain, policy), person, ctx);
        let cost = if critical {
            0
        } else {
            self.settings.cost(ctx.situation)
        };
        let gross = i64::from(rule.value)
            .saturating_mul(i64::from(confidence))
            .checked_div(1_000)
            .unwrap_or(0);
        Some(Eval {
            k,
            critical,
            confidence,
            origin,
            verdict,
            cost,
            score: gross.saturating_sub(i64::from(cost)),
            quiet: in_span(
                at.minute,
                self.settings.quiet_start_min,
                self.settings.quiet_end_min,
            ),
            muted_person: policy.is_some_and(|p| p.muted.contains(&rule.domain)),
        })
    }

    fn classify(&mut self, eval: &Eval, request: &Request, rule: &Rule, now: u64) -> Outcome {
        let person = request.person.as_deref();
        let critical = eval.critical;
        if !critical && eval.muted_person {
            Outcome::Silent(Reason::new("proactive.why.muted_by_person"))
        } else if !critical && self.learner.muted(&eval.k, now) {
            Outcome::Silent(Reason::new("proactive.why.muted_by_feedback"))
        } else if eval.confidence < rule.min_confidence {
            Outcome::Silent(
                Reason::new("proactive.why.low_confidence")
                    .with("confidence", eval.confidence)
                    .with("threshold", rule.min_confidence),
            )
        } else if eval.verdict == Gate::Block {
            Outcome::Defer(Reason::new("proactive.why.privacy_block"))
        } else if !critical && eval.quiet {
            Outcome::Defer(Reason::new("proactive.why.quiet_hours"))
        } else if eval.score <= 0 {
            Outcome::Defer(Reason::new("proactive.why.cost").with("cost", eval.cost))
        } else if !critical && self.interruptions.global(now) >= self.settings.hourly_cap {
            Outcome::Defer(
                Reason::new("proactive.why.cap_global").with("cap", self.settings.hourly_cap),
            )
        } else if !critical
            && self.interruptions.person(person, now) >= self.settings.person_hourly_cap
        {
            Outcome::Defer(
                Reason::new("proactive.why.cap_person")
                    .with("cap", self.settings.person_hourly_cap),
            )
        } else {
            Outcome::Surface
        }
    }

    pub(crate) fn run(
        &mut self,
        request: &Request,
        ctx: &Context,
        now: u64,
        retry: Option<u64>,
    ) -> Option<Decision> {
        let rule = self.rules.rules.get(&request.rule)?.clone();
        let mut reasons = Vec::new();
        let eval = self.assess(request, &rule, ctx, now, &mut reasons)?;
        let redacted = eval.verdict == Gate::Redact;
        if redacted {
            for reason in &mut reasons {
                reason.params.remove("subject");
            }
        }
        let expires_at = retry.unwrap_or_else(|| now.saturating_add(self.settings.proposal_ttl_ms));
        let (mode, deferred, level) = match self.classify(&eval, request, &rule, now) {
            Outcome::Silent(reason) => {
                reasons.push(reason);
                (Mode::Diary, false, Level::Silent)
            }
            Outcome::Defer(reason) => {
                if retry.is_none() {
                    let counter = if reason.code == "proactive.why.privacy_block" {
                        &mut self.stats.blocked
                    } else {
                        &mut self.stats.capped
                    };
                    *counter = counter.saturating_add(1);
                }
                reasons.push(reason);
                push_capped(
                    &mut self.deferred,
                    Deferred {
                        request: request.clone(),
                        expires_at,
                    },
                    self.settings.deferred_cap,
                );
                (Mode::Diary, true, Level::Silent)
            }
            Outcome::Surface => {
                self.pick_mode(&rule, &request.rule, &eval, redacted, ctx, &mut reasons)
            }
        };
        if deferred && retry.is_some() {
            return None;
        }
        if mode == Mode::Diary && !deferred {
            self.stats.silent = self.stats.silent.saturating_add(1);
        }
        let hidden = redacted && rule.urgency != Urgency::Critical;
        let action = if mode == Mode::Diary || hidden || level == Level::Notify {
            None
        } else {
            self.build_task(&request.rule, &rule, &request.subject)
        };
        let decision = Decision {
            id: self.next_id,
            rule: request.rule.clone(),
            person: request.person.clone(),
            summary_key: if redacted {
                "proactive.redacted".to_owned()
            } else {
                rule.summary_key.clone()
            },
            subject: if redacted {
                String::new()
            } else {
                request.subject.clone()
            },
            requires_consent: mode != Mode::Execute
                && action.is_some()
                && rule.action.risk_max >= Risk::Medium,
            action,
            mode,
            confidence: eval.confidence,
            score: eval.score,
            redacted,
            deferred,
            undoable: rule.action.undo.is_some() && mode != Mode::Diary && level >= Level::Propose,
            created_at: now,
            expires_at,
            explanation: Explanation {
                rule: request.rule.clone(),
                origin: eval.origin,
                confidence: eval.confidence,
                threshold: rule.min_confidence,
                score: eval.score,
                reasons,
            },
        };
        self.next_id = self.next_id.saturating_add(1);
        self.store(&decision, now);
        Some(decision)
    }

    fn pick_mode(
        &self,
        rule: &Rule,
        rule_id: &str,
        eval: &Eval,
        redacted: bool,
        ctx: &Context,
        reasons: &mut Vec<Reason>,
    ) -> (Mode, bool, Level) {
        let mut level = rule.level;
        let steps = self.learner.demotions(&eval.k);
        let critical = eval.critical;
        for _ in 0..steps {
            level = level.lower();
        }
        if steps > 0 && rule.level != level {
            reasons.push(Reason::new("proactive.why.level_lowered").with("steps", steps));
        }
        if redacted {
            reasons.push(Reason::new("proactive.why.privacy_redact"));
            if !critical {
                level = level.min(Level::Notify);
            }
        }
        if level == Level::DoAndTell {
            if self.approved.contains(rule_id)
                && rule.action.risk_max <= Risk::Low
                && rule.action.undo.is_some()
            {
                reasons.push(Reason::new("proactive.why.auto_approved"));
            } else {
                reasons.push(Reason::new("proactive.why.needs_approval"));
                level = Level::Propose;
            }
        }
        if level == Level::Propose && rule.action.risk_max >= Risk::Medium {
            reasons.push(Reason::new("proactive.why.consent_needed"));
        }
        match level {
            Level::Silent => (Mode::Diary, false, level),
            Level::DoAndTell => (Mode::Execute, false, level),
            _ => {
                let voice =
                    ctx.voice_free && !redacted && (ctx.situation == Situation::Idle || critical);
                if voice {
                    reasons.push(Reason::new("proactive.why.mode_speak"));
                    (Mode::Speak, false, level)
                } else {
                    reasons.push(Reason::new("proactive.why.mode_widget"));
                    (Mode::Widget, false, level)
                }
            }
        }
    }

    fn store(&mut self, decision: &Decision, now: u64) {
        push_capped(&mut self.log, decision.clone(), self.settings.log_cap);
        match decision.mode {
            Mode::Diary => {}
            Mode::Execute => {
                self.interruptions.charge(decision.person.as_deref(), now);
                self.stats.surfaced = self.stats.surfaced.saturating_add(1);
                self.register_undo(decision, now);
            }
            Mode::Widget | Mode::Speak => {
                self.interruptions.charge(decision.person.as_deref(), now);
                self.stats.surfaced = self.stats.surfaced.saturating_add(1);
                push_capped(
                    &mut self.pending,
                    decision.clone(),
                    self.settings.pending_cap,
                );
            }
        }
    }
}
