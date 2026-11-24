use std::collections::{BTreeMap, BTreeSet};

use reason_eval::{EvalError, EvalResult, Outcome, build, judge, parse_outcomes};
use serde_json::{Value, json};

use crate::backend::Backend;
use crate::custom::{expand_custom, inspect, parse_scenarios};
use crate::outcome::to_outcome;

fn to_json<T: serde::Serialize>(value: &T) -> EvalResult<String> {
    Ok(serde_json::to_string(value)?)
}

pub fn inspect_dataset(dataset: &[u8]) -> EvalResult<String> {
    let scenarios = parse_scenarios(dataset)?;
    let cases = expand_custom(&scenarios)?;
    to_json(&inspect(scenarios.len(), &cases))
}

pub fn list_cases(dataset: &[u8]) -> EvalResult<String> {
    let cases = expand_custom(&parse_scenarios(dataset)?)?;
    let rows: Vec<Value> = cases
        .iter()
        .map(|c| {
            json!({
                "id": c.id,
                "scenario": c.scenario,
                "lang": c.lang,
                "category": c.category,
                "text": c.text,
                "external_content": c.external_content,
            })
        })
        .collect();
    to_json(&rows)
}

pub fn request(
    backend: &str,
    base: &str,
    model: &str,
    user: &str,
    external: Option<&str>,
) -> EvalResult<String> {
    let backend = Backend::parse(backend).ok_or(EvalError::Invalid("backend"))?;
    let prompt = reason_understand::build(user, external);
    to_json(&json!({
        "url": crate::endpoint_url(backend, base),
        "body": backend.body(model, &prompt),
    }))
}

pub fn outcome(
    backend: &str,
    case_id: &str,
    user_text: &str,
    reply: Option<&str>,
    latency_ms: u64,
) -> EvalResult<String> {
    let backend = Backend::parse(backend).ok_or(EvalError::Invalid("backend"))?;
    let extracted = reply.and_then(|body| backend.extract(body));
    let (content, tokens) = extracted.map_or((None, 0), |(c, t)| (Some(c), t));
    let outcome: Outcome = to_outcome(case_id, user_text, content.as_deref(), tokens, latency_ms);
    to_json(&outcome)
}

pub fn report(dataset: &[u8], outcomes: &[u8]) -> EvalResult<String> {
    let outcomes = parse_outcomes(outcomes)?;
    let done: BTreeSet<&str> = outcomes.iter().map(|o| o.case_id.as_str()).collect();
    let cases: Vec<_> = expand_custom(&parse_scenarios(dataset)?)?
        .into_iter()
        .filter(|c| done.contains(c.id.as_str()))
        .collect();
    to_json(&build(&cases, &outcomes)?)
}

pub fn rows(dataset: &[u8], outcomes: &[u8]) -> EvalResult<String> {
    let outcomes = parse_outcomes(outcomes)?;
    let by_id: BTreeMap<&str, &Outcome> =
        outcomes.iter().map(|o| (o.case_id.as_str(), o)).collect();
    let rows: Vec<Value> = expand_custom(&parse_scenarios(dataset)?)?
        .iter()
        .filter_map(|case| {
            let outcome = by_id.get(case.id.as_str())?;
            let verdict = judge(case, outcome);
            Some(json!({
                "case_id": case.id,
                "lang": case.lang,
                "category": case.category,
                "text": case.text,
                "expected_intent": case.expected.intent,
                "expected_effects": case.expected.effects,
                "intent": outcome.intent,
                "effects": outcome.effects,
                "completed": outcome.completed,
                "intent_match": verdict.intent_match,
                "success": verdict.success,
                "wrong_action": verdict.wrong_action,
                "tokens": outcome.tokens,
                "latency_ms": outcome.latency_ms,
            }))
        })
        .collect();
    to_json(&rows)
}
