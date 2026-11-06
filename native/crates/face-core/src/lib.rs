#![forbid(unsafe_code)]

mod book;
mod decide;
mod image;
mod liveness;
mod look;
mod marks;
mod quality;
mod threshold;
mod traits;
mod vector;

pub use book::{Entry, FaceBook, MARK_LIMIT, MAX_MARKS, Report, Settings};
pub use decide::{Pair, Rules, Verdict, decide, fuse, pair};
pub use image::{Gray, ImageError, MAX_SIDE, ramp};
pub use liveness::{Aliveness, LivenessTracker, planar_residual};
pub use look::{HAIR_COLORS, KINDS, LookError, LookEvent, LookMemory, LookSample, LookSummary};
pub use marks::{MARKS_DIM, Mark, distinctive, mean_signature, pair_scores, signature};
pub use quality::{Landmarks, Light, Pose, Quality, assess, frame_issues, light, sharpness};
pub use threshold::{FLOOR_DELTA, GENUINE_SLACK, MIN_FOR_STATS, person_threshold, spread};
pub use traits::{Traits, traits};
pub use vector::{
    MAX_DIM, MAX_ROWS, MIN_DIM, RowsError, centroid, decode_raw, decode_rows, dot, encode_rows,
    leave_one_out, merge, norm, prune, redundancy, score_against, unit,
};

#[cfg(test)]
mod tests;
#[cfg(test)]
mod tests_look;
