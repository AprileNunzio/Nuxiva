use crate::error::GestureError;
use crate::pose::Pose;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Direction {
    Left,
    Right,
    Up,
    Down,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Rotation {
    Clockwise,
    CounterClockwise,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum DuoMotion {
    Spread,
    Squeeze,
    RotateClockwise,
    RotateCounterClockwise,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(try_from = "String", into = "String")]
pub enum GestureKind {
    Pose(Pose),
    Hold(Pose),
    Swipe(Direction),
    Circle(Rotation),
    Tap,
    DoubleTap,
    Duo(DuoMotion),
}

const DIRECTIONS: [(Direction, &str); 4] = [
    (Direction::Left, "left"),
    (Direction::Right, "right"),
    (Direction::Up, "up"),
    (Direction::Down, "down"),
];
const ROTATIONS: [(Rotation, &str); 2] = [
    (Rotation::Clockwise, "cw"),
    (Rotation::CounterClockwise, "ccw"),
];
const DUOS: [(DuoMotion, &str); 4] = [
    (DuoMotion::Spread, "spread"),
    (DuoMotion::Squeeze, "squeeze"),
    (DuoMotion::RotateClockwise, "rotate_cw"),
    (DuoMotion::RotateCounterClockwise, "rotate_ccw"),
];

fn name_of<T: PartialEq + Copy>(table: &[(T, &'static str)], value: T) -> &'static str {
    table
        .iter()
        .find(|(v, _)| *v == value)
        .map_or("", |(_, n)| n)
}

fn value_of<T: Copy>(table: &[(T, &'static str)], name: &str) -> Option<T> {
    table.iter().find(|(_, n)| *n == name).map(|(v, _)| *v)
}

impl GestureKind {
    #[must_use]
    pub fn id(self) -> String {
        match self {
            Self::Pose(p) => format!("pose.{}", p.id()),
            Self::Hold(p) => format!("hold.{}", p.id()),
            Self::Swipe(d) => format!("swipe.{}", name_of(&DIRECTIONS, d)),
            Self::Circle(r) => format!("circle.{}", name_of(&ROTATIONS, r)),
            Self::Tap => "tap".to_owned(),
            Self::DoubleTap => "double_tap".to_owned(),
            Self::Duo(m) => format!("duo.{}", name_of(&DUOS, m)),
        }
    }

    pub fn parse(id: &str) -> Result<Self, GestureError> {
        let unknown = || GestureError::UnknownGesture(id.chars().take(64).collect());
        let (family, name) = id.split_once('.').unwrap_or((id, ""));
        let parsed = match family {
            "pose" => Pose::from_id(name).map(Self::Pose),
            "hold" => Pose::from_id(name).map(Self::Hold),
            "swipe" => value_of(&DIRECTIONS, name).map(Self::Swipe),
            "circle" => value_of(&ROTATIONS, name).map(Self::Circle),
            "duo" => value_of(&DUOS, name).map(Self::Duo),
            "tap" if name.is_empty() => Some(Self::Tap),
            "double_tap" if name.is_empty() => Some(Self::DoubleTap),
            _ => None,
        };
        parsed.ok_or_else(unknown)
    }

    #[must_use]
    pub fn catalog() -> Vec<Self> {
        let mut all = Vec::new();
        for pose in Pose::ALL.into_iter().filter(|p| *p != Pose::Unknown) {
            all.push(Self::Pose(pose));
            all.push(Self::Hold(pose));
        }
        all.extend(DIRECTIONS.iter().map(|(d, _)| Self::Swipe(*d)));
        all.extend(ROTATIONS.iter().map(|(r, _)| Self::Circle(*r)));
        all.extend([Self::Tap, Self::DoubleTap]);
        all.extend(DUOS.iter().map(|(m, _)| Self::Duo(*m)));
        all
    }
}

impl TryFrom<String> for GestureKind {
    type Error = GestureError;

    fn try_from(value: String) -> Result<Self, Self::Error> {
        Self::parse(&value)
    }
}

impl From<GestureKind> for String {
    fn from(value: GestureKind) -> Self {
        value.id()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn catalog_roundtrips() -> Result<(), GestureError> {
        for kind in GestureKind::catalog() {
            assert_eq!(GestureKind::parse(&kind.id())?, kind);
        }
        Ok(())
    }

    #[test]
    fn rejects_unknown() {
        assert!(GestureKind::parse("pose.laser").is_err());
        assert!(GestureKind::parse("tap.extra").is_err());
        assert!(GestureKind::parse("").is_err());
    }
}
