use serde::Serialize;

use crate::index::tokens;

pub const MAX_EXTRA: usize = 50;
pub const MAX_EXTRA_LEN: usize = 64;
pub const MAX_ROOM_LEN: usize = 200;

pub const PRIVATE_ROOMS: &[&str] = &[
    "bagno",
    "bagni",
    "wc",
    "toilette",
    "doccia",
    "camera",
    "camere",
    "cameretta",
    "camerette",
    "stanza da letto",
    "spogliatoio",
    "bathroom",
    "restroom",
    "toilet",
    "shower",
    "bedroom",
    "nursery",
    "dressing room",
    "changing room",
    "salle de bain",
    "salle de bains",
    "toilettes",
    "chambre",
    "douche",
    "vestiaire",
    "bano",
    "banos",
    "aseo",
    "dormitorio",
    "habitacion",
    "recamara",
    "vestidor",
    "ducha",
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct AudioDecision {
    pub allowed: bool,
    pub reason: &'static str,
    pub private: bool,
}

fn contains_phrase(room: &[String], phrase: &str) -> bool {
    let wanted = tokens(phrase);
    !wanted.is_empty() && room.windows(wanted.len()).any(|w| w == wanted.as_slice())
}

#[must_use]
pub fn is_private_room(room: &str, extra: &[String]) -> bool {
    let cut: String = room.chars().take(MAX_ROOM_LEN).collect();
    let words = tokens(&cut);
    PRIVATE_ROOMS.iter().any(|p| contains_phrase(&words, p))
        || extra
            .iter()
            .take(MAX_EXTRA)
            .filter(|e| e.chars().count() <= MAX_EXTRA_LEN)
            .any(|e| contains_phrase(&words, e))
}

#[must_use]
pub fn audio_decision(
    room: &str,
    opted_in: bool,
    notice_active: bool,
    extra: &[String],
) -> AudioDecision {
    let private = is_private_room(room, extra);
    let reason = if private {
        "private_room"
    } else if !notice_active {
        "notice_off"
    } else if !opted_in {
        "not_opted_in"
    } else {
        "allowed"
    };
    AudioDecision {
        allowed: reason == "allowed",
        reason,
        private,
    }
}
