use serde::{Deserialize, Serialize};

use crate::error::{PerceptError, PerceptResult};

pub const MAX_MODAL_CHANNELS: usize = 32;
pub const DISTRESS_VOCAL_RMS_BPS: u16 = 8_500;
pub const GAZE_LOCK_CONFIDENCE_BPS: u16 = 7_500;
pub const GESTURE_ACTION_CONFIDENCE_BPS: u16 = 8_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EmbodiedOrgan {
    EyesVision,
    EarsHearing,
    VoiceSpeech,
    ArmsActuation,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct VisionEyeSnapshot {
    pub camera_node_id: String,
    pub face_recognized_id: Option<String>,
    pub gaze_confidence_bps: u16,
    pub active_gesture_key: Option<String>,
    pub gesture_confidence_bps: u16,
    pub scene_anomaly_bps: u16,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct HearingEarSnapshot {
    pub mic_array_node_id: String,
    pub azimuth_deg: i16,
    pub speaker_id: Option<String>,
    pub transcript_key: Option<String>,
    pub vocal_energy_bps: u16,
    pub danger_acoustic_bps: u16,
    pub barge_in_detected: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SpeechVoiceState {
    pub output_node_id: String,
    pub currently_speaking: bool,
    pub active_utterance_key: Option<String>,
    pub volume_bps: u16,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ArmActuatorCapability {
    pub actuator_id: String,
    pub domain_key: String,
    pub online: bool,
    pub zero_trust_sealed: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EmbodiedMotorCommand {
    pub organ: EmbodiedOrgan,
    pub target_node_id: String,
    pub command_key: String,
    pub payload_key: String,
    pub priority_bps: u16,
    pub requires_confirmation: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SensorimotorFrameOutcome {
    pub attention_target_person: Option<String>,
    pub focused_camera_node: String,
    pub focused_audio_azimuth_deg: i16,
    pub commands: Vec<EmbodiedMotorCommand>,
    pub reflexive_barge_cut: bool,
    pub emergency_triggered: bool,
}

fn clean_id(raw: &str) -> PerceptResult<String> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Err(PerceptError::Invalid);
    }
    if trimmed.len() > 160 {
        return Err(PerceptError::TooLarge);
    }
    if trimmed
        .chars()
        .any(|c| c.is_control() || c == '\0' || c == '\u{202e}')
    {
        return Err(PerceptError::Invalid);
    }
    Ok(trimmed.to_owned())
}

fn append_emergency_commands(
    spk_node: &str,
    arms: &[ArmActuatorCapability],
    commands: &mut Vec<EmbodiedMotorCommand>,
) -> PerceptResult<()> {
    commands.push(EmbodiedMotorCommand {
        organ: EmbodiedOrgan::VoiceSpeech,
        target_node_id: spk_node.to_owned(),
        command_key: "duplex.voice.speak_alert".to_owned(),
        payload_key: "i18n.embodied.emergency_verification_prompt".to_owned(),
        priority_bps: 10_000,
        requires_confirmation: false,
    });
    for arm in arms {
        if arm.online && arm.zero_trust_sealed {
            let act_id = clean_id(&arm.actuator_id)?;
            commands.push(EmbodiedMotorCommand {
                organ: EmbodiedOrgan::ArmsActuation,
                target_node_id: act_id,
                command_key: "actuation.safety.engage_protective_state".to_owned(),
                payload_key: "i18n.embodied.protective_lockdown".to_owned(),
                priority_bps: 10_000,
                requires_confirmation: false,
            });
        }
    }
    Ok(())
}

pub fn coordinate_sensorimotor_cycle(
    eyes: &VisionEyeSnapshot,
    ears: &HearingEarSnapshot,
    voice: &SpeechVoiceState,
    arms: &[ArmActuatorCapability],
) -> PerceptResult<SensorimotorFrameOutcome> {
    if arms.len() > MAX_MODAL_CHANNELS {
        return Err(PerceptError::TooLarge);
    }
    let cam_id = clean_id(&eyes.camera_node_id)?;
    let _mic_id = clean_id(&ears.mic_array_node_id)?;
    let spk_node = clean_id(&voice.output_node_id)?;

    let mut commands = Vec::new();
    let mut reflexive_barge_cut = false;
    let mut emergency_triggered = false;

    let attention_target_person = eyes
        .face_recognized_id
        .clone()
        .or_else(|| ears.speaker_id.clone());

    if ears.barge_in_detected && voice.currently_speaking {
        reflexive_barge_cut = true;
        commands.push(EmbodiedMotorCommand {
            organ: EmbodiedOrgan::VoiceSpeech,
            target_node_id: spk_node.clone(),
            command_key: "duplex.voice.immediate_duck_and_listen".to_owned(),
            payload_key: "i18n.embodied.voice_yield_to_user".to_owned(),
            priority_bps: 9_900,
            requires_confirmation: false,
        });
    }

    if ears.danger_acoustic_bps >= DISTRESS_VOCAL_RMS_BPS
        || eyes.scene_anomaly_bps >= DISTRESS_VOCAL_RMS_BPS
    {
        emergency_triggered = true;
        append_emergency_commands(&spk_node, arms, &mut commands)?;
    }

    if let Some(gesture) = &eyes.active_gesture_key
        && eyes.gesture_confidence_bps >= GESTURE_ACTION_CONFIDENCE_BPS
    {
        let clean_gesture = clean_id(gesture)?;
        if let Some(arm) = arms.iter().find(|a| a.online && a.zero_trust_sealed) {
            let act_id = clean_id(&arm.actuator_id)?;
            commands.push(EmbodiedMotorCommand {
                organ: EmbodiedOrgan::ArmsActuation,
                target_node_id: act_id,
                command_key: format!("actuation.gesture.{clean_gesture}"),
                payload_key: clean_gesture,
                priority_bps: eyes.gesture_confidence_bps,
                requires_confirmation: false,
            });
        }
    }

    if eyes.gaze_confidence_bps >= GAZE_LOCK_CONFIDENCE_BPS
        && let Some(transcript) = &ears.transcript_key
    {
        let clean_tx = clean_id(transcript)?;
        for arm in arms {
            if arm.online && arm.zero_trust_sealed {
                let act_id = clean_id(&arm.actuator_id)?;
                commands.push(EmbodiedMotorCommand {
                    organ: EmbodiedOrgan::ArmsActuation,
                    target_node_id: act_id,
                    command_key: "actuation.intent.execute_gaze_confirmed".to_owned(),
                    payload_key: clean_tx.clone(),
                    priority_bps: eyes.gaze_confidence_bps,
                    requires_confirmation: false,
                });
            }
        }
        if !reflexive_barge_cut && !emergency_triggered {
            commands.push(EmbodiedMotorCommand {
                organ: EmbodiedOrgan::VoiceSpeech,
                target_node_id: spk_node,
                command_key: "duplex.voice.acknowledge_execution".to_owned(),
                payload_key: "i18n.embodied.action_dispatched".to_owned(),
                priority_bps: 8_500,
                requires_confirmation: false,
            });
        }
    }

    Ok(SensorimotorFrameOutcome {
        attention_target_person,
        focused_camera_node: cam_id,
        focused_audio_azimuth_deg: ears.azimuth_deg,
        commands,
        reflexive_barge_cut,
        emergency_triggered,
    })
}
