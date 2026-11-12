use std::collections::{BTreeMap, BTreeSet};

use crate::decide::{Pair, Rules, Verdict, decide, fuse, pair};
use crate::marks::{Mark, distinctive, mean_signature, pair_scores};
use crate::threshold::{person_threshold, spread};
use crate::vector::{centroid, dot, score_against, unit};

pub const MARK_LIMIT: f32 = 0.025;
pub const MAX_MARKS: usize = 4;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Settings {
    pub base: f32,
    pub margin: f32,
    pub twin_margin: f32,
    pub twin_sim: f32,
    pub ir_weight: f32,
    pub shadow_sim: f32,
    pub learn_margin: f32,
    pub marks_margin: f32,
    pub adaptive: bool,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            base: 0.40,
            margin: 0.05,
            twin_margin: 0.12,
            twin_sim: 0.55,
            ir_weight: 0.35,
            shadow_sim: 0.62,
            learn_margin: 0.08,
            marks_margin: 0.015,
            adaptive: true,
        }
    }
}

impl Settings {
    #[must_use]
    pub fn sanitized(self) -> Self {
        let clamp =
            |v: f32, lo: f32, hi: f32, d: f32| if v.is_finite() { v.clamp(lo, hi) } else { d };
        let d = Self::default();
        Self {
            base: clamp(self.base, 0.2, 0.8, d.base),
            margin: clamp(self.margin, 0.0, 0.3, d.margin),
            twin_margin: clamp(self.twin_margin, 0.0, 0.4, d.twin_margin),
            twin_sim: clamp(self.twin_sim, 0.3, 0.95, d.twin_sim),
            ir_weight: clamp(self.ir_weight, 0.0, 1.0, d.ir_weight),
            shadow_sim: clamp(self.shadow_sim, 0.5, 0.99, d.shadow_sim),
            learn_margin: clamp(self.learn_margin, 0.0, 0.3, d.learn_margin),
            marks_margin: clamp(self.marks_margin, 0.001, 0.3, d.marks_margin),
            adaptive: self.adaptive,
        }
    }

    const fn rules(&self) -> Rules {
        Rules {
            base: self.base,
            margin: self.margin,
            twin_margin: self.twin_margin,
        }
    }
}

#[derive(Debug, Clone)]
pub struct Entry {
    pub slug: String,
    pub rows: Vec<Vec<f32>>,
    pub ir: Option<Vec<Vec<f32>>>,
    pub marks: Option<Vec<Vec<f32>>>,
    pub auto: bool,
}

#[derive(Debug, Clone)]
struct Person {
    rows: Vec<Vec<f32>>,
    ir: Option<Vec<Vec<f32>>>,
    auto: bool,
    centroid: Vec<f32>,
    threshold: f32,
    threshold_ir: f32,
    spread: Option<f32>,
    marks: Option<Vec<f32>>,
    distinctive: Vec<Mark>,
    marks_count: usize,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Report {
    pub slug: String,
    pub threshold: f32,
    pub threshold_ir: f32,
    pub spread: Option<f32>,
    pub similar: Vec<(String, f32)>,
    pub shadow_of: Option<String>,
    pub marks: Vec<Mark>,
    pub marks_samples: usize,
}

#[derive(Debug, Clone)]
pub struct FaceBook {
    dim: usize,
    settings: Settings,
    people: BTreeMap<String, Person>,
    twins: BTreeSet<Pair>,
    shadows: BTreeMap<String, String>,
    similarity: BTreeMap<Pair, f32>,
}

impl FaceBook {
    #[must_use]
    pub fn new(dim: usize, settings: Settings) -> Self {
        Self {
            dim,
            settings: settings.sanitized(),
            people: BTreeMap::new(),
            twins: BTreeSet::new(),
            shadows: BTreeMap::new(),
            similarity: BTreeMap::new(),
        }
    }

    #[must_use]
    pub const fn dim(&self) -> usize {
        self.dim
    }

    #[must_use]
    pub const fn settings(&self) -> Settings {
        self.settings
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.people.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.people.is_empty()
    }

    pub fn replace(&mut self, entries: Vec<Entry>) {
        let s = self.settings;
        let dim = self.dim;
        let threshold = |rows: &[Vec<f32>]| {
            if s.adaptive {
                person_threshold(rows, dim, s.base)
            } else {
                s.base
            }
        };
        let people: BTreeMap<String, Person> = entries
            .into_iter()
            .filter(|e| !e.rows.is_empty())
            .map(|e| {
                let person = Person {
                    centroid: centroid(&e.rows, dim),
                    threshold: threshold(&e.rows),
                    threshold_ir: e
                        .ir
                        .as_deref()
                        .filter(|r| !r.is_empty())
                        .map_or(s.base, threshold),
                    spread: spread(&e.rows, dim),
                    marks: e.marks.as_deref().and_then(mean_signature),
                    distinctive: e
                        .marks
                        .as_deref()
                        .map(|m| distinctive(m, MARK_LIMIT, MAX_MARKS))
                        .unwrap_or_default(),
                    marks_count: e.marks.as_ref().map_or(0, Vec::len),
                    rows: e.rows,
                    ir: e.ir.filter(|r| !r.is_empty()),
                    auto: e.auto,
                };
                (e.slug, person)
            })
            .collect();
        let mut similarity = BTreeMap::new();
        let keys: Vec<&String> = people.keys().collect();
        for (i, a) in keys.iter().enumerate() {
            for b in keys.iter().skip(i.saturating_add(1)) {
                if let (Some(pa), Some(pb)) = (people.get(*a), people.get(*b)) {
                    similarity.insert(pair(a, b), dot(&pa.centroid, &pb.centroid));
                }
            }
        }
        let twins = similarity
            .iter()
            .filter(|(_, v)| **v >= s.twin_sim)
            .map(|(k, _)| k.clone())
            .collect();
        self.shadows = Self::find_shadows(&people, &similarity, s.shadow_sim);
        self.people = people;
        self.twins = twins;
        self.similarity = similarity;
    }

    fn find_shadows(
        people: &BTreeMap<String, Person>,
        similarity: &BTreeMap<Pair, f32>,
        limit: f32,
    ) -> BTreeMap<String, String> {
        let mut out = BTreeMap::new();
        for (slug, person) in people.iter().filter(|(_, p)| p.auto) {
            let host = people
                .iter()
                .filter(|(other, p)| !p.auto && *other != slug)
                .filter_map(|(other, p)| {
                    let sim = similarity.get(&pair(slug, other)).copied()?;
                    let agree = person
                        .rows
                        .iter()
                        .filter(|r| score_against(&p.rows, r) >= p.threshold)
                        .count();
                    let enough = agree.saturating_mul(5) >= person.rows.len().saturating_mul(4);
                    (sim >= limit && enough).then_some((other, sim))
                })
                .max_by(|a, b| a.1.total_cmp(&b.1));
            if let Some((host, _)) = host {
                out.insert(slug.clone(), host.clone());
            }
        }
        out
    }

    #[must_use]
    pub fn scores(
        &self,
        feature: &[f32],
        ir: Option<&[f32]>,
    ) -> (BTreeMap<String, f32>, Option<BTreeMap<String, f32>>) {
        let rgb = self
            .people
            .iter()
            .map(|(k, p)| (k.clone(), score_against(&p.rows, feature)))
            .collect();
        let ir = ir.map(|probe| {
            self.people
                .iter()
                .filter_map(|(k, p)| {
                    p.ir.as_ref()
                        .map(|rows| (k.clone(), score_against(rows, probe)))
                })
                .collect::<BTreeMap<_, _>>()
        });
        (rgb, ir.filter(|m| !m.is_empty()))
    }

    #[must_use]
    pub fn verdict(&self, feature: &[f32], ir: Option<&[f32]>) -> Verdict {
        let (rgb, irs) = self.scores(feature, ir);
        let s = self.settings;
        let (fused, conflict) = fuse(&rgb, irs.as_ref(), s.ir_weight, s.base);
        let limits = self
            .people
            .iter()
            .map(|(k, p)| (k.clone(), p.threshold))
            .collect();
        decide(
            &fused,
            &limits,
            s.rules(),
            &self.twins,
            &self.shadows,
            conflict,
        )
    }

    #[must_use]
    pub fn verdict_with_marks(
        &self,
        feature: &[f32],
        ir: Option<&[f32]>,
        probe: Option<&[f32]>,
    ) -> Verdict {
        let mut v = self.verdict(feature, ir);
        if !(v.ambiguous && v.twin) {
            return v;
        }
        let (Some(probe), Some(best), Some(second)) = (probe, v.best.clone(), v.second.clone())
        else {
            return v;
        };
        let (Some(ma), Some(mb)) = (
            self.people.get(&best).and_then(|p| p.marks.as_deref()),
            self.people.get(&second).and_then(|p| p.marks.as_deref()),
        ) else {
            return v;
        };
        let (sa, sb) = pair_scores(probe, ma, mb);
        if (sa - sb).abs() >= self.settings.marks_margin {
            v.slug = Some(if sa > sb { best } else { second });
            v.ambiguous = false;
            v.reason = "segni particolari";
        }
        v
    }

    #[must_use]
    pub fn closest(&self, feature: &[f32]) -> (Option<String>, f32) {
        self.people
            .iter()
            .map(|(k, p)| (k, score_against(&p.rows, feature)))
            .fold((None, 0.0), |acc, (k, v)| {
                if v > acc.1 { (Some(k.clone()), v) } else { acc }
            })
    }

    #[must_use]
    pub fn centroid_score(&self, slug: &str, feature: &[f32]) -> Option<f32> {
        self.people
            .get(slug)
            .map(|p| dot(&p.centroid, &unit(feature)))
    }

    #[must_use]
    pub fn may_learn(&self, slug: &str, feature: &[f32], ir: Option<&[f32]>) -> bool {
        let v = self.verdict(feature, ir);
        if v.slug.as_deref() != Some(slug) {
            return false;
        }
        if v.twin
            && self
                .shadows
                .get(v.second.as_deref().unwrap_or_default())
                .map(String::as_str)
                != Some(slug)
        {
            return v.score - v.second_score >= self.settings.twin_margin;
        }
        let limit = self
            .people
            .get(slug)
            .map_or(self.settings.base, |p| p.threshold);
        v.score >= limit + self.settings.learn_margin
    }

    #[must_use]
    pub fn shadows(&self) -> Vec<(String, String, f32)> {
        self.shadows
            .iter()
            .map(|(g, h)| {
                (
                    g.clone(),
                    h.clone(),
                    self.similarity.get(&pair(g, h)).copied().unwrap_or(0.0),
                )
            })
            .collect()
    }

    #[must_use]
    pub fn twins(&self) -> Vec<(String, String, f32)> {
        self.twins
            .iter()
            .map(|p| {
                (
                    p.0.clone(),
                    p.1.clone(),
                    self.similarity.get(p).copied().unwrap_or(0.0),
                )
            })
            .collect()
    }

    #[must_use]
    pub fn report(&self) -> Vec<Report> {
        self.people
            .iter()
            .map(|(slug, p)| Report {
                slug: slug.clone(),
                threshold: p.threshold,
                threshold_ir: p.threshold_ir,
                spread: p.spread,
                similar: self
                    .twins
                    .iter()
                    .filter_map(|t| {
                        let other = if &t.0 == slug {
                            &t.1
                        } else if &t.1 == slug {
                            &t.0
                        } else {
                            return None;
                        };
                        Some((
                            other.clone(),
                            self.similarity.get(t).copied().unwrap_or(0.0),
                        ))
                    })
                    .collect(),
                shadow_of: self.shadows.get(slug).cloned(),
                marks: p.distinctive.clone(),
                marks_samples: p.marks_count,
            })
            .collect()
    }
}
