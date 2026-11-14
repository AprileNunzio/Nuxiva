use std::fmt;

#[derive(Debug)]
pub enum Error {
    Config(&'static str),
    Path(&'static str),
    Image(&'static str),
    Capture(&'static str),
    Sink(String),
    Io(std::io::Error),
}

impl Error {
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::Config(_) => "screenshot.error.config",
            Self::Path(_) => "screenshot.error.path",
            Self::Image(_) => "screenshot.error.image",
            Self::Capture(_) => "screenshot.error.capture",
            Self::Sink(_) => "screenshot.error.sink",
            Self::Io(_) => "screenshot.error.io",
        }
    }
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Config(m) | Self::Path(m) | Self::Image(m) | Self::Capture(m) => {
                write!(f, "{}: {m}", self.code())
            }
            Self::Sink(m) => write!(f, "{}: {m}", self.code()),
            Self::Io(e) => write!(f, "{}: {e}", self.code()),
        }
    }
}

impl std::error::Error for Error {}

impl From<std::io::Error> for Error {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}

pub type Result<T> = std::result::Result<T, Error>;
