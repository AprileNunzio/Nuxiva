#![forbid(unsafe_code)]

pub mod audience;
pub mod descriptor;
pub mod layout;
pub mod moves;

pub use audience::{Audience, RoomAudience};
pub use descriptor::{GpuCaps, InputCaps, RoomPose, SurfaceDescriptor, SurfaceKind};
pub use layout::{Direction, Layout, Neighbors};
pub use moves::{MoveGuard, MoveOrigin};

#[cfg(test)]
mod tests;
