use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WakeError {
    TooFewRecordings,
    TooManyRecordings,
    RecordingLength(usize),
    NoSpeech(usize),
    Inconsistent(usize),
    Model,
    Checksum,
    Config,
}

impl fmt::Display for WakeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::TooFewRecordings => f.write_str("wake.error.too_few_recordings"),
            Self::TooManyRecordings => f.write_str("wake.error.too_many_recordings"),
            Self::RecordingLength(i) => write!(f, "wake.error.recording_length:{i}"),
            Self::NoSpeech(i) => write!(f, "wake.error.no_speech:{i}"),
            Self::Inconsistent(i) => write!(f, "wake.error.inconsistent:{i}"),
            Self::Model => f.write_str("wake.error.model"),
            Self::Checksum => f.write_str("wake.error.checksum"),
            Self::Config => f.write_str("wake.error.config"),
        }
    }
}

impl std::error::Error for WakeError {}

pub type WakeResult<T> = Result<T, WakeError>;
