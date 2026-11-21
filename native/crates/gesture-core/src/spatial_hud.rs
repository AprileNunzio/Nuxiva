use crate::error::GestureError;
use crate::landmarks::{Hand, Joint};
use crate::pose::{Pose, classify};
use serde::{Deserialize, Serialize};

pub const DEFAULT_AUTO_CLOSE_MS: u64 = 4_000;
pub const DEBOUNCE_FRAMES: u32 = 3;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HologramShape {
    Dispersed,
    #[default]
    Sphere,
    Torus,
    Cube,
    Helix,
}

impl HologramShape {
    #[must_use]
    pub const fn id(self) -> &'static str {
        match self {
            Self::Dispersed => "dispersed",
            Self::Sphere => "sphere",
            Self::Torus => "torus",
            Self::Cube => "cube",
            Self::Helix => "helix",
        }
    }

    #[must_use]
    pub fn from_id(id: &str) -> Option<Self> {
        match id.trim().to_ascii_lowercase().as_str() {
            "dispersed" => Some(Self::Dispersed),
            "sphere" => Some(Self::Sphere),
            "torus" | "ring" => Some(Self::Torus),
            "cube" => Some(Self::Cube),
            "helix" | "spiral" => Some(Self::Helix),
            _ => None,
        }
    }

    #[must_use]
    pub const fn next_focused(self) -> Self {
        match self {
            Self::Dispersed | Self::Helix => Self::Sphere,
            Self::Sphere => Self::Torus,
            Self::Torus => Self::Cube,
            Self::Cube => Self::Helix,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SpatialGestureKind {
    #[default]
    Idle,
    OpenPalmDisperse,
    SingleHandFocusMorph,
    WristRotationTilt,
    TwoHandPinchStretch,
}

impl SpatialGestureKind {
    #[must_use]
    pub const fn id(self) -> &'static str {
        match self {
            Self::Idle => "idle",
            Self::OpenPalmDisperse => "open_palm_disperse",
            Self::SingleHandFocusMorph => "single_hand_focus_morph",
            Self::WristRotationTilt => "wrist_rotation_tilt",
            Self::TwoHandPinchStretch => "two_hand_pinch_stretch",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct SpatialTransform {
    pub yaw_rad: f32,
    pub pitch_rad: f32,
    pub roll_rad: f32,
    pub tx: f32,
    pub ty: f32,
    pub scale: f32,
}

impl Default for SpatialTransform {
    fn default() -> Self {
        Self {
            yaw_rad: 0.0,
            pitch_rad: 0.0,
            roll_rad: 0.0,
            tx: 0.0,
            ty: 0.0,
            scale: 1.0,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SpatialGestureIntent {
    pub gesture: SpatialGestureKind,
    pub shape: HologramShape,
    pub confidence: f32,
    pub hands_count: u8,
    pub requires_confirmation: bool,
    pub bound_action: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SpatialBinding {
    pub gesture: SpatialGestureKind,
    pub action: String,
    pub requires_confirmation: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SpatialHudState {
    pub camera_active: bool,
    pub person_present: bool,
    pub auto_close_timeout_ms: u64,
    pub last_presence_ms: u64,
    pub shape: HologramShape,
    pub active_gesture: SpatialGestureKind,
    pub transform: SpatialTransform,
    pub candidate_gesture: SpatialGestureKind,
    pub candidate_streak: u32,
    pub focus_latched: bool,
    pub baseline_span: f32,
    pub bindings: Vec<SpatialBinding>,
}

impl Default for SpatialHudState {
    fn default() -> Self {
        Self {
            camera_active: false,
            person_present: false,
            auto_close_timeout_ms: DEFAULT_AUTO_CLOSE_MS,
            last_presence_ms: 0,
            shape: HologramShape::Sphere,
            active_gesture: SpatialGestureKind::Idle,
            transform: SpatialTransform::default(),
            candidate_gesture: SpatialGestureKind::Idle,
            candidate_streak: 0,
            focus_latched: false,
            baseline_span: 0.0,
            bindings: Vec::new(),
        }
    }
}

#[must_use]
pub fn is_real_world_action(action: &str) -> bool {
    let lower = action.trim().to_ascii_lowercase();
    lower.starts_with("ha.")
        || lower.starts_with("home.")
        || lower.starts_with("system.")
        || lower.starts_with("device.")
        || lower.starts_with("light.")
        || lower.starts_with("lock.")
        || lower.starts_with("scene.run")
        || lower.starts_with("power.")
}

impl SpatialHudState {
    #[must_use]
    pub fn new(auto_close_timeout_ms: u64) -> Self {
        Self {
            auto_close_timeout_ms: auto_close_timeout_ms.clamp(500, 60_000),
            ..Self::default()
        }
    }

    #[must_use]
    pub const fn is_local_only(&self) -> bool {
        true
    }

    pub fn activate_camera(&mut self, timestamp_ms: u64) {
        self.camera_active = true;
        self.person_present = true;
        self.last_presence_ms = timestamp_ms;
    }

    pub fn shutdown_session(&mut self) {
        self.camera_active = false;
        self.person_present = false;
        self.active_gesture = SpatialGestureKind::Idle;
        self.candidate_gesture = SpatialGestureKind::Idle;
        self.candidate_streak = 0;
        self.focus_latched = false;
        self.baseline_span = 0.0;
        self.transform = SpatialTransform::default();
    }

    pub fn bind_action(
        &mut self,
        gesture: SpatialGestureKind,
        action: &str,
    ) -> Result<SpatialBinding, GestureError> {
        let clean = action.trim();
        if clean.is_empty() || clean.len() > 64 {
            return Err(GestureError::InvalidIdentifier(action.to_owned()));
        }
        let requires_confirmation = is_real_world_action(clean);
        let binding = SpatialBinding {
            gesture,
            action: clean.to_owned(),
            requires_confirmation,
        };
        self.bindings.retain(|b| b.gesture != gesture);
        self.bindings.push(binding.clone());
        Ok(binding)
    }

    pub fn step_frame(
        &mut self,
        hands: &[Hand],
        person_present: bool,
        timestamp_ms: u64,
    ) -> Option<SpatialGestureIntent> {
        if !self.camera_active {
            return None;
        }
        if person_present || !hands.is_empty() {
            self.person_present = true;
            self.last_presence_ms = timestamp_ms;
        } else if timestamp_ms.saturating_sub(self.last_presence_ms) >= self.auto_close_timeout_ms {
            self.shutdown_session();
            return None;
        }

        let detected = Self::classify_frame(hands);
        self.apply_debounce(detected);
        self.update_transform(hands);
        Some(self.build_intent(hands))
    }

    fn classify_frame(hands: &[Hand]) -> SpatialGestureKind {
        if let (Some(first), Some(second)) = (hands.first(), hands.get(1)) {
            let p1 = classify(first, first.pinch_ratio() < 0.35).0;
            let p2 = classify(second, second.pinch_ratio() < 0.35).0;
            if matches!(p1, Pose::Pinch | Pose::Fist | Pose::OpenPalm)
                && matches!(p2, Pose::Pinch | Pose::Fist | Pose::OpenPalm)
            {
                return SpatialGestureKind::TwoHandPinchStretch;
            }
        }
        let Some(hand) = hands.first() else {
            return SpatialGestureKind::Idle;
        };
        let (pose, _) = classify(hand, hand.pinch_ratio() < 0.35);
        match pose {
            Pose::OpenPalm => SpatialGestureKind::OpenPalmDisperse,
            Pose::Fist | Pose::Pinch => SpatialGestureKind::SingleHandFocusMorph,
            _ => SpatialGestureKind::WristRotationTilt,
        }
    }

    fn apply_debounce(&mut self, detected: SpatialGestureKind) {
        if detected == self.candidate_gesture {
            self.candidate_streak = self.candidate_streak.saturating_add(1);
        } else {
            self.candidate_gesture = detected;
            self.candidate_streak = 1;
        }
        if self.candidate_streak < DEBOUNCE_FRAMES {
            return;
        }
        self.active_gesture = detected;
        match detected {
            SpatialGestureKind::OpenPalmDisperse => {
                self.shape = HologramShape::Dispersed;
                self.focus_latched = false;
                self.baseline_span = 0.0;
            }
            SpatialGestureKind::SingleHandFocusMorph => {
                if !self.focus_latched {
                    self.shape = self.shape.next_focused();
                    self.focus_latched = true;
                }
                self.baseline_span = 0.0;
            }
            SpatialGestureKind::WristRotationTilt | SpatialGestureKind::Idle => {
                self.focus_latched = false;
                self.baseline_span = 0.0;
            }
            SpatialGestureKind::TwoHandPinchStretch => {
                self.focus_latched = false;
            }
        }
    }

    fn update_transform(&mut self, hands: &[Hand]) {
        if let (Some(first), Some(second)) = (hands.first(), hands.get(1))
            && self.active_gesture == SpatialGestureKind::TwoHandPinchStretch
        {
            let c1 = first.palm_center();
            let c2 = second.palm_center();
            let safe_span = c1.distance(c2).clamp(0.05, 1.5);
            if self.baseline_span <= 0.0 {
                self.baseline_span = safe_span;
            }
            let ratio = (safe_span / self.baseline_span).clamp(0.4, 2.8);
            self.transform.scale = self.transform.scale * 0.7 + ratio * 0.3;
            self.transform.roll_rad = (c2.y - c1.y).atan2(c2.x - c1.x);
            return;
        }
        let Some(hand) = hands.first() else {
            return;
        };
        let wrist = hand.at(Joint::Wrist);
        let middle = hand.at(Joint::MiddleMcp);
        let index = hand.at(Joint::IndexMcp);
        let pinky = hand.at(Joint::PinkyMcp);
        self.transform.yaw_rad = ((index.x - pinky.x) * 3.2).clamp(-3.141, 3.141);
        self.transform.pitch_rad = ((middle.y - wrist.y) * 3.2).clamp(-3.141, 3.141);
        self.transform.tx = (wrist.x - 0.5).clamp(-0.5, 0.5);
        self.transform.ty = (wrist.y - 0.5).clamp(-0.5, 0.5);
    }

    fn build_intent(&self, hands: &[Hand]) -> SpatialGestureIntent {
        let confidence = hands.first().map_or(0.0, |h| h.score.clamp(0.0, 1.0));
        let binding = self
            .bindings
            .iter()
            .find(|b| b.gesture == self.active_gesture);
        SpatialGestureIntent {
            gesture: self.active_gesture,
            shape: self.shape,
            confidence,
            hands_count: u8::try_from(hands.len()).unwrap_or(0),
            requires_confirmation: binding.is_some_and(|b| b.requires_confirmation),
            bound_action: binding.map(|b| b.action.clone()),
        }
    }
}
