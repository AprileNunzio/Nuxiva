use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{OnceLock, RwLock};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Category {
    Safety,
    Conversation,
    Personal,
    Home,
    Work,
    Media,
    Info,
    System,
    Ambient,
}

impl Category {
    #[must_use]
    pub const fn weight(self) -> f32 {
        match self {
            Self::Safety => 1.0,
            Self::Conversation => 0.95,
            Self::Personal => 0.85,
            Self::Home => 0.75,
            Self::Work => 0.7,
            Self::Media => 0.65,
            Self::Info => 0.5,
            Self::System => 0.4,
            Self::Ambient => 0.2,
        }
    }
}

pub const MAX_WIDGETS: usize = 4096;
pub const MAX_ID: usize = 64;

impl Category {
    #[must_use]
    pub fn parse(raw: &str) -> Option<Self> {
        match raw.trim() {
            "safety" => Some(Self::Safety),
            "conversation" => Some(Self::Conversation),
            "personal" => Some(Self::Personal),
            "home" => Some(Self::Home),
            "work" => Some(Self::Work),
            "media" => Some(Self::Media),
            "info" => Some(Self::Info),
            "system" => Some(Self::System),
            "ambient" => Some(Self::Ambient),
            _ => None,
        }
    }
}

static REGISTRY: OnceLock<RwLock<HashMap<String, Category>>> = OnceLock::new();

fn registry() -> &'static RwLock<HashMap<String, Category>> {
    REGISTRY.get_or_init(|| RwLock::new(HashMap::new()))
}

fn valid_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= MAX_ID
        && id
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_' || b == b'-')
}

pub fn build<I>(entries: I) -> HashMap<String, Category>
where
    I: IntoIterator<Item = (String, Category)>,
{
    entries
        .into_iter()
        .filter(|(id, _)| valid_id(id))
        .take(MAX_WIDGETS)
        .collect()
}

pub fn register<I>(entries: I) -> usize
where
    I: IntoIterator<Item = (String, Category)>,
{
    let next = build(entries);
    let count = next.len();
    if let Ok(mut guard) = registry().write() {
        *guard = next;
    }
    count
}

#[must_use]
pub fn category_of(widget: &str) -> Category {
    registry()
        .read()
        .ok()
        .and_then(|map| map.get(widget).copied())
        .unwrap_or(Category::Info)
}

#[must_use]
pub fn known_widgets() -> Vec<String> {
    registry()
        .read()
        .map(|map| {
            let mut ids: Vec<String> = map.keys().cloned().collect();
            ids.sort();
            ids
        })
        .unwrap_or_default()
}
