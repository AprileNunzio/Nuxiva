#![forbid(unsafe_code)]

pub mod duo;
pub mod engine;
pub mod error;
pub mod events;
pub mod generative_3d;
pub mod gesture;
pub mod landmarks;
pub mod motion;
pub mod pointer;
pub mod pose;
pub mod profile;
pub mod smoothing;
pub mod spatial_hud;
pub mod wire;

pub use engine::GestureEngine;
pub use error::GestureError;
pub use events::{DuoPhase, GestureEvent, PointerPhase};
pub use generative_3d::{
    CsgPrimitiveKind, CsgPrimitiveNode, Generative3dAsset, PbrMaterialSpec, RenderFidelityTier,
    synthesize_procedural_3d,
};
pub use gesture::{Direction, GestureKind, Rotation};
pub use landmarks::{Frame, Hand, Handedness, Joint, LANDMARKS, Point};
pub use pose::Pose;
pub use profile::{Binding, GestureProfile, HandFilter};
pub use spatial_hud::{
    HologramShape, SpatialBinding, SpatialGestureIntent, SpatialGestureKind, SpatialHudState,
    SpatialTransform, is_real_world_action,
};

#[cfg(test)]
mod engine_tests;
