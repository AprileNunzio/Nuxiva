use crate::manifest::{ContextManifest, FocusLockLevel, SafeZone};
use crate::morphology::AssistantMorphology;
use crate::priority::{NotificationEvent, NotificationPriority};
use crate::z_stack::ZLayer;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ArbitrationAction {
    PreemptionTotal,
    SmartPip,
    VoiceInterject,
    MicroBadge,
    Deferral,
    SilentLog,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ArbitrationResult {
    pub action: ArbitrationAction,
    pub target_morphology: AssistantMorphology,
    pub assigned_safe_zone: Option<SafeZone>,
    pub suspend_primary_stage: bool,
    pub target_layer: ZLayer,
    pub should_defer: bool,
    pub reason_code: &'static str,
}

#[derive(Debug, Default, Clone, Copy)]
pub struct PriorityArbiter;

impl PriorityArbiter {
    #[must_use]
    pub const fn new() -> Self {
        Self
    }

    #[must_use]
    pub fn arbitrate(
        &self,
        event: &NotificationEvent,
        manifest: &ContextManifest,
    ) -> ArbitrationResult {
        let lock = manifest.focus_lock_level;
        let preferred_morphology = manifest.assistant_requirement.preferred_morphology;
        let fallback_morphology = manifest.assistant_requirement.fallback_morphology;
        let safe_zones = &manifest.assistant_requirement.allowed_safe_zones;

        match event.priority {
            NotificationPriority::P0Critical => ArbitrationResult {
                action: ArbitrationAction::PreemptionTotal,
                target_morphology: AssistantMorphology::CoreHero,
                assigned_safe_zone: None,
                suspend_primary_stage: true,
                target_layer: ZLayer::Z4CriticalInterrupt,
                should_defer: false,
                reason_code: "p0_preemption",
            },

            NotificationPriority::P1High => {
                if lock == FocusLockLevel::Lock3Immersive {
                    ArbitrationResult {
                        action: ArbitrationAction::VoiceInterject,
                        target_morphology: AssistantMorphology::AmbientStream,
                        assigned_safe_zone: None,
                        suspend_primary_stage: false,
                        target_layer: ZLayer::Z3Assistant,
                        should_defer: false,
                        reason_code: "p1_voice_interject",
                    }
                } else {
                    let zone = safe_zones.first().copied().unwrap_or(SafeZone::TopRight);
                    ArbitrationResult {
                        action: ArbitrationAction::SmartPip,
                        target_morphology: preferred_morphology,
                        assigned_safe_zone: Some(zone),
                        suspend_primary_stage: false,
                        target_layer: ZLayer::Z2ContextualHud,
                        should_defer: false,
                        reason_code: "p1_smart_pip",
                    }
                }
            }

            NotificationPriority::P2Normal => match lock {
                FocusLockLevel::Lock0Idle => ArbitrationResult {
                    action: ArbitrationAction::SmartPip,
                    target_morphology: AssistantMorphology::CoreHero,
                    assigned_safe_zone: Some(SafeZone::Center),
                    suspend_primary_stage: false,
                    target_layer: ZLayer::Z2ContextualHud,
                    should_defer: false,
                    reason_code: "p2_immediate",
                },
                FocusLockLevel::Lock1Focus => {
                    let zone = safe_zones.first().copied().unwrap_or(SafeZone::BottomRight);
                    ArbitrationResult {
                        action: ArbitrationAction::MicroBadge,
                        target_morphology: preferred_morphology,
                        assigned_safe_zone: Some(zone),
                        suspend_primary_stage: false,
                        target_layer: ZLayer::Z2ContextualHud,
                        should_defer: false,
                        reason_code: "p2_micro_badge",
                    }
                }
                FocusLockLevel::Lock2Engaged | FocusLockLevel::Lock3Immersive => {
                    ArbitrationResult {
                        action: ArbitrationAction::Deferral,
                        target_morphology: if lock == FocusLockLevel::Lock3Immersive {
                            fallback_morphology
                        } else {
                            preferred_morphology
                        },
                        assigned_safe_zone: None,
                        suspend_primary_stage: false,
                        target_layer: ZLayer::Z1PrimaryStage,
                        should_defer: true,
                        reason_code: "p2_deferred",
                    }
                }
            },

            NotificationPriority::P3Low => ArbitrationResult {
                action: ArbitrationAction::SilentLog,
                target_morphology: preferred_morphology,
                assigned_safe_zone: None,
                suspend_primary_stage: false,
                target_layer: ZLayer::Z0Ambient,
                should_defer: false,
                reason_code: "p3_silent",
            },
        }
    }
}
