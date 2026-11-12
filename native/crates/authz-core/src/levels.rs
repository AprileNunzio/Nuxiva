#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Risk {
    Info = 0,
    Home = 1,
    Personal = 2,
    Files = 3,
    Critical = 4,
}

impl Risk {
    pub const ALL: [Self; 5] = [
        Self::Info,
        Self::Home,
        Self::Personal,
        Self::Files,
        Self::Critical,
    ];

    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::Info => "info",
            Self::Home => "home",
            Self::Personal => "personal",
            Self::Files => "files",
            Self::Critical => "critical",
        }
    }

    #[must_use]
    pub fn parse(text: &str) -> Option<Self> {
        let wanted = text.trim().to_lowercase();
        Self::ALL.into_iter().find(|r| r.name() == wanted)
    }

    #[must_use]
    pub fn from_level(level: u8) -> Option<Self> {
        Self::ALL.into_iter().find(|r| *r as u8 == level)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Strength {
    None = 0,
    Weak = 1,
    Single = 2,
    Strong = 3,
}

impl Strength {
    pub const ALL: [Self; 4] = [Self::None, Self::Weak, Self::Single, Self::Strong];

    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::Weak => "weak",
            Self::Single => "single",
            Self::Strong => "strong",
        }
    }

    #[must_use]
    pub fn parse_upper(text: &str) -> Option<Self> {
        let wanted = text.to_uppercase();
        Self::ALL
            .into_iter()
            .find(|s| s.name().to_uppercase() == wanted)
    }

    #[must_use]
    pub fn from_level(level: u8) -> Option<Self> {
        Self::ALL.into_iter().find(|s| *s as u8 == level)
    }
}
