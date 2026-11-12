use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

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

#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct RoomAudience {
    pub global: Audience,
    pub rooms: BTreeMap<String, Audience>,
    pub sensed: Vec<String>,
    pub strict: bool,
}

impl RoomAudience {
    #[must_use]
    pub fn for_room(&self, room: Option<&str>) -> Audience {
        let Some(room) = room else { return self.global };
        if let Some(kind) = self.rooms.get(room) {
            return *kind;
        }
        if self.sensed.iter().any(|r| r == room) {
            return self.global;
        }
        if self.strict {
            Audience::Uncertain
        } else {
            self.global
        }
    }
}
