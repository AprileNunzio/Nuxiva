#![forbid(unsafe_code)]

mod clock;
mod lrc;

pub use clock::{ClockReading, JUMP_MS, MAX_OBSERVATIONS, SongClock};
pub use lrc::{LyricLine, LyricWord, MAX_INPUT, MAX_LINES, MAX_TEXT, MAX_WORDS, parse};

#[cfg(test)]
mod tests;
