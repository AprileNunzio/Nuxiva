pub const CONFIDENCE_WEIGHT: f64 = 0.55;
pub const CRITIC_WEIGHT: f64 = 0.45;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct CriticWeights {
    pub confidence: f64,
    pub critic: f64,
}

impl Default for CriticWeights {
    fn default() -> Self {
        Self {
            confidence: CONFIDENCE_WEIGHT,
            critic: CRITIC_WEIGHT,
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Candidate {
    pub has_text: bool,
    pub score: f64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Group {
    Cloud(String),
    Local(Vec<String>),
}

#[must_use]
pub fn valid_text(text: &str) -> bool {
    let stripped = text.trim();
    !stripped.is_empty() && !stripped.to_lowercase().starts_with("errore")
}

#[must_use]
pub fn round3(value: f64) -> f64 {
    format!("{value:.3}").parse().unwrap_or(value)
}

#[must_use]
pub fn score(confidence: f64, critic: Option<f64>, weights: CriticWeights) -> f64 {
    critic.map_or(confidence, |critic| {
        confidence * weights.confidence + critic * weights.critic
    })
}

#[must_use]
pub fn best_index(candidates: &[Candidate]) -> Option<usize> {
    let mut best: Option<(usize, f64)> = None;
    for (index, candidate) in candidates.iter().enumerate() {
        let better = best.is_none_or(|(_, top)| candidate.score > top);
        if better {
            best = Some((index, candidate.score));
        }
    }
    best.map(|(index, _)| index)
}

#[must_use]
pub fn group_models(models: &[(String, bool)]) -> Vec<Group> {
    let mut out: Vec<Group> = Vec::new();
    let mut run: Vec<String> = Vec::new();
    let mut run_cloud: Option<bool> = None;
    for (name, cloud) in models {
        if run_cloud.is_some_and(|current| current != *cloud) {
            flush(&mut out, &mut run, run_cloud);
        }
        run_cloud = Some(*cloud);
        run.push(name.clone());
    }
    flush(&mut out, &mut run, run_cloud);
    out
}

fn flush(out: &mut Vec<Group>, run: &mut Vec<String>, cloud: Option<bool>) {
    let names = std::mem::take(run);
    if names.is_empty() {
        return;
    }
    if cloud == Some(true) {
        out.extend(names.into_iter().map(Group::Cloud));
    } else {
        out.push(Group::Local(names));
    }
}
