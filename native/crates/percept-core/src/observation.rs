use nuxiva_swarm_core::Ident;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Observation {
    Speaker {
        person: Ident,
        permille: u16,
        at_ms: u64,
    },
    Presence {
        people: Vec<Ident>,
        at_ms: u64,
    },
    Emotion {
        person: Ident,
        valence: i16,
        arousal: u16,
        source: Ident,
        at_ms: u64,
    },
    Scene {
        reference: Ident,
        at_ms: u64,
    },
    Audio {
        reference: Ident,
        at_ms: u64,
    },
}

impl Observation {
    #[must_use]
    pub fn at_ms(&self) -> u64 {
        match self {
            Self::Speaker { at_ms, .. }
            | Self::Presence { at_ms, .. }
            | Self::Emotion { at_ms, .. }
            | Self::Scene { at_ms, .. }
            | Self::Audio { at_ms, .. } => *at_ms,
        }
    }
}
