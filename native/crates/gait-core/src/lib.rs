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
    evaluate_match, find_best_match, format_day_month_en, format_day_month_it, format_time_hh_mm,
    GaitMatch, ReferenceGait, MIN_CONFIDENCE_THRESHOLD, SIMILARITY_THRESHOLD,
};
pub use observation::GaitObservation;
pub use signature::{GaitSignature, GAIT_DIM};
