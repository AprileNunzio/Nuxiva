use serde::Serialize;

use crate::look::{Item, VehicleKind};
use crate::sighting::{Class, Sighting, Who};

pub const DELIVERY_MAX_MS: u64 = 10 * 60_000;
pub const VEHICLE_WINDOW_MS: u64 = 5 * 60_000;
pub const PARCEL_BEFORE_MS: u64 = 60_000;
pub const PARCEL_AFTER_MS: u64 = 3 * 60_000;
pub const HOME_WINDOW_MS: u64 = 2 * 60_000;
pub const STOP_MIN_MS: u64 = 60_000;
pub const DELIVERY_MIN: f32 = 0.45;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum EpisodeKind {
    Delivery,
    Visit,
    VehicleStop,
    ParcelLeft,
    MaskedPerson,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Episode {
    pub kind: EpisodeKind,
    pub start_ms: u64,
    pub end_ms: u64,
    pub camera: String,
    pub who: Who,
    pub sightings: Vec<String>,
    pub reasons: Vec<&'static str>,
    pub confidence: f32,
}

fn near(a: &Sighting, b: &Sighting, before: u64, after: u64) -> bool {
    b.end_ms.saturating_add(before) >= a.start_ms && b.start_ms <= a.end_ms.saturating_add(after)
}

const fn stranger(who: &Who) -> bool {
    !matches!(who, Who::Person(_))
}

fn episode(
    kind: EpisodeKind,
    s: &Sighting,
    extra: Vec<&Sighting>,
    reasons: Vec<&'static str>,
    confidence: f32,
) -> Episode {
    let mut ids = vec![s.id.clone()];
    let (mut start, mut end) = (s.start_ms, s.end_ms);
    for e in extra {
        ids.push(e.id.clone());
        start = start.min(e.start_ms);
        end = end.max(e.end_ms);
    }
    Episode {
        kind,
        start_ms: start,
        end_ms: end,
        camera: s.camera.clone(),
        who: s.who.clone(),
        sightings: ids,
        reasons,
        confidence: confidence.clamp(0.0, 0.95),
    }
}

fn delivery(p: &Sighting, all: &[Sighting]) -> Option<Episode> {
    if p.class != Class::Person
        || !stranger(&p.who)
        || p.end_ms.saturating_sub(p.start_ms) > DELIVERY_MAX_MS
    {
        return None;
    }
    let mut score = 0.0_f32;
    let mut reasons = Vec::new();
    let mut extra = Vec::new();
    if p.look.carrying.contains(&Item::Parcel) {
        score += 0.4;
        reasons.push("parcel_in_hand");
    }
    if p.look.hi_vis == Some(true) {
        score += 0.25;
        reasons.push("hi_vis");
    }
    let vehicle = all.iter().find(|v| {
        v.class == Class::Vehicle
            && v.vehicle.is_some_and(|k| {
                matches!(
                    k.kind,
                    VehicleKind::Van
                        | VehicleKind::Truck
                        | VehicleKind::Scooter
                        | VehicleKind::Motorbike
                )
            })
            && near(p, v, VEHICLE_WINDOW_MS, VEHICLE_WINDOW_MS)
    });
    if let Some(v) = vehicle {
        score += 0.25;
        reasons.push("delivery_vehicle");
        extra.push(v);
    }
    let parcel = all.iter().find(|o| {
        o.class == Class::Parcel
            && o.start_ms.saturating_add(PARCEL_BEFORE_MS) >= p.start_ms
            && o.start_ms <= p.end_ms.saturating_add(PARCEL_AFTER_MS)
    });
    if let Some(o) = parcel {
        score += 0.2;
        reasons.push("parcel_left");
        extra.push(o);
    }
    (score >= DELIVERY_MIN).then(|| {
        episode(
            EpisodeKind::Delivery,
            p,
            extra,
            reasons,
            score * (0.5 + 0.5 * p.confidence),
        )
    })
}

#[must_use]
pub fn detect(all: &[Sighting]) -> Vec<Episode> {
    let mut out = Vec::new();
    for s in all {
        if let Some(e) = delivery(s, all) {
            out.push(e);
            continue;
        }
        match s.class {
            Class::Person if stranger(&s.who) && s.look.face_covered == Some(true) => {
                out.push(episode(
                    EpisodeKind::MaskedPerson,
                    s,
                    vec![],
                    vec!["face_covered"],
                    s.confidence,
                ));
            }
            Class::Person if matches!(s.who, Who::Guest(_)) => {
                out.push(episode(
                    EpisodeKind::Visit,
                    s,
                    vec![],
                    vec!["guest"],
                    0.7 * s.confidence.max(0.5),
                ));
            }
            Class::Vehicle if s.end_ms.saturating_sub(s.start_ms) >= STOP_MIN_MS => {
                out.push(episode(
                    EpisodeKind::VehicleStop,
                    s,
                    vec![],
                    vec!["stopped"],
                    0.6 * s.confidence.max(0.5),
                ));
            }
            Class::Parcel => {
                let home = all.iter().any(|h| {
                    h.class == Class::Person
                        && !stranger(&h.who)
                        && near(s, h, HOME_WINDOW_MS, HOME_WINDOW_MS)
                });
                if !home {
                    out.push(episode(
                        EpisodeKind::ParcelLeft,
                        s,
                        vec![],
                        vec!["unattended"],
                        0.6 * s.confidence.max(0.5),
                    ));
                }
            }
            _ => {}
        }
    }
    out.sort_by(|a, b| b.start_ms.cmp(&a.start_ms).then(a.kind.cmp(&b.kind)));
    out
}
