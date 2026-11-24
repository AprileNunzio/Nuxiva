use std::collections::BTreeSet;
use std::path::Path;

use crate::error::{EvalError, EvalResult};
use crate::model::{Case, Category, LANGUAGES, MAX_EXTERNAL_BYTES, MAX_TEXT_BYTES, Scenario};

pub const MIN_CASES: usize = 300;
pub const MIN_ADVERSARIAL_CASES: usize = 50;
pub const MIN_HARD_PERCENT: usize = 40;

fn valid_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 64
        && id
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_')
}

fn clean(text: &str) -> bool {
    !text.trim().is_empty() && !text.chars().any(|c| c.is_control() && c != '\n')
}

fn check(scenario: &Scenario) -> EvalResult<()> {
    if !valid_id(&scenario.id) || !valid_id(&scenario.expected.intent) {
        return Err(EvalError::Invalid("id"));
    }
    if scenario.texts.len() != LANGUAGES.len()
        || LANGUAGES.iter().any(|l| !scenario.texts.contains_key(*l))
    {
        return Err(EvalError::Invalid("languages"));
    }
    if scenario
        .texts
        .values()
        .any(|t| !clean(t) || t.len() > MAX_TEXT_BYTES)
    {
        return Err(EvalError::Invalid("text"));
    }
    let external = scenario.category == Category::Adversarial;
    match &scenario.external_content {
        Some(body) if external && clean(body) && body.len() <= MAX_EXTERNAL_BYTES => Ok(()),
        None if !external => Ok(()),
        _ => Err(EvalError::Invalid("external_content")),
    }
}

pub fn parse(bytes: &[u8]) -> EvalResult<Vec<Scenario>> {
    Ok(serde_json::from_slice(bytes)?)
}

pub fn load_dir(dir: &Path) -> EvalResult<Vec<Scenario>> {
    let mut paths: Vec<_> = std::fs::read_dir(dir)?
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| path.extension().is_some_and(|ext| ext == "json"))
        .collect();
    paths.sort();
    let mut all = Vec::new();
    for path in paths {
        all.extend(parse(&bench_core::read_limited(&path)?)?);
    }
    Ok(all)
}

pub fn expand(scenarios: &[Scenario]) -> EvalResult<Vec<Case>> {
    let mut seen = BTreeSet::new();
    let mut cases = Vec::new();
    for scenario in scenarios {
        check(scenario)?;
        if !seen.insert(scenario.id.clone()) {
            return Err(EvalError::Duplicate(scenario.id.clone()));
        }
        for lang in LANGUAGES {
            let text = scenario
                .texts
                .get(lang)
                .ok_or(EvalError::Invalid("languages"))?;
            cases.push(Case {
                id: format!("{}.{lang}", scenario.id),
                scenario: scenario.id.clone(),
                lang: lang.to_owned(),
                category: scenario.category,
                text: text.clone(),
                external_content: scenario.external_content.clone(),
                expected: scenario.expected.clone(),
            });
        }
    }
    Ok(cases)
}

pub fn enforce_floor(cases: &[Case]) -> EvalResult<()> {
    let total = cases.len();
    let adversarial = cases
        .iter()
        .filter(|c| c.category == Category::Adversarial)
        .count();
    let hard = cases
        .iter()
        .filter(|c| matches!(c.category, Category::Composite | Category::Novel))
        .count();
    if total < MIN_CASES {
        return Err(EvalError::Invalid("too_few_cases"));
    }
    if adversarial < MIN_ADVERSARIAL_CASES {
        return Err(EvalError::Invalid("too_few_adversarial"));
    }
    if hard.saturating_mul(100) < total.saturating_mul(MIN_HARD_PERCENT) {
        return Err(EvalError::Invalid("too_few_hard"));
    }
    Ok(())
}
