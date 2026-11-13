pub const DEFAULT_SENSITIVE: &[&str] = &[
    "1password",
    "bitwarden",
    "keepass",
    "lastpass",
    "dashlane",
    "proton pass",
    "keychain",
    "password",
    "passcode",
    "banca",
    "bank",
    "paypal",
    "iban",
    "wallet",
    "carta di credito",
    "credit card",
    "home banking",
    "tax",
    "spid",
    "cie id",
    "otp",
    "authenticator",
    "private",
    "incognito",
    "navigazione in incognito",
];

const MAX_PATTERNS: usize = 256;
const MAX_PATTERN: usize = 64;
const MAX_CAPACITY: usize = 4096;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Rejection {
    NoConsent,
    Sensitive,
    TooSoon,
    Invalid,
}

impl Rejection {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::NoConsent => "vision.no_consent",
            Self::Sensitive => "vision.sensitive",
            Self::TooSoon => "vision.too_soon",
            Self::Invalid => "vision.invalid",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Policy {
    pub consent: bool,
    pub interval_ms: u64,
    pub ttl_ms: u64,
    pub capacity: usize,
    pub(crate) patterns: Vec<String>,
}

impl Default for Policy {
    fn default() -> Self {
        Self {
            consent: false,
            interval_ms: 2_000,
            ttl_ms: 5 * 60_000,
            capacity: 256,
            patterns: DEFAULT_SENSITIVE.iter().map(|s| (*s).to_owned()).collect(),
        }
    }
}

impl Policy {
    #[must_use]
    pub fn sanitized(mut self) -> Self {
        self.interval_ms = self.interval_ms.clamp(250, 600_000);
        self.ttl_ms = self.ttl_ms.clamp(5_000, 3_600_000);
        self.capacity = self.capacity.clamp(8, MAX_CAPACITY);
        self
    }

    pub fn add_sensitive(&mut self, pattern: &str) -> bool {
        let p = pattern.trim().to_lowercase();
        if p.is_empty()
            || p.chars().count() > MAX_PATTERN
            || self.patterns.len() >= MAX_PATTERNS
            || self.patterns.contains(&p)
        {
            return false;
        }
        self.patterns.push(p);
        true
    }

    #[must_use]
    pub fn is_sensitive(&self, app: &str, title: &str) -> bool {
        let hay = format!("{} {}", app.to_lowercase(), title.to_lowercase());
        self.patterns.iter().any(|p| hay.contains(p.as_str()))
    }
}

impl Policy {
    #[must_use]
    pub fn new(consent: bool, interval_ms: u64, ttl_ms: u64, capacity: usize) -> Self {
        Self {
            consent,
            interval_ms,
            ttl_ms,
            capacity,
            ..Self::default()
        }
        .sanitized()
    }
}
