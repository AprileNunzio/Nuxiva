use std::collections::{BTreeMap, BTreeSet};

use reason_eval::{
    Case, Category, EvalError, EvalResult, MAX_EXTERNAL_BYTES, MAX_TEXT_BYTES, Scenario,
};
use serde::Serialize;

pub const MAX_SCENARIOS: usize = 1_000;
pub const MAX_LANGUAGES: usize = 12;
pub const MAX_DATASET_BYTES: usize = 4 * 1024 * 1024;

fn valid_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 64
        && id
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_')
}

fn valid_lang(lang: &str) -> bool {
    (2..=3).contains(&lang.len()) && lang.bytes().all(|b| b.is_ascii_lowercase())
}

fn clean(text: &str) -> bool {
    !text.trim().is_empty() && !text.chars().any(|c| c.is_control() && c != '\n')
}

fn check(scenario: &Scenario) -> EvalResult<()> {
    if !valid_id(&scenario.id) || !valid_id(&scenario.expected.intent) {
        return Err(EvalError::Invalid("id"));
    }
    let texts = &scenario.texts;
    let langs_ok =
        !texts.is_empty() && texts.len() <= MAX_LANGUAGES && texts.keys().all(|l| valid_lang(l));
    if !langs_ok {
        return Err(EvalError::Invalid("languages"));
    }
    if texts
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

pub fn parse_scenarios(bytes: &[u8]) -> EvalResult<Vec<Scenario>> {
    if bytes.len() > MAX_DATASET_BYTES {
        return Err(EvalError::Invalid("too_large"));
    }
    let scenarios = reason_eval::parse(bytes)?;
    if scenarios.is_empty() || scenarios.len() > MAX_SCENARIOS {
        return Err(EvalError::Invalid("scenario_count"));
    }
    Ok(scenarios)
}

pub fn expand_custom(scenarios: &[Scenario]) -> EvalResult<Vec<Case>> {
    let mut seen = BTreeSet::new();
    let mut cases = Vec::new();
    for scenario in scenarios {
        check(scenario)?;
        if !seen.insert(scenario.id.clone()) {
            return Err(EvalError::Duplicate(scenario.id.clone()));
        }
        for (lang, text) in &scenario.texts {
            cases.push(Case {
                id: format!("{}.{lang}", scenario.id),
                scenario: scenario.id.clone(),
                lang: lang.clone(),
                category: scenario.category,
                text: text.clone(),
                external_content: scenario.external_content.clone(),
                expected: scenario.expected.clone(),
            });
        }
    }
    Ok(cases)
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Inspection {
    pub scenarios: usize,
    pub cases: usize,
    pub by_language: BTreeMap<String, u64>,
    pub by_category: BTreeMap<Category, u64>,
}

#[must_use]
pub fn inspect(scenarios: usize, cases: &[Case]) -> Inspection {
    let mut by_language: BTreeMap<String, u64> = BTreeMap::new();
    let mut by_category: BTreeMap<Category, u64> = BTreeMap::new();
    for case in cases {
        let language = by_language.entry(case.lang.clone()).or_default();
        *language = language.saturating_add(1);
        let category = by_category.entry(case.category).or_default();
        *category = category.saturating_add(1);
    }
    Inspection {
        scenarios,
        cases: cases.len(),
        by_language,
        by_category,
    }
}
