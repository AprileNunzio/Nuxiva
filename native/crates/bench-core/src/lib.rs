#![forbid(unsafe_code)]

mod barge;
mod cli;
mod error;
mod fsio;
mod latency;
mod ledger;
mod observations;
mod report;
mod scene;
mod speaker;
mod stats;
mod synth;
mod thresholds;
mod wake;
mod wer;

pub use barge::{BargeReport, BargeTrial};
pub use cli::{EXIT_FAIL, EXIT_INSUFFICIENT, EXIT_PASS, EXIT_WARN, Outcome, execute, verdict_code};
pub use error::{BenchError, BenchResult};
pub use fsio::{MAX_FILE_BYTES, read_limited, write_atomic};
pub use latency::{LatencyReport, STAGES, StageTimes};
pub use ledger::{Criteria, Entry, Kind, Ledger, Status};
pub use observations::{Observations, SCHEMA, Source, UtteranceObs, is_token};
pub use report::{BenchReport, Regression, Severity, Violation, compare, run};
pub use scene::{Background, Class};
pub use speaker::{SpeakerReport, SpeakerTrial};
pub use stats::{Summary, summarize};
pub use synth::{Profile, SENTENCES, Scale, generate};
pub use thresholds::{Limit, SECTIONS, Thresholds, Tolerance};
pub use wake::{WakeReport, WakeTrial};
pub use wer::{Ops, WerReport, align, tokens};

pub mod stats_api {
    pub use crate::stats::{count_f, ratio, u64_f64};
}

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::cast_possible_truncation,
    clippy::float_cmp,
    clippy::needless_range_loop,
    clippy::manual_assert_eq,
    clippy::cast_sign_loss,
    clippy::cast_precision_loss,
    clippy::too_many_lines
)]
mod tests;
