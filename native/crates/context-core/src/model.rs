use serde::{Deserialize, Serialize};

use crate::error::{ContextError, ContextResult};
use crate::id::PersonId;
use crate::seal::Sealed;
use crate::settings::ContextSettings;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Role {
    Family,
    Guest,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Affect {
    pub valence: i16,
    pub arousal: u16,
    pub at_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Relation {
    pub kind: String,
    #[serde(default)]
    pub with: Option<PersonId>,
    #[serde(default)]
    pub name: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Custom {
    pub key: String,
    pub value: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Listen {
    pub title: String,
    pub artist: String,
    pub at_ms: u64,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Prefs {
    pub food_likes: Vec<String>,
    pub food_dislikes: Vec<String>,
    pub drinks: Vec<String>,
    pub music: Vec<String>,
    pub movies: Vec<String>,
    pub sports: Vec<String>,
    pub hobbies: Vec<String>,
    pub coffee: Option<String>,
    pub custom: Vec<Custom>,
}

fn yes() -> bool {
    true
}

#[derive(Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Person {
    pub id: PersonId,
    pub name: String,
    pub role: Role,
    #[serde(default = "yes")]
    pub consent: bool,
    #[serde(default)]
    pub share_health: bool,
    #[serde(default)]
    pub nickname: Option<String>,
    #[serde(default)]
    pub age: Option<u16>,
    #[serde(default)]
    pub work: Option<String>,
    #[serde(default)]
    pub notes: Option<String>,
    #[serde(default)]
    pub habits: Option<String>,
    #[serde(default)]
    pub languages: Vec<String>,
    #[serde(default)]
    pub relations: Vec<Relation>,
    #[serde(default)]
    pub prefs: Prefs,
    #[serde(default)]
    pub listening: Vec<Listen>,
    #[serde(default)]
    pub today: Vec<String>,
    #[serde(default)]
    pub affect: Option<Affect>,
    #[serde(default)]
    pub vitals: Option<Sealed>,
    #[serde(default)]
    pub stale: bool,
}

impl std::fmt::Debug for Person {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Person(..)")
    }
}

fn clean(text: &str, max: usize) -> ContextResult<()> {
    if text.chars().count() > max {
        return Err(ContextError::TooLarge);
    }
    if text.chars().any(char::is_control) {
        return Err(ContextError::Invalid);
    }
    Ok(())
}

fn clean_list(items: &[String], settings: &ContextSettings) -> ContextResult<()> {
    if items.len() > settings.max_list_items {
        return Err(ContextError::TooLarge);
    }
    items
        .iter()
        .try_for_each(|i| clean(i, settings.max_text_chars))
}

fn clean_opt(item: Option<&String>, settings: &ContextSettings) -> ContextResult<()> {
    item.map_or(Ok(()), |t| clean(t, settings.max_text_chars))
}

impl Person {
    pub fn validate(&self, settings: &ContextSettings) -> ContextResult<()> {
        let max = settings.max_text_chars;
        clean(&self.name, max)?;
        if self.name.trim().is_empty() {
            return Err(ContextError::Invalid);
        }
        clean_opt(self.nickname.as_ref(), settings)?;
        clean_opt(self.work.as_ref(), settings)?;
        clean_opt(self.notes.as_ref(), settings)?;
        clean_opt(self.habits.as_ref(), settings)?;
        clean_opt(self.prefs.coffee.as_ref(), settings)?;
        if self.age.is_some_and(|a| a > 150) {
            return Err(ContextError::Invalid);
        }
        let prefs = &self.prefs;
        for list in [
            &self.languages,
            &self.today,
            &prefs.food_likes,
            &prefs.food_dislikes,
            &prefs.drinks,
            &prefs.music,
            &prefs.movies,
            &prefs.sports,
            &prefs.hobbies,
        ] {
            clean_list(list, settings)?;
        }
        if prefs.custom.len() > settings.max_list_items
            || self.relations.len() > settings.max_relations
        {
            return Err(ContextError::TooLarge);
        }
        for custom in &prefs.custom {
            clean(&custom.key, max)?;
            clean(&custom.value, max)?;
        }
        for relation in &self.relations {
            clean(&relation.kind, max)?;
            clean_opt(relation.name.as_ref(), settings)?;
            if relation.with.is_none() && relation.name.is_none() {
                return Err(ContextError::Invalid);
            }
        }
        if self.listening.len() > settings.max_listening {
            return Err(ContextError::TooLarge);
        }
        for listen in &self.listening {
            clean(&listen.title, max)?;
            clean(&listen.artist, max)?;
        }
        if let Some(affect) = &self.affect {
            if !(-1000..=1000).contains(&affect.valence) || affect.arousal > 1000 {
                return Err(ContextError::Invalid);
            }
        }
        if let Some(sealed) = &self.vitals {
            if sealed.nonce.len() != crate::seal::NONCE_LEN
                || sealed.data.len() > settings.max_sealed_bytes
            {
                return Err(ContextError::Invalid);
            }
        }
        Ok(())
    }

    #[must_use]
    pub fn approx_bytes(&self) -> usize {
        let text = |s: &String| s.len();
        let list = |v: &Vec<String>| v.iter().map(text).fold(0_usize, usize::saturating_add);
        let prefs = &self.prefs;
        let parts = [
            std::mem::size_of::<Self>(),
            self.name.len(),
            self.nickname.as_ref().map_or(0, text),
            self.work.as_ref().map_or(0, text),
            self.notes.as_ref().map_or(0, text),
            self.habits.as_ref().map_or(0, text),
            list(&self.languages),
            list(&self.today),
            list(&prefs.food_likes),
            list(&prefs.food_dislikes),
            list(&prefs.drinks),
            list(&prefs.music),
            list(&prefs.movies),
            list(&prefs.sports),
            list(&prefs.hobbies),
            prefs
                .custom
                .iter()
                .map(|c| c.key.len().saturating_add(c.value.len()))
                .fold(0_usize, usize::saturating_add),
            self.relations
                .iter()
                .map(|r| r.kind.len().saturating_add(64))
                .fold(0_usize, usize::saturating_add),
            self.listening
                .iter()
                .map(|l| {
                    l.title
                        .len()
                        .saturating_add(l.artist.len())
                        .saturating_add(8)
                })
                .fold(0_usize, usize::saturating_add),
            self.vitals
                .as_ref()
                .map_or(0, |s| s.nonce.len().saturating_add(s.data.len())),
        ];
        parts.into_iter().fold(0_usize, usize::saturating_add)
    }
}
