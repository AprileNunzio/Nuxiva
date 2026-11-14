use std::collections::BTreeSet;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RankError {
    NotFinite,
}

impl std::fmt::Display for RankError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "llm.rank.not_finite")
    }
}

impl std::error::Error for RankError {}

fn finite(values: &[f64]) -> bool {
    values.iter().all(|value| value.is_finite())
}

fn sum_products(left: &[f64], right: &[f64]) -> f64 {
    left.iter()
        .zip(right)
        .fold(0.0, |total, (a, b)| total + a * b)
}

fn norm(values: &[f64]) -> f64 {
    values.iter().fold(0.0, |total, a| total + a * a).sqrt()
}

pub fn cosine(left: &[f64], right: &[f64]) -> Result<f64, RankError> {
    if !finite(left) || !finite(right) {
        return Err(RankError::NotFinite);
    }
    if left.is_empty() || right.is_empty() {
        return Ok(0.0);
    }
    let (na, nb) = (norm(left), norm(right));
    if na == 0.0 || nb == 0.0 {
        return Ok(0.0);
    }
    Ok(sum_products(left, right) / (na * nb))
}

pub fn retrieve(
    prompt: &[f64],
    indexed: &[(String, Vec<f64>)],
    top_k: usize,
    always: &[&str],
) -> Result<BTreeSet<String>, RankError> {
    let mut scores = Vec::with_capacity(indexed.len());
    for (id, embedding) in indexed {
        scores.push((cosine(prompt, embedding)?, id));
    }
    scores.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
    let mut chosen: BTreeSet<String> = always.iter().map(|id| (*id).to_owned()).collect();
    chosen.extend(scores.into_iter().take(top_k).map(|(_, id)| id.clone()));
    Ok(chosen)
}
