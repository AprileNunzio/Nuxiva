#![forbid(unsafe_code)]

mod book;
mod decide;
mod threshold;
mod vector;

pub use book::{Entry, FaceBook, Report, Settings};
pub use decide::{Pair, Rules, Verdict, decide, fuse, pair};
pub use threshold::{FLOOR_DELTA, GENUINE_SLACK, MIN_FOR_STATS, person_threshold, spread};
pub use vector::{
    MAX_DIM, MAX_ROWS, MIN_DIM, RowsError, centroid, decode_rows, dot, encode_rows, leave_one_out,
    merge, norm, prune, redundancy, score_against, unit,
};

#[cfg(test)]
mod tests;
