use nuxiva_gesture_core::GestureEvent;
use serde::{Deserialize, Serialize};

use crate::owner::Owner;

pub const PUBLIC_ACTIONS: [&str; 6] = [
    "media.toggle",
    "media.next",
    "media.previous",
    "volume.up",
    "volume.down",
    "volume.mute",
];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Audience {
    Empty,
    GuestOnly,
    Authorized,
    Mixed,
    #[default]
    Uncertain,
}

impl Audience {
    #[must_use]
    pub fn parse(raw: &str) -> Self {
        match raw {
            "empty" => Self::Empty,
            "guest_only" => Self::GuestOnly,
            "authorized" => Self::Authorized,
            "mixed" => Self::Mixed,
            _ => Self::Uncertain,
        }
    }
}

#[must_use]
pub const fn trusted(owner: Owner, audience: Audience, trust_guests: bool) -> bool {
    match owner {
        Owner::Authorized => !matches!(audience, Audience::Empty),
        Owner::Guest => trust_guests && matches!(audience, Audience::Mixed),
        Owner::Unknown => {
            matches!(audience, Audience::Authorized)
                || (trust_guests && matches!(audience, Audience::Mixed))
        }
    }
}

#[must_use]
pub fn public_only(events: Vec<GestureEvent>) -> Vec<GestureEvent> {
    events
        .into_iter()
        .filter(|e| match e {
            GestureEvent::Action {
                action, confirm, ..
            } => !confirm && PUBLIC_ACTIONS.contains(&action.as_str()),
            GestureEvent::Pointer { .. }
            | GestureEvent::Gesture { .. }
            | GestureEvent::Duo { .. } => false,
        })
        .collect()
}
