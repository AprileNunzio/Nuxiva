use model_router::Sensitivity;

pub const MAX_TEXT_BYTES: usize = 768;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Platform {
    Windows,
    MacOs,
    Android,
    Linux,
    Other,
}

impl Platform {
    #[must_use]
    pub fn parse(name: &str) -> Self {
        match name.trim().to_ascii_lowercase().as_str() {
            "windows" => Self::Windows,
            "macos" | "darwin" | "osx" => Self::MacOs,
            "android" => Self::Android,
            "linux" => Self::Linux,
            _ => Self::Other,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Node {
    pub id: String,
    pub platform: Platform,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Input<'a> {
    pub text: &'a str,
    pub sensitivity: Sensitivity,
    pub attachments: Attachments,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Attachments(u8);

impl Attachments {
    pub const NONE: Self = Self(0);
    pub const IMAGE: Self = Self(1);
    pub const RESULTS: Self = Self(2);
    pub const RESEARCH: Self = Self(4);
    pub const CONTEXT: Self = Self(8);

    #[must_use]
    pub fn with(self, other: Self) -> Self {
        Self(self.0 | other.0)
    }

    #[must_use]
    pub fn any(self) -> bool {
        self.0 != 0
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Unavailable;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Reason {
    NoKey,
    NodeNotEnabled,
    UnsupportedPlatform,
    TooLong,
    RichInput,
    NotPublic,
    BreakerOpen,
    NotSimple,
    Unavailable,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Route {
    Jev,
    Deep(Reason),
}

pub trait Classifier {
    fn is_simple(&mut self, text: &str) -> Result<bool, Unavailable>;
}
