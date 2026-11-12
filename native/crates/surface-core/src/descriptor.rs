use serde::{Deserialize, Serialize};

pub const MAX_ROOM: usize = 48;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SurfaceKind {
    #[default]
    Monitor,
    XrHeadset,
    HoloQuilt,
    HoloPyramid,
    HoloFan,
    Cast,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
#[allow(clippy::struct_excessive_bools)]
pub struct InputCaps {
    pub touch: bool,
    pub pointer: bool,
    pub hands: bool,
    pub gaze: bool,
    pub keyboard: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct GpuCaps {
    pub webgl2: bool,
    pub max_texture: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RoomPose {
    pub room: String,
    pub x_m: f32,
    pub y_m: f32,
    #[serde(default)]
    pub z_m: f32,
    #[serde(default)]
    pub yaw_deg: f32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct SurfaceDescriptor {
    pub kind: SurfaceKind,
    pub width: u32,
    pub height: u32,
    pub refresh_hz: u16,
    pub stereo: bool,
    pub field_of_view_deg: Option<f32>,
    pub views: u16,
    pub input: InputCaps,
    pub gpu: GpuCaps,
    pub placement: Option<RoomPose>,
}

impl Default for SurfaceDescriptor {
    fn default() -> Self {
        Self {
            kind: SurfaceKind::Monitor,
            width: 1920,
            height: 1080,
            refresh_hz: 60,
            stereo: false,
            field_of_view_deg: None,
            views: 1,
            input: InputCaps::default(),
            gpu: GpuCaps::default(),
            placement: None,
        }
    }
}

#[must_use]
pub fn valid_room(room: &str) -> bool {
    !room.is_empty()
        && room.len() <= MAX_ROOM
        && room
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_' || b == b'-')
}

impl RoomPose {
    #[must_use]
    pub fn sane(&self) -> bool {
        valid_room(&self.room)
            && [self.x_m, self.y_m, self.z_m]
                .iter()
                .all(|v| v.is_finite() && v.abs() <= 100.0)
            && self.yaw_deg.is_finite()
            && self.yaw_deg.abs() <= 360.0
    }
}

impl SurfaceDescriptor {
    #[must_use]
    pub fn sane(&self) -> bool {
        (1..=16_384).contains(&self.width)
            && (1..=16_384).contains(&self.height)
            && (1..=500).contains(&self.refresh_hz)
            && (1..=256).contains(&self.views)
            && self
                .field_of_view_deg
                .is_none_or(|f| f.is_finite() && (1.0..=360.0).contains(&f))
            && self.gpu.max_texture <= 65_536
            && self.placement.as_ref().is_none_or(RoomPose::sane)
    }

    #[must_use]
    pub fn aspect(&self) -> f32 {
        #[allow(clippy::cast_precision_loss)]
        let ratio = self.width as f32 / self.height.max(1) as f32;
        ratio
    }
}
