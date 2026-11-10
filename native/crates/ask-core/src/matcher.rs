use nuxiva_memory_core::{Class, Item, Sighting, VehicleKind, Who};

use crate::query::{AskQuery, RoleTarget};

#[derive(Debug, Clone)]
pub struct ScoredMatch<'a> {
    pub sighting: &'a Sighting,
    pub score: f32,
    pub matched_reasons: Vec<&'static str>,
}

#[must_use]
#[allow(clippy::too_many_lines)]
pub fn match_sightings<'a>(query: &AskQuery, sightings: &'a [Sighting]) -> Vec<ScoredMatch<'a>> {
    let mut matches = Vec::new();

    for s in sightings {
        if s.end_ms < query.from_ms || s.start_ms > query.to_ms {
            continue;
        }

        let mut score = 10.0_f32;
        let mut reasons = Vec::new();

        if let Some(target_class) = query.class {
            if s.class == target_class {
                score += 20.0;
                reasons.push("class_match");
            } else if query.target_role == Some(RoleTarget::Courier) && s.class == Class::Parcel {
                score += 15.0;
                reasons.push("parcel_class");
            } else {
                continue;
            }
        }

        if let Some(role) = query.target_role {
            match role {
                RoleTarget::Courier => {
                    let mut courier_signal = s.class == Class::Parcel;
                    if s.look.carrying.contains(&Item::Parcel) {
                        score += 30.0;
                        reasons.push("parcel_in_hand");
                        courier_signal = true;
                    }
                    if s.look.hi_vis == Some(true) {
                        score += 20.0;
                        reasons.push("hi_vis");
                        courier_signal = true;
                    }
                    if let Some(v) = &s.vehicle {
                        if matches!(v.kind, VehicleKind::Van | VehicleKind::Truck) {
                            score += 25.0;
                            reasons.push("delivery_vehicle");
                            courier_signal = true;
                        }
                    }
                    if !courier_signal {
                        continue;
                    }
                    if matches!(s.who, Who::Unknown) {
                        score += 10.0;
                        reasons.push("stranger");
                    }
                }
                RoleTarget::Visitor => {
                    if matches!(s.who, Who::Guest(_)) {
                        score += 30.0;
                        reasons.push("guest");
                    } else if matches!(s.who, Who::Unknown) {
                        score += 15.0;
                        reasons.push("unknown_visitor");
                    }
                }
                RoleTarget::Vehicle => {
                    if s.class == Class::Vehicle {
                        score += 20.0;
                        reasons.push("vehicle");
                    }
                }
                RoleTarget::Animal => {
                    if s.class == Class::Animal {
                        score += 30.0;
                        reasons.push("animal");
                    }
                }
                RoleTarget::Household => {
                    if matches!(s.who, Who::Person(_)) {
                        score += 30.0;
                        reasons.push("household_member");
                    }
                }
                RoleTarget::Unknown => {
                    if matches!(s.who, Who::Unknown) {
                        score += 20.0;
                        reasons.push("unknown_person");
                    }
                }
            }
        }

        if let Some(color) = query.upper_color {
            if s.look.upper == Some(color) {
                score += 30.0;
                reasons.push("upper_color_match");
            }
        }

        if let Some(color) = query.lower_color {
            if s.look.lower == Some(color) {
                score += 25.0;
                reasons.push("lower_color_match");
            }
        }

        if let Some(item) = query.item {
            if s.look.carrying.contains(&item) {
                score += 25.0;
                reasons.push("carrying_item");
            }
        }

        if let Some(vk) = query.vehicle_kind {
            if let Some(v) = &s.vehicle {
                if v.kind == vk {
                    score += 30.0;
                    reasons.push("vehicle_kind_match");
                }
            }
        }

        if let Some(vc) = query.vehicle_color {
            if let Some(v) = &s.vehicle {
                if v.color == Some(vc) {
                    score += 25.0;
                    reasons.push("vehicle_color_match");
                }
            }
        }

        if let Some(loc) = &query.camera_or_zone {
            let loc_lower = loc.to_lowercase();
            if s.camera.to_lowercase().contains(&loc_lower)
                || s.zone
                    .as_ref()
                    .is_some_and(|z| z.to_lowercase().contains(&loc_lower))
            {
                score += 20.0;
                reasons.push("location_match");
            }
        }

        let total_score = score * (0.5 + 0.5 * s.confidence.clamp(0.1, 1.0));
        if total_score >= 15.0 {
            matches.push(ScoredMatch {
                sighting: s,
                score: total_score,
                matched_reasons: reasons,
            });
        }
    }

    matches.sort_by(|a, b| b.score.total_cmp(&a.score));
    matches
}
