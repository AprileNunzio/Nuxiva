use std::fmt;

use nuxiva_gesture_core::wire::{events_to_json, frame_from_json};
use nuxiva_gesture_core::{Frame, GestureEngine, GestureError, GestureEvent, GestureProfile};
use serde::Serialize;

use crate::gate::{Audience, public_only, trusted};
use crate::owner::{Face, MAX_FACES, Owner, owner_of};

const MAX_FACES_JSON: usize = 8 * 1024;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HandsError {
    Gesture(String),
    Faces,
}

impl fmt::Display for HandsError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Gesture(e) => write!(f, "hands.gesture: {e}"),
            Self::Faces => f.write_str("hands.faces.invalid"),
        }
    }
}

impl std::error::Error for HandsError {}

impl From<GestureError> for HandsError {
    fn from(e: GestureError) -> Self {
        Self::Gesture(e.to_string())
    }
}

#[derive(Debug, Default, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct Tally {
    pub trusted: usize,
    pub public: usize,
}

#[derive(Debug)]
pub struct HandsEngine {
    trusted: GestureEngine,
    public: GestureEngine,
    faces: Vec<Face>,
    audience: Audience,
    trust_guests: bool,
    last: Tally,
}

impl HandsEngine {
    pub fn new(profile_json: &str) -> Result<Self, HandsError> {
        let profile = GestureProfile::from_json(profile_json)?;
        Ok(Self {
            trusted: GestureEngine::new(profile.clone()),
            public: GestureEngine::new(profile),
            faces: Vec::new(),
            audience: Audience::Uncertain,
            trust_guests: false,
            last: Tally::default(),
        })
    }

    pub fn set_profile(&mut self, profile_json: &str) -> Result<(), HandsError> {
        let profile = GestureProfile::from_json(profile_json)?;
        self.trusted.set_profile(profile.clone());
        self.public.set_profile(profile);
        Ok(())
    }

    pub fn set_scene(
        &mut self,
        faces_json: &str,
        audience: &str,
        trust_guests: bool,
    ) -> Result<(), HandsError> {
        if faces_json.len() > MAX_FACES_JSON {
            return Err(HandsError::Faces);
        }
        let faces: Vec<Face> = serde_json::from_str(faces_json).map_err(|_| HandsError::Faces)?;
        if faces.len() > MAX_FACES || !faces.iter().all(Face::sane) {
            return Err(HandsError::Faces);
        }
        self.faces = faces;
        self.audience = Audience::parse(audience);
        self.trust_guests = trust_guests;
        Ok(())
    }

    pub fn feed(&mut self, frame: &Frame, context: &str) -> Vec<GestureEvent> {
        let (mine, others): (Vec<_>, Vec<_>) = frame.hands.iter().cloned().partition(|h| {
            let owner: Owner = owner_of(h, &self.faces);
            trusted(owner, self.audience, self.trust_guests)
        });
        self.last = Tally {
            trusted: mine.len(),
            public: others.len(),
        };
        let at = frame.timestamp_ms;
        let mut out = self.trusted.feed(
            &Frame {
                timestamp_ms: at,
                hands: mine,
            },
            context,
        );
        if !matches!(self.audience, Audience::Empty) {
            out.extend(public_only(self.public.feed(
                &Frame {
                    timestamp_ms: at,
                    hands: others,
                },
                context,
            )));
        }
        out
    }

    pub fn feed_json(&mut self, frame_json: &str, context: &str) -> Result<String, HandsError> {
        let frame = frame_from_json(frame_json)?;
        let events = self.feed(&frame, context);
        Ok(events_to_json(&events)?)
    }

    #[must_use]
    pub const fn tally(&self) -> Tally {
        self.last
    }
}
