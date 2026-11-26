use std::collections::{BTreeMap, BTreeSet};

use serde::Deserialize;

use crate::error::{ResolveError, ResolveResult};
use crate::lexicon::{AREA_GROUPS, DOMAIN_WORDS};
use crate::text::{phrase, stem};

pub const MAX_AREAS: usize = 512;
pub const MAX_ENTITIES: usize = 8_192;
pub const MAX_NAMES: usize = 32;
pub const MAX_NAME_BYTES: usize = 200;
pub const MAX_INVENTORY_BYTES: usize = 8 * 1024 * 1024;

#[derive(Debug, Clone, Deserialize)]
pub struct Area {
    pub id: String,
    pub name: String,
    #[serde(default)]
    pub aliases: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Entity {
    pub id: String,
    pub domain: String,
    pub name: String,
    #[serde(default)]
    pub aliases: Vec<String>,
    #[serde(default)]
    pub area: Option<String>,
    #[serde(default)]
    pub device: Option<String>,
    #[serde(default)]
    pub group: bool,
    #[serde(default)]
    pub as_light: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Inventory {
    #[serde(default)]
    pub areas: Vec<Area>,
    #[serde(default)]
    pub entities: Vec<Entity>,
}

#[derive(Debug, Clone)]
pub struct IndexedArea {
    pub id: String,
    pub name: String,
    pub phrases: Vec<Vec<String>>,
}

#[derive(Debug, Clone)]
pub struct IndexedEntity {
    pub entity: Entity,
    pub phrases: Vec<Vec<String>>,
}

#[derive(Debug, Clone)]
pub struct Index {
    pub areas: Vec<IndexedArea>,
    pub entities: Vec<IndexedEntity>,
    pub generic: BTreeSet<String>,
    pub domain_stems: Vec<(String, String)>,
    pub area_stems: BTreeSet<String>,
    weights: BTreeMap<String, f64>,
}

fn bounded(name: &str) -> ResolveResult<()> {
    if name.len() > MAX_NAME_BYTES {
        return Err(ResolveError::TooLarge("name"));
    }
    Ok(())
}

fn check(inv: &Inventory) -> ResolveResult<()> {
    if inv.areas.len() > MAX_AREAS {
        return Err(ResolveError::TooLarge("areas"));
    }
    if inv.entities.len() > MAX_ENTITIES {
        return Err(ResolveError::TooLarge("entities"));
    }
    for a in &inv.areas {
        if a.aliases.len() > MAX_NAMES {
            return Err(ResolveError::TooLarge("aliases"));
        }
        bounded(&a.id)?;
        bounded(&a.name)?;
        a.aliases.iter().try_for_each(|x| bounded(x))?;
    }
    for e in &inv.entities {
        if e.aliases.len() > MAX_NAMES {
            return Err(ResolveError::TooLarge("aliases"));
        }
        bounded(&e.id)?;
        bounded(&e.name)?;
        bounded(&e.domain)?;
        e.aliases.iter().try_for_each(|x| bounded(x))?;
        if !e.id.starts_with(&format!("{}.", e.domain)) {
            return Err(ResolveError::Invalid(format!(
                "entity {} outside its domain",
                e.id
            )));
        }
    }
    Ok(())
}

fn contains(haystack: &[String], needle: &[String]) -> bool {
    !needle.is_empty() && needle.iter().all(|n| haystack.contains(n))
}

fn area_phrases(area: &Area, others: &[Vec<String>]) -> Vec<Vec<String>> {
    let own = phrase(&area.name);
    let mut out: BTreeSet<Vec<String>> = std::iter::once(own.clone())
        .chain(area.aliases.iter().map(|a| phrase(a)))
        .filter(|p| !p.is_empty())
        .collect();
    let fit = |group: &[&str]| {
        group
            .iter()
            .map(|g| phrase(g))
            .filter(|m| contains(&own, m))
            .map(|m| m.len())
            .max()
            .unwrap_or(0)
    };
    let best = AREA_GROUPS.iter().map(|g| fit(g)).max().unwrap_or(0);
    for group in AREA_GROUPS.iter().filter(|g| best > 0 && fit(g) == best) {
        for m in group.iter().map(|g| phrase(g)) {
            if !others.iter().any(|o| contains(o, &m)) {
                out.insert(m);
            }
        }
    }
    out.into_iter().collect()
}

fn ratio(a: usize, b: usize) -> f64 {
    let a = f64::from(u32::try_from(a).unwrap_or(u32::MAX));
    let b = f64::from(u32::try_from(b.max(1)).unwrap_or(u32::MAX));
    a / b
}

impl Index {
    pub fn build(inv: Inventory) -> ResolveResult<Self> {
        check(&inv)?;
        let names: Vec<Vec<String>> = inv.areas.iter().map(|a| phrase(&a.name)).collect();
        let areas: Vec<IndexedArea> = inv
            .areas
            .iter()
            .enumerate()
            .map(|(i, a)| {
                let others: Vec<Vec<String>> = names
                    .iter()
                    .enumerate()
                    .filter(|(j, _)| *j != i)
                    .map(|(_, p)| p.clone())
                    .collect();
                IndexedArea {
                    id: a.id.clone(),
                    name: a.name.clone(),
                    phrases: area_phrases(a, &others),
                }
            })
            .collect();
        let entities: Vec<IndexedEntity> = inv
            .entities
            .into_iter()
            .map(|e| {
                let phrases: BTreeSet<Vec<String>> = std::iter::once(phrase(&e.name))
                    .chain(e.aliases.iter().map(|a| phrase(a)))
                    .filter(|p| !p.is_empty())
                    .collect();
                IndexedEntity {
                    entity: e,
                    phrases: phrases.into_iter().collect(),
                }
            })
            .collect();
        let mut df: BTreeMap<String, usize> = BTreeMap::new();
        for e in &entities {
            let seen: BTreeSet<&String> = e.phrases.iter().flatten().collect();
            for s in seen {
                let slot = df.entry(s.clone()).or_insert(0);
                *slot = slot.saturating_add(1);
            }
        }
        let total = entities.len().max(1);
        let weights = df
            .into_iter()
            .map(|(s, n)| (s, (1.0 + ratio(total, n)).ln().max(0.1)))
            .collect();
        let generic = DOMAIN_WORDS
            .iter()
            .flat_map(|(_, generic, _)| generic.iter().map(|w| stem(w)))
            .collect();
        let domain_stems = DOMAIN_WORDS
            .iter()
            .flat_map(|(d, generic, specific)| {
                generic
                    .iter()
                    .chain(specific.iter())
                    .map(move |w| ((*d).to_owned(), stem(w)))
            })
            .collect();
        let area_stems = areas
            .iter()
            .flat_map(|a| a.phrases.iter().flatten().cloned())
            .collect();
        Ok(Self {
            areas,
            entities,
            generic,
            domain_stems,
            area_stems,
            weights,
        })
    }

    #[must_use]
    pub fn weight(&self, stem: &str) -> f64 {
        self.weights.get(stem).copied().unwrap_or(1.0)
    }

    #[must_use]
    pub fn area_name(&self, id: &str) -> Option<&str> {
        self.areas
            .iter()
            .find(|a| a.id == id)
            .map(|a| a.name.as_str())
    }
}
