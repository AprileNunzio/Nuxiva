use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::config::{DAY_MS, Gate};
use crate::error::{EngineError, EngineResult};

pub const KEEP_DAYS: u64 = 60;
pub const MAX_LEDGER_BYTES: usize = 256 * 1024;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
#[allow(clippy::struct_excessive_bools)]
pub struct Sample {
    pub comparable: bool,
    pub agreed: bool,
    pub valid: bool,
    pub missing: bool,
    pub cached: bool,
    pub wrong_action: bool,
    pub latency_ms: u32,
    pub tokens: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Bucket {
    pub total: u32,
    pub comparable: u32,
    pub agreed: u32,
    pub invalid: u32,
    pub missing: u32,
    pub cached: u32,
    pub wrong_action: u32,
    pub latency_ms: u64,
    pub tokens: u64,
}

impl Bucket {
    fn add(&mut self, s: &Sample) {
        let inc = |v: &mut u32, on: bool| {
            if on {
                *v = v.saturating_add(1);
            }
        };
        inc(&mut self.total, true);
        inc(&mut self.comparable, s.comparable);
        inc(&mut self.agreed, s.comparable && s.agreed);
        inc(&mut self.invalid, !s.valid);
        inc(&mut self.missing, s.missing);
        inc(&mut self.cached, s.cached);
        inc(&mut self.wrong_action, s.wrong_action);
        self.latency_ms = self.latency_ms.saturating_add(u64::from(s.latency_ms));
        self.tokens = self.tokens.saturating_add(u64::from(s.tokens));
    }

    fn merge(&mut self, o: &Self) {
        self.total = self.total.saturating_add(o.total);
        self.comparable = self.comparable.saturating_add(o.comparable);
        self.agreed = self.agreed.saturating_add(o.agreed);
        self.invalid = self.invalid.saturating_add(o.invalid);
        self.missing = self.missing.saturating_add(o.missing);
        self.cached = self.cached.saturating_add(o.cached);
        self.wrong_action = self.wrong_action.saturating_add(o.wrong_action);
        self.latency_ms = self.latency_ms.saturating_add(o.latency_ms);
        self.tokens = self.tokens.saturating_add(o.tokens);
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct GateStatus {
    pub ready: bool,
    pub days: u64,
    pub samples: u32,
    pub agreement_bps: u16,
    pub invalid_bps: u16,
    pub wrong_action: u32,
    pub totals: Bucket,
    pub reasons: Vec<&'static str>,
}

#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Ledger {
    days: BTreeMap<u64, Bucket>,
}

fn ratio_bps(part: u32, whole: u32) -> u16 {
    if whole == 0 {
        return 0;
    }
    let value = u64::from(part)
        .saturating_mul(10_000)
        .checked_div(u64::from(whole))
        .unwrap_or(0);
    u16::try_from(value.min(10_000)).unwrap_or(10_000)
}

impl Ledger {
    pub fn parse(raw: &str) -> EngineResult<Self> {
        if raw.len() > MAX_LEDGER_BYTES {
            return Err(EngineError::Ledger("too_large"));
        }
        let ledger: Self = serde_json::from_str(raw).map_err(|_| EngineError::Ledger("schema"))?;
        if u64::try_from(ledger.days.len()).unwrap_or(u64::MAX) > KEEP_DAYS {
            return Err(EngineError::Ledger("too_many_days"));
        }
        Ok(ledger)
    }

    pub fn to_json(&self) -> EngineResult<String> {
        serde_json::to_string(self).map_err(|_| EngineError::Ledger("encode"))
    }

    pub fn record(&mut self, sample: &Sample, now: u64) {
        let day = now.checked_div(DAY_MS).unwrap_or(0);
        self.days.entry(day).or_default().add(sample);
        let floor = day.saturating_sub(KEEP_DAYS.saturating_sub(1));
        self.days.retain(|d, _| *d >= floor);
    }

    pub fn reset(&mut self) {
        self.days.clear();
    }

    #[must_use]
    pub fn status(&self, gate: &Gate, now: u64) -> GateStatus {
        let today = now.checked_div(DAY_MS).unwrap_or(0);
        let window = today.saturating_sub(u64::from(gate.min_days).saturating_sub(1));
        let mut totals = Bucket::default();
        for (_, bucket) in self.days.range(window..=today) {
            totals.merge(bucket);
        }
        let first = self.days.keys().next().copied().unwrap_or(today);
        let days = today.saturating_sub(first).saturating_add(1);
        let agreement_bps = ratio_bps(totals.agreed, totals.comparable);
        let invalid_bps = ratio_bps(totals.invalid, totals.total);
        let mut reasons = Vec::new();
        if self.days.is_empty() || days < u64::from(gate.min_days) {
            reasons.push("reason.gate.too_few_days");
        }
        if totals.comparable < gate.min_samples {
            reasons.push("reason.gate.too_few_samples");
        }
        if agreement_bps < gate.min_agreement_bps {
            reasons.push("reason.gate.low_agreement");
        }
        if invalid_bps > gate.max_invalid_bps {
            reasons.push("reason.gate.too_many_invalid");
        }
        if totals.wrong_action > gate.max_wrong_action {
            reasons.push("reason.gate.wrong_actions");
        }
        GateStatus {
            ready: reasons.is_empty(),
            days,
            samples: totals.comparable,
            agreement_bps,
            invalid_bps,
            wrong_action: totals.wrong_action,
            totals,
            reasons,
        }
    }
}
