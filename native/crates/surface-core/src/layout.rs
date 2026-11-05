use serde::{Deserialize, Serialize};

use crate::descriptor::SurfaceDescriptor;

const MAX_ANGLE_COS: f32 = 0.5;
pub const MAX_SCREENS: usize = 17;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Direction {
    Left,
    Right,
    Up,
    Down,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct Neighbors {
    pub left: Option<u8>,
    pub right: Option<u8>,
    pub up: Option<u8>,
    pub down: Option<u8>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Screen {
    pub n: u8,
    #[serde(default)]
    pub x: i32,
    #[serde(default)]
    pub surface: SurfaceDescriptor,
}

#[derive(Debug, Clone, PartialEq, Default)]
pub struct Layout {
    screens: Vec<Screen>,
}

impl Layout {
    #[must_use]
    pub fn new(mut screens: Vec<Screen>) -> Self {
        screens.retain(|s| s.surface.sane() && usize::from(s.n) < MAX_SCREENS);
        screens.sort_by_key(|s| (s.x, s.n));
        screens.dedup_by_key(|s| s.n);
        Self { screens }
    }

    fn get(&self, n: u8) -> Option<&Screen> {
        self.screens.iter().find(|s| s.n == n)
    }

    fn physical(&self, from: &Screen, dir: Direction) -> Option<u8> {
        let a = from.surface.placement.as_ref()?;
        let yaw = a.yaw_deg.to_radians();
        let (rx, ry) = (yaw.cos(), -yaw.sin());
        self.screens
            .iter()
            .filter(|s| s.n != from.n)
            .filter_map(|s| {
                let b = s.surface.placement.as_ref().filter(|b| b.room == a.room)?;
                let (dx, dy, dz) = (b.x_m - a.x_m, b.y_m - a.y_m, b.z_m - a.z_m);
                let side = dx * rx + dy * ry;
                let distance = (dx * dx + dy * dy + dz * dz).sqrt();
                if distance < 1e-3 {
                    return None;
                }
                let along = match dir {
                    Direction::Right => side,
                    Direction::Left => -side,
                    Direction::Up => dz,
                    Direction::Down => -dz,
                };
                (along / distance >= MAX_ANGLE_COS).then_some((distance, s.n))
            })
            .min_by(|a, b| a.0.total_cmp(&b.0))
            .map(|(_, n)| n)
    }

    fn ordered(&self, from: &Screen, dir: Direction) -> Option<u8> {
        let index = self.screens.iter().position(|s| s.n == from.n)?;
        let pick = match dir {
            Direction::Left => index.checked_sub(1),
            Direction::Right => index.checked_add(1),
            Direction::Up | Direction::Down => None,
        }?;
        self.screens.get(pick).map(|s| s.n)
    }

    #[must_use]
    pub fn neighbor(&self, from: u8, dir: Direction) -> Option<u8> {
        let screen = self.get(from)?;
        if screen.surface.placement.is_some() {
            self.physical(screen, dir)
        } else {
            self.ordered(screen, dir)
        }
    }

    #[must_use]
    pub fn neighbors(&self, from: u8) -> Neighbors {
        Neighbors {
            left: self.neighbor(from, Direction::Left),
            right: self.neighbor(from, Direction::Right),
            up: self.neighbor(from, Direction::Up),
            down: self.neighbor(from, Direction::Down),
        }
    }

    #[must_use]
    pub fn room_of(&self, n: u8) -> Option<&str> {
        self.get(n)?
            .surface
            .placement
            .as_ref()
            .map(|p| p.room.as_str())
    }

    #[must_use]
    pub fn numbers(&self) -> Vec<u8> {
        self.screens.iter().map(|s| s.n).collect()
    }
}
