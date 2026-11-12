use std::collections::{BTreeMap, BTreeSet};

pub const MAX_DIM: usize = 1024;
pub const MAX_ROWS: usize = 64;
pub const MAX_PEOPLE: usize = 256;
const TOP_K: usize = 3;
const CENTROID_SHARE: f32 = 0.5;
const MIN_FOR_STATS: usize = 6;
const FLOOR_DELTA: f32 = 0.08;
const GENUINE_SLACK: f32 = 0.06;
const GENUINE_PERCENTILE: f32 = 0.10;
const SECOND_SHARE: f32 = 0.8;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct VoicePolicy {
    pub base: f32,
    pub margin: f32,
    pub twin_margin: f32,
    pub twin_similarity: f32,
    pub adaptive: bool,
}

impl Default for VoicePolicy {
    fn default() -> Self {
        Self {
            base: 0.62,
            margin: 0.06,
            twin_margin: 0.12,
            twin_similarity: 0.5,
            adaptive: true,
        }
    }
}

impl VoicePolicy {
    #[must_use]
    pub fn sanitized(self) -> Self {
        let pick =
            |v: f32, lo: f32, hi: f32, d: f32| if v.is_finite() { v.clamp(lo, hi) } else { d };
        Self {
            base: pick(self.base, 0.3, 0.95, 0.62),
            margin: pick(self.margin, 0.0, 0.5, 0.06),
            twin_margin: pick(self.twin_margin, 0.0, 0.6, 0.12),
            twin_similarity: pick(self.twin_similarity, 0.2, 0.95, 0.5),
            adaptive: self.adaptive,
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Verdict {
    pub slug: Option<String>,
    pub best: Option<String>,
    pub score: f32,
    pub second: Option<String>,
    pub second_score: f32,
    pub ambiguous: bool,
    pub reason: &'static str,
}

#[derive(Debug, Clone)]
struct Person {
    rows: Vec<Vec<f32>>,
    centre: Vec<f32>,
    limit: f32,
}

#[must_use]
pub fn unit(v: &[f32]) -> Vec<f32> {
    let norm = v.iter().map(|x| x * x).sum::<f32>().sqrt().max(1e-9);
    v.iter().map(|x| x / norm).collect()
}

#[must_use]
pub fn dot(a: &[f32], b: &[f32]) -> f32 {
    a.iter().zip(b).map(|(x, y)| x * y).sum()
}

fn centroid(rows: &[Vec<f32>], dim: usize) -> Vec<f32> {
    let mut sum = vec![0.0_f32; dim];
    for row in rows {
        for (s, v) in sum.iter_mut().zip(row) {
            *s += v;
        }
    }
    #[allow(clippy::cast_precision_loss)]
    let count = rows.len().max(1) as f32;
    unit(&sum.iter().map(|v| v / count).collect::<Vec<_>>())
}

fn leave_one_out(rows: &[Vec<f32>], dim: usize) -> Vec<f32> {
    let mut sum = vec![0.0_f32; dim];
    for row in rows {
        for (s, v) in sum.iter_mut().zip(row) {
            *s += v;
        }
    }
    rows.iter()
        .map(|row| {
            let rest: Vec<f32> = sum.iter().zip(row).map(|(s, v)| s - v).collect();
            dot(row, &unit(&rest))
        })
        .collect()
}

fn threshold(rows: &[Vec<f32>], base: f32) -> f32 {
    if rows.len() < MIN_FOR_STATS {
        return base;
    }
    let dim = rows.first().map_or(0, Vec::len);
    let mut sims = leave_one_out(rows, dim);
    sims.sort_by(f32::total_cmp);
    #[allow(
        clippy::cast_precision_loss,
        clippy::cast_possible_truncation,
        clippy::cast_sign_loss
    )]
    let index = ((sims.len().saturating_sub(1)) as f32 * GENUINE_PERCENTILE).floor() as usize;
    let low = sims.get(index).copied().unwrap_or(base);
    (low - GENUINE_SLACK).max(base - FLOOR_DELTA).min(base)
}

fn person_score(person: &Person, probe: &[f32]) -> f32 {
    let mut sims: Vec<f32> = person.rows.iter().map(|r| dot(r, probe)).collect();
    sims.sort_by(|a, b| b.total_cmp(a));
    let top: Vec<f32> = sims.into_iter().take(TOP_K).collect();
    #[allow(clippy::cast_precision_loss)]
    let mean = top.iter().sum::<f32>() / top.len().max(1) as f32;
    CENTROID_SHARE * dot(&person.centre, probe) + (1.0 - CENTROID_SHARE) * mean
}

#[must_use]
pub fn valid_slug(slug: &str) -> bool {
    let bytes = slug.as_bytes();
    let Some(first) = bytes.first() else {
        return false;
    };
    bytes.len() <= 41
        && (first.is_ascii_lowercase() || first.is_ascii_digit())
        && bytes
            .iter()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || *b == b'-')
}

#[derive(Debug, Clone, Default)]
pub struct VoiceBook {
    policy: VoicePolicy,
    dim: Option<usize>,
    people: BTreeMap<String, Person>,
    twins: BTreeSet<(String, String)>,
}

impl VoiceBook {
    #[must_use]
    pub fn new(policy: VoicePolicy) -> Self {
        Self {
            policy: policy.sanitized(),
            ..Self::default()
        }
    }

    #[must_use]
    pub fn policy(&self) -> VoicePolicy {
        self.policy
    }

    pub fn set_policy(&mut self, policy: VoicePolicy) {
        self.policy = policy.sanitized();
        let base = self.policy.base;
        let adaptive = self.policy.adaptive;
        for person in self.people.values_mut() {
            person.limit = if adaptive {
                threshold(&person.rows, base)
            } else {
                base
            };
        }
        self.refresh_twins();
    }

    fn refresh_twins(&mut self) {
        let keys: Vec<&String> = self.people.keys().collect();
        let mut twins = BTreeSet::new();
        for (i, a) in keys.iter().enumerate() {
            for b in keys.iter().skip(i.saturating_add(1)) {
                let (Some(pa), Some(pb)) = (self.people.get(*a), self.people.get(*b)) else {
                    continue;
                };
                if dot(&pa.centre, &pb.centre) >= self.policy.twin_similarity {
                    twins.insert(((*a).clone(), (*b).clone()));
                }
            }
        }
        self.twins = twins;
    }

    fn twin(&self, a: &str, b: &str) -> bool {
        let key = if a <= b {
            (a.to_owned(), b.to_owned())
        } else {
            (b.to_owned(), a.to_owned())
        };
        self.twins.contains(&key)
    }

    pub fn set_person(&mut self, slug: &str, rows: &[Vec<f32>]) -> bool {
        let Some(first) = rows.first() else {
            return false;
        };
        let dim = first.len();
        if !valid_slug(slug)
            || dim == 0
            || dim > MAX_DIM
            || rows.len() > MAX_ROWS
            || self.dim.is_some_and(|d| d != dim)
            || rows
                .iter()
                .any(|r| r.len() != dim || r.iter().any(|v| !v.is_finite()))
            || (!self.people.contains_key(slug) && self.people.len() >= MAX_PEOPLE)
        {
            return false;
        }
        let unit_rows: Vec<Vec<f32>> = rows.iter().map(|r| unit(r)).collect();
        let centre = centroid(&unit_rows, dim);
        let limit = if self.policy.adaptive {
            threshold(&unit_rows, self.policy.base)
        } else {
            self.policy.base
        };
        self.dim = Some(dim);
        self.people.insert(
            slug.to_owned(),
            Person {
                rows: unit_rows,
                centre,
                limit,
            },
        );
        self.refresh_twins();
        true
    }

    pub fn remove(&mut self, slug: &str) {
        self.people.remove(slug);
        if self.people.is_empty() {
            self.dim = None;
        }
        self.refresh_twins();
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.people.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.people.is_empty()
    }

    #[must_use]
    pub fn limit(&self, slug: &str) -> Option<f32> {
        self.people.get(slug).map(|p| p.limit)
    }

    #[must_use]
    pub fn twins(&self) -> Vec<(String, String)> {
        self.twins.iter().cloned().collect()
    }

    #[must_use]
    pub fn scores(&self, probe: &[f32]) -> Vec<(String, f32)> {
        if self.dim != Some(probe.len()) || probe.iter().any(|v| !v.is_finite()) {
            return Vec::new();
        }
        let probe = unit(probe);
        self.people
            .iter()
            .map(|(slug, p)| (slug.clone(), person_score(p, &probe)))
            .collect()
    }

    #[must_use]
    pub fn verdict(&self, probe: &[f32]) -> Verdict {
        let mut ranked = self.scores(probe);
        ranked.sort_by(|a, b| b.1.total_cmp(&a.1));
        let mut it = ranked.into_iter();
        let Some((best, score)) = it.next() else {
            return Verdict {
                slug: None,
                best: None,
                score: 0.0,
                second: None,
                second_score: 0.0,
                ambiguous: false,
                reason: "nessuno",
            };
        };
        let (second, second_score) = it.next().map_or((None, 0.0), |(s, v)| (Some(s), v));
        let mut out = Verdict {
            slug: None,
            best: Some(best.clone()),
            score,
            second: second.clone(),
            second_score,
            ambiguous: false,
            reason: "",
        };
        if score < self.limit(&best).unwrap_or(self.policy.base) {
            out.reason = "sotto soglia";
            return out;
        }
        if let Some(other) = second.as_deref() {
            let needed = if self.twin(&best, other) {
                self.policy.twin_margin
            } else {
                self.policy.margin
            };
            if second_score >= self.policy.base * SECOND_SHARE && score - second_score < needed {
                out.ambiguous = true;
                out.reason = "troppo simile a un'altra persona";
                return out;
            }
        }
        out.slug = Some(best);
        out.reason = "ok";
        out
    }
}
