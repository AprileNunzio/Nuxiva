use serde_json::Value;

use crate::error::{ContextError, ContextResult};
use crate::id::PersonId;
use crate::model::{Affect, Custom, Person, Prefs, Relation, Role};
use crate::seal::{Sealer, Vitals};
use crate::settings::ContextSettings;

const MOODS: [(&str, i32, i32); 13] = [
    ("felice", 700, 500),
    ("sereno", 500, 150),
    ("entusiasta", 850, 850),
    ("innamorato", 850, 600),
    ("grato", 700, 300),
    ("neutro", 0, 300),
    ("stanco", -250, 100),
    ("annoiato", -300, 200),
    ("stressato", -500, 800),
    ("preoccupato", -450, 600),
    ("triste", -700, 200),
    ("arrabbiato", -700, 850),
    ("malato", -600, 150),
];

fn text(value: Option<&Value>, settings: &ContextSettings) -> Option<String> {
    let raw = value?.as_str()?;
    let clean: String = raw
        .chars()
        .filter(|c| !c.is_control())
        .take(settings.max_text_chars)
        .collect();
    let trimmed = clean.trim();
    (!trimmed.is_empty()).then(|| trimmed.to_owned())
}

fn list(value: Option<&Value>, settings: &ContextSettings) -> Vec<String> {
    let Some(items) = value.and_then(Value::as_array) else {
        return Vec::new();
    };
    let mut out: Vec<String> = Vec::new();
    for item in items {
        let candidate = match item {
            Value::String(_) => text(Some(item), settings),
            Value::Object(map) => text(map.get("name").or_else(|| map.get("title")), settings),
            _ => None,
        };
        if let Some(entry) = candidate {
            if !out.contains(&entry) && out.len() < settings.max_list_items {
                out.push(entry);
            }
        }
    }
    out
}

fn relations(value: Option<&Value>, settings: &ContextSettings) -> Vec<Relation> {
    let Some(items) = value.and_then(Value::as_array) else {
        return Vec::new();
    };
    items
        .iter()
        .filter_map(|item| {
            let map = item.as_object()?;
            let kind = text(map.get("type"), settings)?.replace('_', " ");
            let with = text(map.get("person"), settings).and_then(|s| PersonId::new(&s).ok());
            let name = text(map.get("name"), settings);
            (with.is_some() || name.is_some()).then_some(Relation { kind, with, name })
        })
        .take(settings.max_relations)
        .collect()
}

fn custom(value: Option<&Value>, settings: &ContextSettings) -> Vec<Custom> {
    let Some(items) = value.and_then(Value::as_array) else {
        return Vec::new();
    };
    items
        .iter()
        .filter_map(|item| {
            let map = item.as_object()?;
            Some(Custom {
                key: text(map.get("key"), settings)?,
                value: text(map.get("value"), settings)?,
            })
        })
        .take(settings.max_list_items)
        .collect()
}

fn affect(value: Option<&Value>) -> Option<Affect> {
    let map = value?.as_object()?;
    let name = map.get("mood")?.as_str()?.trim().to_lowercase();
    let intensity = map
        .get("intensity")
        .and_then(Value::as_i64)
        .filter(|n| (1..=5).contains(n))
        .and_then(|n| i32::try_from(n).ok())?;
    let (_, valence, arousal) = MOODS.iter().find(|(label, _, _)| *label == name)?;
    let scaled = valence
        .saturating_mul(intensity)
        .checked_div(3)?
        .clamp(-1000, 1000);
    let energy = arousal
        .saturating_mul(intensity)
        .checked_div(3)?
        .clamp(0, 1000);
    let at_seconds = map
        .get("at")
        .and_then(Value::as_f64)
        .filter(|s| s.is_finite() && *s >= 0.0)?;
    Some(Affect {
        valence: i16::try_from(scaled).ok()?,
        arousal: u16::try_from(energy).ok()?,
        at_ms: format!("{:.0}", at_seconds * 1000.0).parse().ok()?,
    })
}

fn vitals(
    profile: &Value,
    settings: &ContextSettings,
    sealer: &Sealer,
) -> Option<crate::seal::Sealed> {
    let mut allergies = list(profile.get("allergies"), settings);
    for extra in list(profile.get("intolerances"), settings) {
        if !allergies.contains(&extra) && allergies.len() < settings.max_list_items {
            allergies.push(extra);
        }
    }
    let diet = text(profile.get("diet"), settings);
    if allergies.is_empty() && diet.is_none() {
        return None;
    }
    sealer
        .seal(&Vitals {
            allergies,
            diet,
            notes: None,
        })
        .ok()
}

fn name_of(profile: &Value, slug: &str, settings: &ContextSettings) -> String {
    let first = text(profile.get("first_name"), settings).unwrap_or_default();
    let last = text(profile.get("last_name"), settings).unwrap_or_default();
    let full = format!("{first} {last}").trim().to_owned();
    if full.is_empty() {
        text(profile.get("name"), settings).unwrap_or_else(|| slug.to_owned())
    } else {
        full
    }
}

pub fn person_from_profile(
    profile: &Value,
    settings: &ContextSettings,
    sealer: &Sealer,
) -> ContextResult<Person> {
    let slug = profile
        .get("slug")
        .and_then(Value::as_str)
        .ok_or(ContextError::Invalid)?;
    let id = PersonId::new(slug)?;
    let role = match profile.get("role").and_then(Value::as_str) {
        Some("owner" | "family") => Role::Family,
        _ => Role::Guest,
    };
    let flag =
        |key: &str, default: bool| profile.get(key).and_then(Value::as_bool).unwrap_or(default);
    let person = Person {
        name: name_of(profile, slug, settings),
        id,
        role,
        consent: flag("consent", true),
        share_health: flag("share_health", false),
        nickname: text(profile.get("nickname"), settings),
        age: profile
            .get("age")
            .and_then(Value::as_u64)
            .and_then(|a| u16::try_from(a).ok())
            .filter(|a| *a <= 150),
        work: text(profile.get("occupation"), settings),
        notes: text(profile.get("notes"), settings),
        habits: text(profile.get("habits_summary"), settings),
        languages: list(profile.get("languages"), settings),
        relations: relations(profile.get("relations"), settings),
        prefs: Prefs {
            food_likes: list(profile.get("food_likes"), settings),
            food_dislikes: list(profile.get("food_dislikes"), settings),
            drinks: list(profile.get("drinks"), settings),
            music: list(profile.get("music"), settings),
            movies: list(profile.get("movies"), settings),
            sports: list(profile.get("sports"), settings),
            hobbies: list(profile.get("hobbies"), settings),
            coffee: text(profile.get("coffee"), settings),
            custom: custom(profile.get("custom"), settings),
        },
        listening: Vec::new(),
        today: list(profile.get("today"), settings),
        affect: affect(profile.get("mood")),
        vitals: vitals(profile, settings, sealer),
        stale: false,
    };
    person.validate(settings)?;
    Ok(person)
}
