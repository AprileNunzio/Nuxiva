use std::collections::BTreeSet;

use crate::fuzzy::{root_similarity, similarity};
use crate::inventory::{Index, IndexedEntity};
use crate::lexicon::{ACTION_ROOTS, Action, PHRASAL, QUANTIFIERS, WHOLE_HOME, plural_word};
use crate::text::Token;

pub const ACTION_FLOOR: f64 = 0.8;
pub const STEM_FLOOR: f64 = 0.75;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ActionHit {
    pub action: Action,
    pub sure: f64,
    pub index: usize,
}

#[derive(Debug, Clone, Default, PartialEq)]
pub struct DomainHits {
    pub domains: Vec<String>,
    pub sure: f64,
    pub used: BTreeSet<usize>,
    pub plural: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub struct AreaHit {
    pub ids: Vec<String>,
    pub sure: f64,
    pub partial: bool,
    pub used: BTreeSet<usize>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct NameHit {
    pub score: f64,
    pub distinct: bool,
    pub names_area: bool,
    pub used: BTreeSet<usize>,
}

fn better(candidate: ActionHit, current: Option<ActionHit>) -> bool {
    current.is_none_or(|c| {
        candidate.index < c.index || (candidate.index == c.index && candidate.sure > c.sure)
    })
}

#[must_use]
pub fn action(words: &[String]) -> Option<ActionHit> {
    let mut best: Option<ActionHit> = None;
    for (index, pair) in words.windows(2).enumerate() {
        if let [a, b] = pair {
            if let Some((_, _, act)) = PHRASAL.iter().find(|(x, y, _)| x == a && y == b) {
                let hit = ActionHit {
                    action: *act,
                    sure: 1.0,
                    index,
                };
                if better(hit, best) {
                    best = Some(hit);
                }
            }
        }
    }
    for (index, word) in words.iter().enumerate() {
        for (act, roots) in ACTION_ROOTS {
            let sure = roots
                .iter()
                .map(|r| root_similarity(word, r))
                .fold(0.0, f64::max);
            let hit = ActionHit {
                action: *act,
                sure,
                index,
            };
            if sure >= ACTION_FLOOR && better(hit, best) {
                best = Some(hit);
            }
        }
    }
    best
}

#[must_use]
pub fn domains(index: &Index, tokens: &[Token], skip: &BTreeSet<usize>) -> DomainHits {
    let mut hits = DomainHits {
        sure: 1.0,
        ..DomainHits::default()
    };
    for t in tokens.iter().filter(|t| !skip.contains(&t.index)) {
        let found = index
            .domain_stems
            .iter()
            .map(|(d, s)| (d, similarity(&t.stem, s)))
            .filter(|(_, sim)| *sim >= STEM_FLOOR)
            .fold(None::<(&String, f64)>, |acc, (d, sim)| match acc {
                Some((_, best)) if best >= sim => acc,
                _ => Some((d, sim)),
            });
        if let Some((d, sim)) = found {
            if !hits.domains.contains(d) {
                hits.domains.push(d.clone());
            }
            hits.sure = hits.sure.min(sim);
            hits.used.insert(t.index);
            hits.plural = hits.plural || plural_word(&t.word);
        }
    }
    hits
}

#[must_use]
pub fn quantified(words: &[String], normalized: &str) -> (bool, bool, BTreeSet<usize>) {
    let padded = format!(" {normalized} ");
    let whole = WHOLE_HOME
        .iter()
        .any(|p| padded.contains(&format!(" {p} ")));
    let used: BTreeSet<usize> = words
        .iter()
        .enumerate()
        .filter(|(_, w)| {
            QUANTIFIERS.contains(&w.as_str())
                || matches!(
                    w.as_str(),
                    "casa" | "stanze" | "ovunque" | "dappertutto" | "everywhere" | "house" | "home"
                )
        })
        .map(|(i, _)| i)
        .collect();
    let quantifier = words.iter().any(|w| QUANTIFIERS.contains(&w.as_str()));
    (whole, quantifier, used)
}

fn align(
    phrase: &[String],
    tokens: &[Token],
    skip: &BTreeSet<usize>,
) -> (Vec<f64>, BTreeSet<usize>) {
    let mut used = BTreeSet::new();
    let sims = phrase
        .iter()
        .map(|p| {
            let best = tokens
                .iter()
                .filter(|t| !skip.contains(&t.index) && !used.contains(&t.index))
                .map(|t| (t.index, similarity(&t.stem, p)))
                .filter(|(_, s)| *s >= STEM_FLOOR)
                .fold(None::<(usize, f64)>, |acc, cur| match acc {
                    Some(a) if a.1 >= cur.1 => Some(a),
                    _ => Some(cur),
                });
            if let Some((i, s)) = best {
                used.insert(i);
                s
            } else {
                0.0
            }
        })
        .collect();
    (sims, used)
}

fn mean(values: &[f64]) -> f64 {
    let n = f64::from(u32::try_from(values.len().max(1)).unwrap_or(u32::MAX));
    values.iter().sum::<f64>() / n
}

#[must_use]
pub fn areas(index: &Index, tokens: &[Token], skip: &BTreeSet<usize>) -> Option<AreaHit> {
    let mut ranked: Vec<(bool, usize, f64, String, BTreeSet<usize>)> = Vec::new();
    for area in &index.areas {
        let mut best: Option<(bool, usize, f64, BTreeSet<usize>)> = None;
        for phrase in &area.phrases {
            let (sims, used) = align(phrase, tokens, skip);
            let matched = sims.iter().filter(|s| **s > 0.0).count();
            let full = matched == phrase.len();
            let head = sims.first().is_some_and(|s| *s > 0.0);
            if matched == 0 || (!full && !head) {
                continue;
            }
            let hit = (full, matched, mean(&sims), used);
            let wins = best.as_ref().is_none_or(|b| {
                (hit.0, hit.1) > (b.0, b.1) || ((hit.0, hit.1) == (b.0, b.1) && hit.2 > b.2)
            });
            if wins {
                best = Some(hit);
            }
        }
        if let Some((full, matched, score, used)) = best {
            ranked.push((full, matched, score, area.id.clone(), used));
        }
    }
    let top = ranked.iter().map(|r| (r.0, r.1)).max()?;
    let peak = ranked
        .iter()
        .filter(|r| (r.0, r.1) == top)
        .map(|r| r.2)
        .fold(0.0, f64::max);
    let chosen: Vec<_> = ranked
        .into_iter()
        .filter(|r| (r.0, r.1) == top && r.2 >= peak - 0.05)
        .collect();
    let used = chosen.iter().flat_map(|r| r.4.iter().copied()).collect();
    Some(AreaHit {
        ids: chosen.iter().map(|r| r.3.clone()).collect(),
        sure: peak,
        partial: !top.0,
        used,
    })
}

#[must_use]
pub fn name(
    index: &Index,
    entity: &IndexedEntity,
    tokens: &[Token],
    skip: &BTreeSet<usize>,
    areas: &[String],
) -> NameHit {
    let mut best = NameHit {
        score: 0.0,
        distinct: false,
        names_area: false,
        used: BTreeSet::new(),
    };
    let area_phrases: Vec<&Vec<String>> = index
        .areas
        .iter()
        .filter(|a| areas.contains(&a.id))
        .flat_map(|a| a.phrases.iter())
        .collect();
    for phrase in &entity.phrases {
        let (sims, used) = align(phrase, tokens, skip);
        let (mut got, mut total, mut distinct_total, mut distinct_hit) =
            (0.0, 0.0, 0_usize, 0_usize);
        for (stem, sim) in phrase.iter().zip(&sims) {
            let w = index.weight(stem);
            total += w;
            got += w * sim;
            let distinct = !index.generic.contains(stem)
                && !index.area_stems.contains(stem)
                && !stem.chars().all(|c| c.is_ascii_digit());
            if distinct {
                distinct_total = distinct_total.saturating_add(1);
                if *sim > 0.0 {
                    distinct_hit = distinct_hit.saturating_add(1);
                }
            }
        }
        let score = if total > 0.0 { got / total } else { 0.0 };
        let distinct = distinct_total > 0
            && (distinct_hit == distinct_total
                || (distinct_total >= 2 && distinct_hit.saturating_mul(2) >= distinct_total));
        let names_area = area_phrases
            .iter()
            .any(|ap| ap.iter().all(|s| phrase.contains(s)));
        let candidate = NameHit {
            score,
            distinct,
            names_area,
            used,
        };
        let wins = (candidate.distinct, candidate.score) > (best.distinct, best.score);
        best.names_area = best.names_area || names_area;
        if wins {
            let keep = best.names_area;
            best = candidate;
            best.names_area = best.names_area || keep;
        }
    }
    best
}
