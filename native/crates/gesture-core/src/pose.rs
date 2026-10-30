use crate::landmarks::{Hand, Joint};
use serde::{Deserialize, Serialize};

const FINGER_PIVOT: f32 = 1.1;
const THUMB_PIVOT: f32 = 0.9;
const SCORE_SPAN: f32 = 0.3;
const THUMB_TILT: f32 = 0.3;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Pose {
    OpenPalm,
    Fist,
    Point,
    Victory,
    Three,
    Four,
    RockOn,
    CallMe,
    ThumbsUp,
    ThumbsDown,
    Pinch,
    OkSign,
    Unknown,
}

impl Pose {
    pub const ALL: [Self; 13] = [
        Self::OpenPalm,
        Self::Fist,
        Self::Point,
        Self::Victory,
        Self::Three,
        Self::Four,
        Self::RockOn,
        Self::CallMe,
        Self::ThumbsUp,
        Self::ThumbsDown,
        Self::Pinch,
        Self::OkSign,
        Self::Unknown,
    ];

    #[must_use]
    pub const fn id(self) -> &'static str {
        match self {
            Self::OpenPalm => "open_palm",
            Self::Fist => "fist",
            Self::Point => "point",
            Self::Victory => "victory",
            Self::Three => "three",
            Self::Four => "four",
            Self::RockOn => "rock_on",
            Self::CallMe => "call_me",
            Self::ThumbsUp => "thumbs_up",
            Self::ThumbsDown => "thumbs_down",
            Self::Pinch => "pinch",
            Self::OkSign => "ok_sign",
            Self::Unknown => "unknown",
        }
    }

    #[must_use]
    pub fn from_id(id: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|pose| pose.id() == id)
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct FingerState {
    pub scores: [f32; 5],
}

impl FingerState {
    #[must_use]
    pub fn of(hand: &Hand) -> Self {
        let wrist = hand.at(Joint::Wrist);
        let finger = |pip: Joint, tip: Joint| {
            let reach = wrist.distance(hand.at(pip)).max(1e-4);
            ((wrist.distance(hand.at(tip)) / reach - FINGER_PIVOT) / SCORE_SPAN).clamp(-1.0, 1.0)
        };
        let pinky_base = hand.at(Joint::PinkyMcp);
        let thumb_reach = hand.at(Joint::ThumbMcp).distance(pinky_base).max(1e-4);
        let thumb = ((hand.at(Joint::ThumbTip).distance(pinky_base) / thumb_reach - THUMB_PIVOT)
            / SCORE_SPAN)
            .clamp(-1.0, 1.0);
        Self {
            scores: [
                thumb,
                finger(Joint::IndexPip, Joint::IndexTip),
                finger(Joint::MiddlePip, Joint::MiddleTip),
                finger(Joint::RingPip, Joint::RingTip),
                finger(Joint::PinkyPip, Joint::PinkyTip),
            ],
        }
    }

    #[must_use]
    pub fn extended(&self) -> [bool; 5] {
        self.scores.map(|s| s > 0.0)
    }

    #[must_use]
    pub fn certainty(&self) -> f32 {
        self.scores.iter().map(|s| s.abs()).sum::<f32>() / 5.0
    }
}

const INDEX_ENGAGED: f32 = -0.8;

#[must_use]
pub fn effective_pinch_ratio(hand: &Hand) -> f32 {
    let index = FingerState::of(hand).scores.get(1).copied().unwrap_or(-1.0);
    if index > INDEX_ENGAGED {
        hand.pinch_ratio()
    } else {
        f32::MAX
    }
}

fn thumb_direction(hand: &Hand) -> Pose {
    let rise = hand.at(Joint::ThumbMcp).y - hand.at(Joint::ThumbTip).y;
    let limit = hand.palm_size() * THUMB_TILT;
    if rise > limit {
        Pose::ThumbsUp
    } else if rise < -limit {
        Pose::ThumbsDown
    } else {
        Pose::Unknown
    }
}

#[must_use]
pub fn classify(hand: &Hand, pinching: bool) -> (Pose, f32) {
    let fingers = FingerState::of(hand);
    let confidence = (fingers.certainty() * hand.score).clamp(0.0, 1.0);
    let [thumb, index, middle, ring, pinky] = fingers.extended();
    if pinching {
        let pose = if middle && ring && pinky {
            Pose::OkSign
        } else {
            Pose::Pinch
        };
        return (pose, hand.score);
    }
    let pose = match (thumb, index, middle, ring, pinky) {
        (true, true, true, true, true) => Pose::OpenPalm,
        (false, true, true, true, true) => Pose::Four,
        (false, false, false, false, false) => Pose::Fist,
        (true, false, false, false, false) => thumb_direction(hand),
        (_, true, false, false, false) => Pose::Point,
        (_, true, true, false, false) => Pose::Victory,
        (_, true, true, true, false) => Pose::Three,
        (_, true, false, false, true) => Pose::RockOn,
        (true, false, false, false, true) => Pose::CallMe,
        _ => Pose::Unknown,
    };
    (pose, confidence)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::error::GestureError;
    use crate::landmarks::fixtures::shaped;
    use crate::landmarks::{Handedness, Point};

    fn pose_of(fingers: [bool; 5]) -> Result<Pose, GestureError> {
        Ok(classify(
            &shaped(fingers, Point::new(0.5, 0.5), Handedness::Right)?,
            false,
        )
        .0)
    }

    #[test]
    fn classifies_finger_patterns() -> Result<(), GestureError> {
        assert_eq!(pose_of([true, true, true, true, true])?, Pose::OpenPalm);
        assert_eq!(pose_of([false, false, false, false, false])?, Pose::Fist);
        assert_eq!(pose_of([false, true, false, false, false])?, Pose::Point);
        assert_eq!(pose_of([false, true, true, false, false])?, Pose::Victory);
        assert_eq!(pose_of([false, true, true, true, false])?, Pose::Three);
        assert_eq!(pose_of([false, true, true, true, true])?, Pose::Four);
        assert_eq!(pose_of([false, true, false, false, true])?, Pose::RockOn);
        assert_eq!(pose_of([true, false, false, false, true])?, Pose::CallMe);
        assert_eq!(pose_of([true, false, false, false, false])?, Pose::ThumbsUp);
        Ok(())
    }

    #[test]
    fn pinch_flag_wins() -> Result<(), GestureError> {
        let hand = shaped(
            [true, true, true, true, true],
            Point::new(0.5, 0.5),
            Handedness::Left,
        )?;
        assert_eq!(classify(&hand, true).0, Pose::OkSign);
        let fist = shaped([false; 5], Point::new(0.5, 0.5), Handedness::Left)?;
        assert_eq!(classify(&fist, true).0, Pose::Pinch);
        Ok(())
    }

    #[test]
    fn ids_roundtrip() {
        for pose in Pose::ALL {
            assert_eq!(Pose::from_id(pose.id()), Some(pose));
        }
    }
}
