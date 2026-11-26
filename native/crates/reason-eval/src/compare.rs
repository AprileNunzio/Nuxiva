use std::collections::BTreeMap;

use serde::Serialize;

use crate::error::{EvalError, EvalResult};
use crate::model::Category;
use crate::report::{Report, Slice};

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Gates {
    pub max_success_drop: f64,
    pub max_slice_drop: f64,
    pub max_latency_growth_percent: f64,
    pub max_tokens_growth_percent: f64,
    pub min_improvement: f64,
}

impl Default for Gates {
    fn default() -> Self {
        Self {
            max_success_drop: 1.0,
            max_slice_drop: 3.0,
            max_latency_growth_percent: 25.0,
            max_tokens_growth_percent: 25.0,
            min_improvement: 1.0,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize)]
pub struct Delta {
    pub baseline: f64,
    pub candidate: f64,
    pub change: f64,
}

impl Delta {
    fn of(baseline: f64, candidate: f64) -> Self {
        Self {
            baseline,
            candidate,
            change: ((candidate - baseline) * 100.0).round() / 100.0,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Trend {
    Improved,
    Unchanged,
    Regressed,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Regression {
    pub code: &'static str,
    pub scope: String,
    pub delta: Delta,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Comparison {
    pub schema: u32,
    pub dataset: String,
    pub trend: Trend,
    pub success: Delta,
    pub intent: Delta,
    pub wrong_actions: Delta,
    pub language_gap: Delta,
    pub tokens_mean: Delta,
    pub latency_p95: Delta,
    pub by_language: BTreeMap<String, Delta>,
    pub by_category: BTreeMap<Category, Delta>,
    pub regressions: Vec<Regression>,
}

fn counts(value: u64) -> f64 {
    f64::from(u32::try_from(value).unwrap_or(u32::MAX))
}

fn growth_percent(delta: &Delta) -> f64 {
    if delta.baseline <= 0.0 {
        0.0
    } else {
        delta.change / delta.baseline * 100.0
    }
}

fn slices<K: Ord + Clone>(
    baseline: &BTreeMap<K, Slice>,
    candidate: &BTreeMap<K, Slice>,
    limit: f64,
    scope: impl Fn(&K) -> String,
    out: &mut Vec<Regression>,
) -> BTreeMap<K, Delta> {
    let mut deltas = BTreeMap::new();
    for (key, before) in baseline {
        let Some(after) = candidate.get(key) else {
            out.push(Regression {
                code: "slice_missing",
                scope: scope(key),
                delta: Delta::of(before.success_rate, 0.0),
            });
            continue;
        };
        let delta = Delta::of(before.success_rate, after.success_rate);
        if -delta.change > limit {
            out.push(Regression {
                code: "slice_drop",
                scope: scope(key),
                delta,
            });
        }
        deltas.insert(key.clone(), delta);
    }
    deltas
}

pub fn compare(baseline: &Report, candidate: &Report, gates: &Gates) -> EvalResult<Comparison> {
    let known = !baseline.dataset.is_empty() && !candidate.dataset.is_empty();
    if known && baseline.dataset != candidate.dataset {
        return Err(EvalError::Invalid("dataset_mismatch"));
    }
    let mut regressions = Vec::new();
    let success = Delta::of(
        baseline.overall.success_rate,
        candidate.overall.success_rate,
    );
    if -success.change > gates.max_success_drop {
        regressions.push(Regression {
            code: "success_drop",
            scope: "overall".into(),
            delta: success,
        });
    }
    let wrong_actions = Delta::of(
        counts(baseline.overall.wrong_actions),
        counts(candidate.overall.wrong_actions),
    );
    if wrong_actions.change > 0.0 {
        regressions.push(Regression {
            code: "wrong_actions_up",
            scope: "overall".into(),
            delta: wrong_actions,
        });
    }
    let latency_p95 = Delta::of(baseline.latency_ms.p95, candidate.latency_ms.p95);
    if growth_percent(&latency_p95) > gates.max_latency_growth_percent {
        regressions.push(Regression {
            code: "latency_up",
            scope: "p95".into(),
            delta: latency_p95,
        });
    }
    let tokens_mean = Delta::of(baseline.tokens.mean, candidate.tokens.mean);
    if growth_percent(&tokens_mean) > gates.max_tokens_growth_percent {
        regressions.push(Regression {
            code: "tokens_up",
            scope: "mean".into(),
            delta: tokens_mean,
        });
    }
    let by_language = slices(
        &baseline.by_language,
        &candidate.by_language,
        gates.max_slice_drop,
        |lang| format!("language.{lang}"),
        &mut regressions,
    );
    let by_category = slices(
        &baseline.by_category,
        &candidate.by_category,
        gates.max_slice_drop,
        |category| format!("category.{category:?}").to_lowercase(),
        &mut regressions,
    );
    let trend = if !regressions.is_empty() {
        Trend::Regressed
    } else if success.change >= gates.min_improvement {
        Trend::Improved
    } else {
        Trend::Unchanged
    };
    Ok(Comparison {
        schema: 1,
        dataset: candidate.dataset.clone(),
        trend,
        success,
        intent: Delta::of(baseline.overall.intent_rate, candidate.overall.intent_rate),
        wrong_actions,
        language_gap: Delta::of(baseline.language_gap_points, candidate.language_gap_points),
        tokens_mean,
        latency_p95,
        by_language,
        by_category,
        regressions,
    })
}
