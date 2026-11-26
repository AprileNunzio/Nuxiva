use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

use crate::error::{ResolveError, ResolveResult};
use crate::inventory::{Index, IndexedEntity, Inventory};
use crate::lexicon::{Action, DEFER, NEUTRAL};
use crate::signals::{self, ActionHit, AreaHit, DomainHits};
use crate::text::{Token, content_tokens, normalize, words};

pub const MAX_TEXT_BYTES: usize = 600;
pub const EXECUTE: f64 = 0.75;
pub const CONFIRM: f64 = 0.5;
const PRIORITY: &[&str] = &[
    "light",
    "cover",
    "climate",
    "fan",
    "media_player",
    "switch",
    "lock",
    "valve",
    "humidifier",
    "input_boolean",
    "siren",
];

#[derive(Debug, Clone, Default, Deserialize)]
pub struct Request {
    pub text: String,
    #[serde(default)]
    pub here: Option<String>,
    #[serde(default)]
    pub fallback: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Decision {
    Execute,
    Confirm,
    Clarify,
    Missing,
    None,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Call {
    pub entity: String,
    pub action: &'static str,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Resolution {
    pub decision: Decision,
    pub action: Option<&'static str>,
    pub domains: Vec<String>,
    pub calls: Vec<Call>,
    pub areas: Vec<String>,
    pub rooms: Vec<String>,
    pub how: &'static str,
    pub confidence: f64,
    pub plural: bool,
}

impl Resolution {
    fn none() -> Self {
        Self {
            decision: Decision::None,
            action: None,
            domains: Vec::new(),
            calls: Vec::new(),
            areas: Vec::new(),
            rooms: Vec::new(),
            how: "",
            confidence: 0.0,
            plural: false,
        }
    }
}

#[derive(Debug, Clone)]
pub struct Resolver {
    index: Index,
}

struct Scene<'a> {
    tokens: Vec<Token>,
    act: ActionHit,
    domains: DomainHits,
    area: Option<AreaHit>,
    whole: bool,
    plural: bool,
    used: BTreeSet<usize>,
    verbs: BTreeSet<usize>,
    request: &'a Request,
}

struct Pick<'a> {
    chosen: Vec<&'a IndexedEntity>,
    sure: f64,
    how: &'static str,
}

fn priority(domain: &str) -> usize {
    PRIORITY
        .iter()
        .position(|d| *d == domain)
        .unwrap_or(PRIORITY.len())
}

fn in_areas(e: &IndexedEntity, ids: &[String]) -> bool {
    e.entity.area.as_ref().is_some_and(|a| ids.contains(a))
}

impl Resolver {
    pub fn new(inventory: Inventory) -> ResolveResult<Self> {
        Ok(Self {
            index: Index::build(inventory)?,
        })
    }

    pub fn from_json(raw: &str) -> ResolveResult<Self> {
        if raw.len() > crate::inventory::MAX_INVENTORY_BYTES {
            return Err(ResolveError::TooLarge("inventory"));
        }
        let inv: Inventory =
            serde_json::from_str(raw).map_err(|e| ResolveError::Invalid(e.to_string()))?;
        Self::new(inv)
    }

    pub fn resolve(&self, request: &Request) -> ResolveResult<Resolution> {
        if request.text.len() > MAX_TEXT_BYTES {
            return Err(ResolveError::TooLarge("text"));
        }
        let all = words(&request.text);
        let tokens = content_tokens(&request.text);
        if tokens.iter().any(|t| DEFER.contains(&t.word.as_str())) {
            return Ok(Resolution::none());
        }
        let Some(act) = signals::action(&all) else {
            return Ok(Resolution::none());
        };
        let mut used: BTreeSet<usize> = [
            act.index,
            act.index.saturating_add(usize::from(
                all.get(act.index.saturating_add(1))
                    .is_some_and(|w| w == "on" || w == "off"),
            )),
        ]
        .into();
        let verbs = used.clone();
        let domains = signals::domains(&self.index, &tokens, &used);
        used.extend(domains.used.iter().copied());
        let (whole, quantifier, quantified) = signals::quantified(&all, &normalize(&request.text));
        used.extend(quantified);
        let area = signals::areas(&self.index, &tokens, &used);
        if let Some(a) = &area {
            used.extend(a.used.iter().copied());
        }
        let whole = whole || (quantifier && area.is_none());
        let plural = domains.plural || quantifier || whole;
        let scene = Scene {
            tokens,
            act,
            domains,
            area,
            whole,
            plural,
            used,
            verbs,
            request,
        };
        Ok(self.decide(&scene))
    }

    fn pool(&self, scene: &Scene<'_>) -> Vec<&IndexedEntity> {
        let wanted = &scene.domains.domains;
        self.index
            .entities
            .iter()
            .filter(|e| {
                let d = e.entity.domain.as_str();
                let fits = wanted.is_empty()
                    || wanted.iter().any(|w| w == d)
                    || (e.entity.as_light && wanted.iter().any(|w| w == "light"));
                fits && scene.act.action.adapted(d).supports(d)
            })
            .collect()
    }

    fn named<'a>(
        &self,
        scene: &Scene<'_>,
        pool: &[&'a IndexedEntity],
        used: &mut BTreeSet<usize>,
    ) -> Option<Pick<'a>> {
        let area_ids = scene
            .area
            .as_ref()
            .map(|a| a.ids.clone())
            .unwrap_or_default();
        let scored: Vec<(&IndexedEntity, signals::NameHit)> = pool
            .iter()
            .map(|e| {
                (
                    *e,
                    signals::name(&self.index, e, &scene.tokens, &scene.verbs, &area_ids),
                )
            })
            .filter(|(_, h)| h.distinct && h.score >= 0.5)
            .collect();
        let scored: Vec<_> = if area_ids.is_empty() {
            scored
        } else {
            scored
                .into_iter()
                .filter(|(e, h)| in_areas(e, &area_ids) || h.names_area || e.entity.area.is_none())
                .collect()
        };
        let top = scored.iter().map(|(_, h)| h.score).fold(0.0, f64::max);
        if top <= 0.0 {
            return None;
        }
        let second = scored
            .iter()
            .map(|(_, h)| h.score)
            .filter(|s| *s < top - 0.02)
            .fold(0.0, f64::max);
        let chosen: Vec<_> = scored
            .iter()
            .filter(|(_, h)| h.score >= top - 0.02)
            .collect();
        for (_, h) in &chosen {
            used.extend(h.used.iter().copied());
        }
        let sure = if second > 0.6 {
            top * 0.85
        } else if second > 0.0 {
            top
        } else {
            0.5 + 0.5 * top
        };
        Some(Pick {
            chosen: chosen.into_iter().map(|(e, _)| *e).collect(),
            sure,
            how: "name",
        })
    }

    fn by_room<'a>(
        &self,
        scene: &Scene<'_>,
        pool: &[&'a IndexedEntity],
        area: &AreaHit,
    ) -> Pick<'a> {
        let named_room = |e: &&IndexedEntity| {
            in_areas(e, &area.ids)
                || (e.entity.area.is_none()
                    && signals::name(&self.index, e, &scene.tokens, &BTreeSet::new(), &area.ids)
                        .names_area)
        };
        let mut chosen: Vec<&IndexedEntity> = pool.iter().copied().filter(named_room).collect();
        let mut sure = area.sure * if area.partial { 0.75 } else { 1.0 };
        if scene.domains.domains.is_empty() {
            let best = chosen.iter().map(|e| priority(&e.entity.domain)).min();
            chosen.retain(|e| Some(priority(&e.entity.domain)) == best);
            sure *= 0.8;
        }
        Pick {
            chosen,
            sure,
            how: "area",
        }
    }

    fn by_context<'a>(
        &self,
        scene: &Scene<'_>,
        pool: &[&'a IndexedEntity],
    ) -> Result<Pick<'a>, Vec<String>> {
        if pool.is_empty() {
            return Ok(Pick {
                chosen: Vec::new(),
                sure: 0.0,
                how: "context",
            });
        }
        if scene.whole {
            return Ok(Pick {
                chosen: pool.to_vec(),
                sure: 0.95,
                how: "home",
            });
        }
        let places = [
            (scene.request.here.as_deref(), 0.9, "here"),
            (scene.request.fallback.as_deref(), 0.8, "default"),
        ];
        for (place, sure, how) in places {
            if let Some(id) = place {
                let chosen: Vec<_> = pool
                    .iter()
                    .copied()
                    .filter(|e| e.entity.area.as_deref() == Some(id))
                    .collect();
                if !chosen.is_empty() {
                    return Ok(Pick { chosen, sure, how });
                }
            }
        }
        if pool.len() == 1 {
            return Ok(Pick {
                chosen: pool.to_vec(),
                sure: 0.9,
                how: "single",
            });
        }
        if scene.plural {
            return Ok(Pick {
                chosen: pool.to_vec(),
                sure: 0.6,
                how: "home",
            });
        }
        let rooms: BTreeSet<String> = pool
            .iter()
            .filter_map(|e| {
                e.entity
                    .area
                    .as_deref()
                    .and_then(|a| self.index.area_name(a))
            })
            .map(str::to_owned)
            .collect();
        Err(rooms.into_iter().collect())
    }

    fn ask<'b>(&self, mut out: Resolution, areas: impl Iterator<Item = &'b str>) -> Resolution {
        let named: BTreeSet<String> = areas
            .filter_map(|a| self.index.area_name(a))
            .map(str::to_owned)
            .chain(out.rooms.drain(..))
            .collect();
        out.rooms = named.into_iter().collect();
        out.decision = Decision::Clarify;
        out.how = "ambiguous";
        out
    }

    fn decide(&self, scene: &Scene<'_>) -> Resolution {
        let pool = self.pool(scene);
        let mut used = scene.used.clone();
        let mut out = Resolution {
            action: Some(scene.act.action.key()),
            domains: scene.domains.domains.clone(),
            plural: scene.plural,
            ..Resolution::none()
        };
        out.areas = scene
            .area
            .as_ref()
            .map(|a| a.ids.clone())
            .unwrap_or_default();
        let pick = if let Some(p) = self.named(scene, &pool, &mut used) {
            p
        } else if let Some(area) = scene.area.as_ref().filter(|a| a.partial && a.ids.len() > 1) {
            return self.ask(out, area.ids.iter().map(String::as_str));
        } else if let Some(area) = &scene.area {
            self.by_room(scene, &pool, area)
        } else if scene.domains.domains.is_empty() {
            return out;
        } else {
            match self.by_context(scene, &pool) {
                Ok(p) => p,
                Err(rooms) => {
                    out.rooms = rooms;
                    return self.ask(out, std::iter::empty());
                }
            }
        };
        if pick.chosen.is_empty() {
            out.decision = Decision::Missing;
            out.rooms = out
                .areas
                .iter()
                .filter_map(|a| self.index.area_name(a))
                .map(str::to_owned)
                .collect();
            out.how = pick.how;
            return out;
        }
        let chosen = narrow(pick.chosen, scene.plural || scene.whole);
        let unexplained = scene
            .tokens
            .iter()
            .filter(|t| {
                !used.contains(&t.index)
                    && !NEUTRAL.contains(&t.word.as_str())
                    && !t.word.chars().all(|c| c.is_ascii_digit())
            })
            .count();
        if pick.how == "home" && !scene.whole && unexplained > 0 {
            return self.ask(out, chosen.iter().filter_map(|e| e.entity.area.as_deref()));
        }
        let penalty = (0.05 * f64::from(u32::try_from(unexplained).unwrap_or(u32::MAX))).min(0.2);
        let domain_sure = if scene.domains.domains.is_empty() {
            1.0
        } else {
            scene.domains.sure
        };
        out.confidence =
            (scene.act.sure * pick.sure * domain_sure * (1.0 - penalty)).clamp(0.0, 1.0);
        out.how = pick.how;
        out.calls = chosen
            .iter()
            .map(|e| Call {
                entity: e.entity.id.clone(),
                action: scene.act.action.adapted(&e.entity.domain).key(),
            })
            .collect();
        out.decision = if out.confidence >= EXECUTE {
            Decision::Execute
        } else if out.confidence >= CONFIRM {
            Decision::Confirm
        } else {
            Decision::None
        };
        out
    }
}

fn narrow(chosen: Vec<&IndexedEntity>, plural: bool) -> Vec<&IndexedEntity> {
    let chosen = if !plural && chosen.len() > 1 {
        match chosen.iter().find(|e| e.entity.group) {
            Some(g) => vec![*g],
            None => chosen,
        }
    } else {
        chosen
    };
    let mut best: BTreeMap<String, &IndexedEntity> = BTreeMap::new();
    for e in chosen {
        let key = e
            .entity
            .device
            .clone()
            .unwrap_or_else(|| e.entity.id.clone());
        let replace = best
            .get(&key)
            .is_none_or(|b| priority(&e.entity.domain) < priority(&b.entity.domain));
        if replace {
            best.insert(key, e);
        }
    }
    let mut out: Vec<&IndexedEntity> = best.into_values().collect();
    out.sort_by(|a, b| a.entity.id.cmp(&b.entity.id));
    out
}

#[must_use]
pub fn action_of(text: &str) -> Option<Action> {
    signals::action(&words(text)).map(|h| h.action)
}
