#![forbid(unsafe_code)]

mod buffer;
mod cadence;
pub mod chromatic;
mod policy;
pub mod recognition;

pub use buffer::{
    FrameMeta, Hit, Indicator, MAX_DIM, MAX_FRAMES, PushOutcome, Source, VisualBuffer,
};
pub use cadence::{Cadence, THUMB_H, THUMB_W, Verdict, dhash};
pub use policy::{DEFAULT_SENSITIVE, Policy, Rejection};
pub use recognition::{
    BoundingBox, CHROMATIC_BINS, ColorPaletteProfile, DetectedObject, MAX_ACTIVE_TRACKS,
    MAX_OBJECT_PROTOTYPES, OBJECT_MATCH_THRESHOLD_BPS, PERSON_REID_THRESHOLD_BPS,
    PersonIdentityMatch, PersonVisualObservation, RgbSample, SemanticColor,
    VisualRecognitionEngine, classify_rgb_pixel, extract_color_palette,
};

#[cfg(test)]
mod tests;
#[cfg(test)]
#[allow(clippy::arithmetic_side_effects)]
mod tests_cadence;
