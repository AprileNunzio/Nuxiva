#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Speaker {
    Authorized { score: f32 },
    Unknown { score: f32 },
    Ambiguous,
    Unavailable,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Policy {
    pub min_wake: f32,
    pub require_speaker: bool,
}

impl Default for Policy {
    fn default() -> Self {
        Self {
            min_wake: 0.3,
            require_speaker: true,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Decision {
    Accept {
        confidence: f32,
        speaker: Option<f32>,
    },
    RejectWake,
    RejectSpeaker,
    RejectAmbiguous,
    NeedsEnrollment,
}

impl Decision {
    #[must_use]
    pub const fn accepted(self) -> bool {
        matches!(self, Self::Accept { .. })
    }

    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Accept { .. } => "accept",
            Self::RejectWake => "reject_wake",
            Self::RejectSpeaker => "reject_speaker",
            Self::RejectAmbiguous => "reject_ambiguous",
            Self::NeedsEnrollment => "needs_enrollment",
        }
    }
}

#[must_use]
pub fn decide(wake_confidence: f32, speaker: Speaker, policy: Policy) -> Decision {
    if !wake_confidence.is_finite() || wake_confidence < policy.min_wake {
        return Decision::RejectWake;
    }
    match speaker {
        Speaker::Authorized { score } if score.is_finite() => Decision::Accept {
            confidence: wake_confidence.min(score.clamp(0.0, 1.0)),
            speaker: Some(score),
        },
        Speaker::Authorized { .. } | Speaker::Unknown { .. } => Decision::RejectSpeaker,
        Speaker::Ambiguous => Decision::RejectAmbiguous,
        Speaker::Unavailable if policy.require_speaker => Decision::NeedsEnrollment,
        Speaker::Unavailable => Decision::Accept {
            confidence: wake_confidence,
            speaker: None,
        },
    }
}
