use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum AssistantMorphology {
    CoreHero,
    FloatingOrb,
    AmbientStream,
    WhisperPill,
}

impl AssistantMorphology {
    #[must_use]
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::CoreHero => "CORE_HERO",
            Self::FloatingOrb => "FLOATING_ORB",
            Self::AmbientStream => "AMBIENT_STREAM",
            Self::WhisperPill => "WHISPER_PILL",
        }
    }

    #[must_use]
    pub const fn requires_gpu_canvas(&self) -> bool {
        match self {
            Self::CoreHero | Self::FloatingOrb => true,
            Self::AmbientStream | Self::WhisperPill => false,
        }
    }
}
