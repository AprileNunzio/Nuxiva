use nuxiva_swarm_core::{Affect, Channel, Ident, Percept, SCHEMA_VERSION, Settings, Validate};

use crate::error::{PerceptError, PerceptResult};
use crate::observation::Observation;
use crate::settings::PerceptSettings;

#[derive(Debug, Clone)]
struct Stamped<T> {
    value: T,
    at_ms: u64,
}

fn newer<T>(slot: &mut Option<Stamped<T>>, value: T, at_ms: u64) {
    if slot.as_ref().is_none_or(|s| at_ms >= s.at_ms) {
        *slot = Some(Stamped { value, at_ms });
    }
}

fn fresh<T>(slot: Option<&Stamped<T>>, now_ms: u64, ttl_ms: u64) -> Option<&T> {
    slot.filter(|s| now_ms.saturating_sub(s.at_ms) <= ttl_ms)
        .map(|s| &s.value)
}

#[derive(Debug, Clone)]
pub struct Fuser {
    settings: PerceptSettings,
    speaker: Option<Stamped<(Ident, u16)>>,
    presence: Option<Stamped<Vec<Ident>>>,
    emotion: Option<Stamped<(Ident, Affect)>>,
    scene: Option<Stamped<Ident>>,
    audio: Option<Stamped<Ident>>,
}

impl Fuser {
    pub fn new(settings: PerceptSettings) -> PerceptResult<Self> {
        settings.validate()?;
        Ok(Self {
            settings,
            speaker: None,
            presence: None,
            emotion: None,
            scene: None,
            audio: None,
        })
    }

    pub fn observe(&mut self, observation: Observation, now_ms: u64) -> PerceptResult<()> {
        let at_ms = observation.at_ms();
        if at_ms > now_ms.saturating_add(self.settings.max_clock_skew_ms) {
            return Err(PerceptError::Clock);
        }
        match observation {
            Observation::Speaker {
                person, permille, ..
            } => {
                if permille > 1000 {
                    return Err(PerceptError::Invalid);
                }
                newer(&mut self.speaker, (person, permille), at_ms);
            }
            Observation::Presence { people, .. } => {
                if people.len() > self.settings.max_presence {
                    return Err(PerceptError::TooLarge);
                }
                newer(&mut self.presence, people, at_ms);
            }
            Observation::Emotion {
                person,
                valence,
                arousal,
                source,
                ..
            } => {
                let affect = Affect {
                    valence,
                    arousal,
                    source,
                    at_ms,
                };
                affect.validate(&Settings::default())?;
                newer(&mut self.emotion, (person, affect), at_ms);
            }
            Observation::Scene { reference, .. } => newer(&mut self.scene, reference, at_ms),
            Observation::Audio { reference, .. } => newer(&mut self.audio, reference, at_ms),
        }
        Ok(())
    }

    pub fn fuse(
        &self,
        id: Ident,
        channel: Channel,
        text: String,
        now_ms: u64,
        limits: &Settings,
    ) -> PerceptResult<Percept> {
        let speaker = fresh(self.speaker.as_ref(), now_ms, self.settings.speaker_ttl_ms)
            .filter(|(_, permille)| *permille >= self.settings.min_speaker_permille);
        let mut presence: Vec<Ident> = fresh(
            self.presence.as_ref(),
            now_ms,
            self.settings.presence_ttl_ms,
        )
        .cloned()
        .unwrap_or_default();
        if let Some((person, _)) = speaker {
            if !presence.contains(person) {
                presence.push(person.clone());
            }
        }
        let emotion = speaker.and_then(|(person, _)| {
            fresh(self.emotion.as_ref(), now_ms, self.settings.emotion_ttl_ms)
                .filter(|(owner, _)| owner == person)
                .map(|(_, affect)| affect.clone())
        });
        let percept = Percept {
            schema_version: SCHEMA_VERSION,
            id,
            at_ms: now_ms,
            channel,
            text,
            speaker: speaker.map(|(person, _)| person.clone()),
            addressee_permille: speaker.map_or(0, |(_, permille)| *permille),
            emotion,
            scene_ref: fresh(self.scene.as_ref(), now_ms, self.settings.scene_ttl_ms).cloned(),
            audio_ref: fresh(self.audio.as_ref(), now_ms, self.settings.audio_ttl_ms).cloned(),
            presence,
        };
        percept.validate(limits)?;
        Ok(percept)
    }
}
