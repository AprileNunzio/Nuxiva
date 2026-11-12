use serde::{Deserialize, Serialize};

pub const ENHANCE_SCORE: usize = 4;
pub const SIMILAR_SCORE: usize = 2;
pub const MAX_LISTED: usize = 5;
pub const MAX_HITS: usize = 256;

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Hit {
    pub id: String,
    pub score: usize,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Case {
    pub hits: Vec<Hit>,
    pub id_taken: bool,
    pub motive: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Verdict {
    pub action: &'static str,
    pub target: String,
    pub similar: Vec<Hit>,
    pub creatable: bool,
    pub reason: &'static str,
}

#[must_use]
pub fn decide(case: &Case) -> Verdict {
    let mut similar: Vec<Hit> = case
        .hits
        .iter()
        .take(MAX_HITS)
        .filter(|h| h.score >= SIMILAR_SCORE)
        .cloned()
        .collect();
    similar.sort_by(|a, b| b.score.cmp(&a.score).then_with(|| a.id.cmp(&b.id)));
    similar.truncate(MAX_LISTED);
    let top = similar.first().cloned();
    let (action, target, creatable, reason) = match top {
        _ if case.id_taken => ("potenzia", String::new(), false, "id_taken"),
        Some(hit) if hit.score >= ENHANCE_SCORE => ("potenzia", hit.id, false, "strong_match"),
        Some(hit) => ("verifica", hit.id, case.motive, "weak_match"),
        None => ("crea", String::new(), true, "no_match"),
    };
    Verdict {
        action,
        target,
        similar,
        creatable,
        reason,
    }
}

#[cfg(test)]
mod tests {
    use super::{Case, Hit, decide};

    fn hit(id: &str, score: usize) -> Hit {
        Hit {
            id: id.to_owned(),
            score,
        }
    }

    #[test]
    fn empty_catalog_allows_creation() {
        let v = decide(&Case::default());
        assert_eq!(
            (v.action, v.creatable, v.reason),
            ("crea", true, "no_match")
        );
    }

    #[test]
    fn strong_match_forces_enhancement() {
        let v = decide(&Case {
            hits: vec![hit("b", 2), hit("a", 5)],
            motive: true,
            ..Case::default()
        });
        assert_eq!(
            (v.action, v.target.as_str(), v.creatable),
            ("potenzia", "a", false)
        );
        assert_eq!(v.similar.first().map(|h| h.id.as_str()), Some("a"));
    }

    #[test]
    fn weak_match_needs_a_motive() {
        let weak = |motive| Case {
            hits: vec![hit("a", 3), hit("z", 1)],
            motive,
            ..Case::default()
        };
        assert!(!decide(&weak(false)).creatable);
        let v = decide(&weak(true));
        assert_eq!(
            (v.action, v.creatable, v.similar.len()),
            ("verifica", true, 1)
        );
    }

    #[test]
    fn taken_id_never_creates_and_ties_are_stable() {
        let v = decide(&Case {
            hits: vec![hit("b", 3), hit("a", 3)],
            id_taken: true,
            motive: true,
        });
        assert_eq!((v.action, v.creatable), ("potenzia", false));
        assert_eq!(v.similar.first().map(|h| h.id.as_str()), Some("a"));
    }

    #[test]
    fn list_is_capped() {
        let hits = (0..40).map(|i| hit(&format!("a{i:02}"), 3)).collect();
        assert_eq!(
            decide(&Case {
                hits,
                ..Case::default()
            })
            .similar
            .len(),
            5
        );
    }
}
