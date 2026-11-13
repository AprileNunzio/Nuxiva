use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::model::{Person, Role};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FieldKey {
    Identity,
    Relations,
    Work,
    Food,
    Drinks,
    Music,
    Movies,
    Sports,
    Hobbies,
    Custom,
    Listening,
    Mood,
    Today,
    Allergies,
    Diet,
    Notes,
    Habits,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Audience {
    Anyone,
    Family,
    SelfOnly,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Policy {
    pub audience: BTreeMap<FieldKey, Audience>,
    pub health: Vec<FieldKey>,
    pub safety: Vec<FieldKey>,
}

impl Default for Policy {
    fn default() -> Self {
        use FieldKey::{
            Allergies, Custom, Diet, Drinks, Food, Habits, Hobbies, Identity, Listening, Mood,
            Movies, Music, Notes, Relations, Sports, Today, Work,
        };
        let family = [
            Relations, Work, Food, Drinks, Music, Movies, Sports, Hobbies, Custom, Listening, Mood,
            Today, Allergies, Diet, Notes, Habits,
        ];
        let mut audience: BTreeMap<FieldKey, Audience> =
            family.iter().map(|k| (*k, Audience::Family)).collect();
        audience.insert(Identity, Audience::Anyone);
        Self {
            audience,
            health: vec![Allergies, Diet],
            safety: vec![Allergies, Diet],
        }
    }
}

impl Policy {
    #[must_use]
    pub fn audience_of(&self, key: FieldKey) -> Audience {
        self.audience
            .get(&key)
            .copied()
            .unwrap_or(Audience::SelfOnly)
    }

    #[must_use]
    pub fn is_safety(&self, key: FieldKey) -> bool {
        self.safety.contains(&key)
    }

    #[must_use]
    pub fn allows(&self, key: FieldKey, subject: &Person, others: &[Option<&Person>]) -> bool {
        if !subject.consent {
            return false;
        }
        if self.health.contains(&key) && !subject.share_health {
            return false;
        }
        match self.audience_of(key) {
            Audience::Anyone => true,
            Audience::Family => others
                .iter()
                .all(|p| p.is_some_and(|p| p.role == Role::Family)),
            Audience::SelfOnly => others.is_empty(),
        }
    }
}
