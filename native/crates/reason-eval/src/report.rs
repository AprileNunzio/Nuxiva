use std::collections::{BTreeMap, HashMap};

use bench_core::{Summary, summarize};
use serde::Serialize;

use crate::error::{EvalError, EvalResult};
use crate::model::{Case, Category, Outcome};
use crate::score::judge;

#[derive(Debug, Clone, Default, PartialEq, Serialize)]
pub struct Slice {
    pub cases: u64,
    pub intent_match: u64,
    pub success: u64,
    pub wrong_actions: u64,
    pub intent_rate: f64,
    pub success_rate: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Report {
    pub schema: u32,
    pub overall: Slice,
    pub by_language: BTreeMap<String, Slice>,
    pub by_category: BTreeMap<Category, Slice>,
    pub language_gap_points: f64,
    pub tokens: Summary,
    pub latency_ms: Summary,
}

fn rate(part: u64, whole: u64) -> f64 {
    let scaled = part.saturating_mul(10_000).checked_div(whole).unwrap_or(0);
    f64::from(u32::try_from(scaled).unwrap_or(u32::MAX)) / 100.0
}

fn finish(slice: &mut Slice) {
    slice.intent_rate = rate(slice.intent_match, slice.cases);
    slice.success_rate = rate(slice.success, slice.cases);
}

fn add(slice: &mut Slice, intent: bool, success: bool, wrong: bool) {
    slice.cases = slice.cases.saturating_add(1);
    slice.intent_match = slice.intent_match.saturating_add(u64::from(intent));
    slice.success = slice.success.saturating_add(u64::from(success));
    slice.wrong_actions = slice.wrong_actions.saturating_add(u64::from(wrong));
}

fn counts(value: u64) -> f64 {
    f64::from(u32::try_from(value).unwrap_or(u32::MAX))
}

pub fn build(cases: &[Case], outcomes: &[Outcome]) -> EvalResult<Report> {
    let index: HashMap<&str, &Outcome> = outcomes.iter().map(|o| (o.case_id.as_str(), o)).collect();
    if index.len() != outcomes.len() {
        return Err(EvalError::Invalid("duplicate_outcome"));
    }
    let mut overall = Slice::default();
    let mut languages: BTreeMap<String, Slice> = BTreeMap::new();
    let mut categories: BTreeMap<Category, Slice> = BTreeMap::new();
    let mut tokens = Vec::with_capacity(cases.len());
    let mut latency = Vec::with_capacity(cases.len());
    for case in cases {
        let outcome = index
            .get(case.id.as_str())
            .ok_or_else(|| EvalError::Missing(case.id.clone()))?;
        let verdict = judge(case, outcome);
        add(
            &mut overall,
            verdict.intent_match,
            verdict.success,
            verdict.wrong_action,
        );
        add(
            languages.entry(case.lang.clone()).or_default(),
            verdict.intent_match,
            verdict.success,
            verdict.wrong_action,
        );
        add(
            categories.entry(case.category).or_default(),
            verdict.intent_match,
            verdict.success,
            verdict.wrong_action,
        );
        tokens.push(counts(outcome.tokens));
        latency.push(counts(outcome.latency_ms));
    }
    finish(&mut overall);
    languages.values_mut().for_each(finish);
    categories.values_mut().for_each(finish);
    let rates: Vec<f64> = languages.values().map(|s| s.intent_rate).collect();
    let best = rates.iter().copied().fold(0.0_f64, f64::max);
    let worst = rates.iter().copied().fold(100.0_f64, f64::min);
    Ok(Report {
        schema: 1,
        overall,
        by_language: languages,
        by_category: categories,
        language_gap_points: if rates.is_empty() { 0.0 } else { best - worst },
        tokens: summarize(&tokens)?,
        latency_ms: summarize(&latency)?,
    })
}

pub fn parse_outcomes(bytes: &[u8]) -> EvalResult<Vec<Outcome>> {
    let text = std::str::from_utf8(bytes).map_err(|_| EvalError::Invalid("utf8"))?;
    text.lines()
        .filter(|line| !line.trim().is_empty())
        .map(|line| serde_json::from_str(line).map_err(EvalError::from))
        .collect()
}
