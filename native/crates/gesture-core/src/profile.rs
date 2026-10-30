use crate::error::GestureError;
use crate::gesture::{Direction, GestureKind};
use crate::landmarks::Handedness;
use crate::pose::Pose;
use crate::smoothing::OneEuroConfig;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const MAX_PROFILE_BYTES: usize = 65_536;
pub const MAX_BINDINGS: usize = 256;
const MAX_ARGS: usize = 16;
const MAX_ARG_CHARS: usize = 256;
const MAX_ID_CHARS: usize = 64;
pub const ANY_CONTEXT: &str = "*";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HandFilter {
    #[default]
    Any,
    Left,
    Right,
    Dominant,
    Secondary,
}

impl HandFilter {
    #[must_use]
    pub fn accepts(self, hand: Handedness, dominant: Handedness) -> bool {
        match self {
            Self::Any => true,
            Self::Left => hand == Handedness::Left,
            Self::Right => hand == Handedness::Right,
            Self::Dominant => hand == dominant || hand == Handedness::Unknown,
            Self::Secondary => hand != dominant && hand != Handedness::Unknown,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Binding {
    pub gesture: GestureKind,
    #[serde(default)]
    pub hand: HandFilter,
    #[serde(default = "any_context")]
    pub context: String,
    #[serde(default)]
    pub modifier: Option<Pose>,
    pub action: String,
    #[serde(default)]
    pub args: BTreeMap<String, String>,
    #[serde(default)]
    pub confirm: bool,
    #[serde(default = "enabled")]
    pub enabled: bool,
}

fn any_context() -> String {
    ANY_CONTEXT.to_owned()
}

const fn enabled() -> bool {
    true
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct ActiveZone {
    pub x0: f32,
    pub x1: f32,
    pub y0: f32,
    pub y1: f32,
}

impl Default for ActiveZone {
    fn default() -> Self {
        Self {
            x0: 0.12,
            x1: 0.88,
            y0: 0.08,
            y1: 0.78,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct DuoTuning {
    pub dead_scale: f32,
    pub dead_rotate: f32,
    pub dead_pan: f32,
    pub max_scale: f32,
    pub max_rotate: f32,
    pub smooth: f32,
    pub spread_trigger: f32,
    pub rotate_trigger: f32,
}

impl Default for DuoTuning {
    fn default() -> Self {
        Self {
            dead_scale: 0.006,
            dead_rotate: 0.01,
            dead_pan: 0.0015,
            max_scale: 1.35,
            max_rotate: 0.7,
            smooth: 0.55,
            spread_trigger: 1.3,
            rotate_trigger: 0.6,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct MotionTuning {
    pub swipe_distance: f32,
    pub swipe_speed: f32,
    pub swipe_window_ms: u32,
    pub circle_window_ms: u32,
    pub circle_min_radius: f32,
    pub cooldown_ms: u32,
    pub hold_ms: u32,
    pub tap_max_ms: u32,
    pub double_tap_ms: u32,
    pub stable_frames: u32,
}

impl Default for MotionTuning {
    fn default() -> Self {
        Self {
            swipe_distance: 0.22,
            swipe_speed: 1.0,
            swipe_window_ms: 450,
            circle_window_ms: 1500,
            circle_min_radius: 0.04,
            cooldown_ms: 600,
            hold_ms: 700,
            tap_max_ms: 300,
            double_tap_ms: 450,
            stable_frames: 3,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Smoothing {
    pub min_cutoff: f32,
    pub beta: f32,
}

impl Default for Smoothing {
    fn default() -> Self {
        let base = OneEuroConfig::default();
        Self {
            min_cutoff: base.min_cutoff,
            beta: base.beta,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct GestureProfile {
    pub version: u32,
    pub mirror: bool,
    pub dominant: Handedness,
    pub pointer: bool,
    pub pinch_on: f32,
    pub pinch_off: f32,
    pub follow: f32,
    pub follow_window_ms: u32,
    pub lost_ms: u32,
    pub flick_speed: f32,
    pub flick_window_ms: u32,
    pub zone: ActiveZone,
    pub smoothing: Smoothing,
    pub motion: MotionTuning,
    pub duo: DuoTuning,
    pub bindings: Vec<Binding>,
}

fn binding(gesture: GestureKind, context: &str, action: &str) -> Binding {
    Binding {
        gesture,
        hand: HandFilter::Any,
        context: context.to_owned(),
        modifier: None,
        action: action.to_owned(),
        args: BTreeMap::new(),
        confirm: false,
        enabled: true,
    }
}

impl Default for GestureProfile {
    fn default() -> Self {
        Self {
            version: 1,
            mirror: true,
            dominant: Handedness::Right,
            pointer: true,
            pinch_on: 0.32,
            pinch_off: 0.5,
            follow: 0.45,
            follow_window_ms: 400,
            lost_ms: 700,
            flick_speed: 2.2,
            flick_window_ms: 160,
            zone: ActiveZone::default(),
            smoothing: Smoothing::default(),
            motion: MotionTuning::default(),
            duo: DuoTuning::default(),
            bindings: vec![
                binding(
                    GestureKind::Hold(Pose::OpenPalm),
                    ANY_CONTEXT,
                    "assistant.listen",
                ),
                binding(GestureKind::Swipe(Direction::Left), "tv", "media.previous"),
                binding(GestureKind::Swipe(Direction::Right), "tv", "media.next"),
                binding(GestureKind::Hold(Pose::Fist), "tv", "media.toggle"),
                binding(
                    GestureKind::Pose(Pose::ThumbsUp),
                    ANY_CONTEXT,
                    "feedback.positive",
                ),
                binding(
                    GestureKind::Pose(Pose::ThumbsDown),
                    ANY_CONTEXT,
                    "feedback.negative",
                ),
            ],
        }
    }
}

fn valid_identifier(value: &str) -> bool {
    !value.is_empty()
        && value.chars().count() <= MAX_ID_CHARS
        && value
            .chars()
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || matches!(c, '_' | '.' | '-'))
}

fn invalid(detail: &str) -> GestureError {
    GestureError::ProfileInvalid(detail.to_owned())
}

fn check_range(name: &str, value: f32, lo: f32, hi: f32) -> Result<(), GestureError> {
    if value.is_finite() && (lo..=hi).contains(&value) {
        Ok(())
    } else {
        Err(invalid(name))
    }
}

fn check_binding(b: &Binding) -> Result<(), GestureError> {
    if !valid_identifier(&b.action) {
        return Err(GestureError::InvalidIdentifier(
            b.action.chars().take(MAX_ID_CHARS).collect(),
        ));
    }
    if b.context != ANY_CONTEXT && !valid_identifier(&b.context) {
        return Err(GestureError::InvalidIdentifier(
            b.context.chars().take(MAX_ID_CHARS).collect(),
        ));
    }
    if b.args.len() > MAX_ARGS {
        return Err(invalid("bindings.args"));
    }
    for (key, value) in &b.args {
        if !valid_identifier(key)
            || value.chars().count() > MAX_ARG_CHARS
            || value.chars().any(char::is_control)
        {
            return Err(invalid("bindings.args"));
        }
    }
    Ok(())
}

impl GestureProfile {
    pub fn from_json(raw: &str) -> Result<Self, GestureError> {
        if raw.len() > MAX_PROFILE_BYTES {
            return Err(GestureError::ProfileTooLarge);
        }
        if raw.trim().is_empty() {
            return Ok(Self::default());
        }
        let profile: Self = serde_json::from_str(raw).map_err(|e| invalid(&e.to_string()))?;
        profile.validate()?;
        Ok(profile)
    }

    pub fn to_json(&self) -> Result<String, GestureError> {
        serde_json::to_string(self).map_err(|e| invalid(&e.to_string()))
    }

    pub fn validate(&self) -> Result<(), GestureError> {
        check_range("pinch_on", self.pinch_on, 0.05, 1.0)?;
        check_range("pinch_off", self.pinch_off, self.pinch_on, 1.5)?;
        check_range("follow", self.follow, 0.05, 1.0)?;
        check_range("flick_speed", self.flick_speed, 0.1, 20.0)?;
        check_range("zone.x0", self.zone.x0, 0.0, 0.45)?;
        check_range("zone.x1", self.zone.x1, 0.55, 1.0)?;
        check_range("zone.y0", self.zone.y0, 0.0, 0.45)?;
        check_range("zone.y1", self.zone.y1, 0.55, 1.0)?;
        check_range(
            "smoothing.min_cutoff",
            self.smoothing.min_cutoff,
            0.01,
            30.0,
        )?;
        check_range("smoothing.beta", self.smoothing.beta, 0.0, 10.0)?;
        check_range(
            "motion.swipe_distance",
            self.motion.swipe_distance,
            0.02,
            1.0,
        )?;
        check_range("motion.swipe_speed", self.motion.swipe_speed, 0.05, 20.0)?;
        check_range(
            "motion.circle_min_radius",
            self.motion.circle_min_radius,
            0.005,
            0.5,
        )?;
        check_range("duo.smooth", self.duo.smooth, 0.05, 1.0)?;
        check_range("duo.max_scale", self.duo.max_scale, 1.01, 4.0)?;
        check_range("duo.max_rotate", self.duo.max_rotate, 0.05, 3.2)?;
        check_range("duo.dead_scale", self.duo.dead_scale, 0.0, 0.2)?;
        check_range("duo.dead_rotate", self.duo.dead_rotate, 0.0, 0.5)?;
        check_range("duo.dead_pan", self.duo.dead_pan, 0.0, 0.1)?;
        check_range("duo.spread_trigger", self.duo.spread_trigger, 1.05, 4.0)?;
        check_range("duo.rotate_trigger", self.duo.rotate_trigger, 0.1, 3.2)?;
        let windows = [
            self.follow_window_ms,
            self.lost_ms,
            self.flick_window_ms,
            self.motion.swipe_window_ms,
            self.motion.circle_window_ms,
            self.motion.cooldown_ms,
            self.motion.hold_ms,
            self.motion.tap_max_ms,
            self.motion.double_tap_ms,
        ];
        if windows.iter().any(|w| !(10..=10_000).contains(w)) {
            return Err(invalid("timing"));
        }
        if !(1..=30).contains(&self.motion.stable_frames) {
            return Err(invalid("motion.stable_frames"));
        }
        if self.bindings.len() > MAX_BINDINGS {
            return Err(invalid("bindings"));
        }
        self.bindings.iter().try_for_each(check_binding)
    }

    #[must_use]
    pub const fn one_euro(&self) -> OneEuroConfig {
        OneEuroConfig {
            min_cutoff: self.smoothing.min_cutoff,
            beta: self.smoothing.beta,
            derivative_cutoff: 1.0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_profile_is_valid_and_roundtrips() -> Result<(), GestureError> {
        let profile = GestureProfile::default();
        profile.validate()?;
        assert_eq!(GestureProfile::from_json(&profile.to_json()?)?, profile);
        Ok(())
    }

    #[test]
    fn partial_json_fills_defaults() -> Result<(), GestureError> {
        let profile = GestureProfile::from_json(
            r#"{"pinch_on":0.3,"bindings":[{"gesture":"swipe.up","action":"volume.up"}]}"#,
        )?;
        assert!((profile.pinch_on - 0.3).abs() < 1e-6);
        assert_eq!(
            profile.bindings.first().map(|b| b.context.as_str()),
            Some(ANY_CONTEXT)
        );
        Ok(())
    }

    #[test]
    fn rejects_bad_input() {
        assert!(GestureProfile::from_json(r#"{"pinch_on":0.6,"pinch_off":0.5}"#).is_err());
        assert!(GestureProfile::from_json(r#"{"unknown":1}"#).is_err());
        assert!(
            GestureProfile::from_json(r#"{"bindings":[{"gesture":"swipe.up","action":"Rm -rf"}]}"#)
                .is_err()
        );
        assert!(
            GestureProfile::from_json(r#"{"bindings":[{"gesture":"pose.laser","action":"x"}]}"#)
                .is_err()
        );
        assert!(
            GestureProfile::from_json(
                r#"{"bindings":[{"gesture":"tap","action":"x","args":{"k":"a\nb"}}]}"#
            )
            .is_err()
        );
        assert_eq!(
            GestureProfile::from_json(&" ".repeat(MAX_PROFILE_BYTES + 1)),
            Err(GestureError::ProfileTooLarge)
        );
    }

    #[test]
    fn hand_filter_semantics() {
        assert!(HandFilter::Dominant.accepts(Handedness::Right, Handedness::Right));
        assert!(!HandFilter::Dominant.accepts(Handedness::Left, Handedness::Right));
        assert!(HandFilter::Secondary.accepts(Handedness::Left, Handedness::Right));
        assert!(!HandFilter::Secondary.accepts(Handedness::Unknown, Handedness::Right));
    }
}
