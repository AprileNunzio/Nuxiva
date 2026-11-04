use crate::morphology::AssistantMorphology;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ViewportMode {
    ImmersiveStage,
    SplitPivot,
    FloatingWidget,
    AmbientBackground,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum GpuLoad {
    None,
    Low,
    Medium,
    High,
    Extreme,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SafeZone {
    TopLeft,
    TopRight,
    BottomLeft,
    BottomRight,
    Center,
    ScreenEdgeGlow,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum VoiceInteraction {
    ContinuousCoPilot,
    OnDemandAssistant,
    SilentObserver,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum FocusLockLevel {
    #[serde(rename = "0")]
    Lock0Idle = 0,
    #[serde(rename = "1")]
    Lock1Focus = 1,
    #[serde(rename = "2")]
    Lock2Engaged = 2,
    #[serde(rename = "3")]
    Lock3Immersive = 3,
}

impl FocusLockLevel {
    #[must_use]
    pub const fn level_number(&self) -> u8 {
        match self {
            Self::Lock0Idle => 0,
            Self::Lock1Focus => 1,
            Self::Lock2Engaged => 2,
            Self::Lock3Immersive => 3,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AssistantRequirement {
    pub preferred_morphology: AssistantMorphology,
    pub fallback_morphology: AssistantMorphology,
    pub allowed_safe_zones: Vec<SafeZone>,
    pub voice_interaction: VoiceInteraction,
}

impl AssistantRequirement {
    #[must_use]
    pub const fn new(
        preferred_morphology: AssistantMorphology,
        fallback_morphology: AssistantMorphology,
        voice_interaction: VoiceInteraction,
    ) -> Self {
        Self {
            preferred_morphology,
            fallback_morphology,
            allowed_safe_zones: Vec::new(),
            voice_interaction,
        }
    }

    #[must_use]
    pub fn with_safe_zones(mut self, zones: Vec<SafeZone>) -> Self {
        self.allowed_safe_zones = zones;
        self
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ContextManifest {
    pub context_id: String,
    pub viewport_mode: ViewportMode,
    pub gpu_load: GpuLoad,
    pub assistant_requirement: AssistantRequirement,
    pub focus_lock_level: FocusLockLevel,
}

impl ContextManifest {
    #[must_use]
    pub fn new(
        context_id: impl Into<String>,
        viewport_mode: ViewportMode,
        gpu_load: GpuLoad,
        assistant_requirement: AssistantRequirement,
        focus_lock_level: FocusLockLevel,
    ) -> Self {
        Self {
            context_id: context_id.into(),
            viewport_mode,
            gpu_load,
            assistant_requirement,
            focus_lock_level,
        }
    }

    #[must_use]
    pub fn idle_default() -> Self {
        Self {
            context_id: "app.nuxiva.idle".to_string(),
            viewport_mode: ViewportMode::AmbientBackground,
            gpu_load: GpuLoad::Low,
            assistant_requirement: AssistantRequirement {
                preferred_morphology: AssistantMorphology::CoreHero,
                fallback_morphology: AssistantMorphology::FloatingOrb,
                allowed_safe_zones: vec![SafeZone::Center],
                voice_interaction: VoiceInteraction::ContinuousCoPilot,
            },
            focus_lock_level: FocusLockLevel::Lock0Idle,
        }
    }
}
