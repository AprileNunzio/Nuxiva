mod error;
mod extract;
mod match_eval;
mod observation;
mod signature;

#[cfg(test)]
mod tests;

pub use error::GaitError;
pub use extract::extract_signature;
pub use match_eval::{
    GaitMatch, MIN_CONFIDENCE_THRESHOLD, ReferenceGait, SIMILARITY_THRESHOLD, evaluate_match,
    find_best_match, format_day_month_en, format_day_month_it, format_time_hh_mm,
};
pub use observation::GaitObservation;
pub use signature::{GAIT_DIM, GaitSignature};
