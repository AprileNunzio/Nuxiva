use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, PartialEq)]
pub struct Verdict {
    pub slug: Option<String>,
    pub best: Option<String>,
    pub score: f32,
    pub second: Option<String>,
    pub second_score: f32,
    pub ambiguous: bool,
    pub twin: bool,
    pub reason: &'static str,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Rules {
    pub base: f32,
    pub margin: f32,
    pub twin_margin: f32,
}

pub type Pair = (String, String);

#[must_use]
pub fn pair(a: &str, b: &str) -> Pair {
    if a <= b {
        (a.to_owned(), b.to_owned())
    } else {
        (b.to_owned(), a.to_owned())
    }
}

#[must_use]
pub fn fuse(
    primary: &BTreeMap<String, f32>,
    secondary: Option<&BTreeMap<String, f32>>,
    weight: f32,
    floor: f32,
) -> (BTreeMap<String, f32>, bool) {
    let Some(secondary) = secondary.filter(|s| !s.is_empty()) else {
        return (primary.clone(), false);
    };
    let mut fused = BTreeMap::new();
    for slug in primary.keys().chain(secondary.keys()) {
        let value = match (primary.get(slug), secondary.get(slug)) {
            (Some(a), Some(b)) => (1.0 - weight) * a + weight * b,
            (Some(a), None) => *a,
            (None, Some(b)) => *b,
            (None, None) => continue,
        };
        fused.insert(slug.clone(), value);
    }
    let top = |m: &BTreeMap<String, f32>| {
        m.iter()
            .max_by(|a, b| a.1.total_cmp(b.1))
            .map(|(k, v)| (k.clone(), *v))
    };
    let conflict = match (top(primary), top(secondary)) {
        (Some((a, _)), Some((b, score))) => a != b && score >= floor,
        _ => false,
    };
    (fused, conflict)
}

#[must_use]
pub fn decide(
    scores: &BTreeMap<String, f32>,
    thresholds: &BTreeMap<String, f32>,
    rules: Rules,
    twins: &BTreeSet<Pair>,
    shadows: &BTreeMap<String, String>,
    conflict: bool,
) -> Verdict {
    let mut ranked: Vec<(&String, f32)> = scores.iter().map(|(k, v)| (k, *v)).collect();
    ranked.sort_by(|a, b| b.1.total_cmp(&a.1).then_with(|| a.0.cmp(b.0)));
    let mut out = Verdict {
        slug: None,
        best: None,
        score: 0.0,
        second: None,
        second_score: 0.0,
        ambiguous: false,
        twin: false,
        reason: "nessuno",
    };
    let Some((best, score)) = ranked.first().copied() else {
        return out;
    };
    out.best = Some(best.clone());
    out.score = score;
    if let Some((second, second_score)) = ranked.get(1).copied() {
        out.second = Some(second.clone());
        out.second_score = second_score;
        out.twin = twins.contains(&pair(best, second));
    }
    if score < thresholds.get(best).copied().unwrap_or(rules.base) {
        out.reason = "sotto soglia";
        return out;
    }
    let mut chosen = best.clone();
    if let Some(second) = out.second.clone() {
        let same_person = shadows.get(&second) == Some(best) || shadows.get(best) == Some(&second);
        if same_person {
            if shadows.get(best) == Some(&second) {
                chosen = second;
            }
        } else {
            let needed = if out.twin {
                rules.twin_margin
            } else {
                rules.margin
            };
            if out.second_score >= rules.base * 0.8 && score - out.second_score < needed {
                out.ambiguous = true;
                out.reason = "troppo simile a un'altra persona";
                return out;
            }
        }
    }
    if conflict {
        out.ambiguous = true;
        out.reason = "volto visibile e infrarosso non concordano";
        return out;
    }
    out.slug = Some(chosen);
    out.reason = "ok";
    out
}
