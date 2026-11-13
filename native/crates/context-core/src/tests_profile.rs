use serde_json::json;

use crate::profile::person_from_profile;
use crate::tests::{pid, shared};
use crate::{ContextError, Delta, Lang, Request, Role};

fn sample() -> serde_json::Value {
    json!({
        "slug": "anna",
        "first_name": "Anna",
        "last_name": "Rossi",
        "nickname": "Nan",
        "role": "family",
        "consent": true,
        "share_health": true,
        "age": 34,
        "occupation": "ingegnera",
        "languages": ["it", "en"],
        "relations": [
            {"type": "madre", "person": "luca"},
            {"type": "amico", "name": "Paolo"},
            {"type": "collega"}
        ],
        "food_likes": ["salato", "salato", "pasta"],
        "food_dislikes": ["funghi"],
        "drinks": ["tè"],
        "coffee": "senza zucchero",
        "custom": [{"key": "colore", "value": "blu"}, {"key": "", "value": "x"}],
        "allergies": ["funghi"],
        "intolerances": ["lattosio"],
        "diet": "Vegetariana",
        "notes": "ama il teatro\u{7}",
        "habits_summary": "arriva spesso alle 18",
        "today": ["Compleanno di Anna"],
        "mood": {"mood": "felice", "intensity": 3, "at": 100.0}
    })
}

#[test]
fn a_profile_maps_every_supported_field() {
    let ctx = shared();
    let person = person_from_profile(&sample(), ctx.settings(), ctx.sealer())
        .unwrap_or_else(|_| unreachable!("profile rejected"));
    assert_eq!(person.name, "Anna Rossi");
    assert_eq!(person.role, Role::Family);
    assert_eq!(person.age, Some(34));
    assert_eq!(person.prefs.food_likes, ["salato", "pasta"]);
    assert_eq!(person.relations.len(), 2);
    assert_eq!(person.notes.as_deref(), Some("ama il teatro"));
    assert_eq!(person.prefs.custom.len(), 1);
    assert_eq!(person.affect.map(|a| a.valence), Some(700));
    let vitals = person
        .vitals
        .as_ref()
        .and_then(|s| ctx.sealer().open(s).ok());
    let vitals = vitals.unwrap_or_else(|| unreachable!("sealed vitals"));
    assert_eq!(vitals.allergies, ["funghi", "lattosio"]);
    assert_eq!(vitals.diet.as_deref(), Some("Vegetariana"));
}

#[test]
fn a_mapped_profile_renders_every_fact_for_the_family() {
    let ctx = shared();
    let anna = person_from_profile(&sample(), ctx.settings(), ctx.sealer())
        .unwrap_or_else(|_| unreachable!());
    let luca = json!({"slug": "luca", "name": "Luca", "role": "owner"});
    let luca =
        person_from_profile(&luca, ctx.settings(), ctx.sealer()).unwrap_or_else(|_| unreachable!());
    assert!(
        ctx.apply_all(vec![
            Delta::Upsert(Box::new(anna)),
            Delta::Upsert(Box::new(luca))
        ])
        .is_ok()
    );
    let request = Request {
        subjects: vec![pid("anna")],
        present: vec![pid("anna")],
        lang: Lang::It,
        budget_chars: 4_000,
        now_ms: 200_000,
    };
    let text = ctx.render(&request);
    for fact in [
        "Anna Rossi",
        "famiglia",
        "Nan",
        "34 anni",
        "ingegnera",
        "madre Luca",
        "amico Paolo",
        "salato",
        "funghi",
        "lattosio",
        "Vegetariana",
        "tè",
        "senza zucchero",
        "colore: blu",
        "ama il teatro",
        "arriva spesso alle 18",
        "Compleanno di Anna",
        "umore: positivo",
    ] {
        assert!(text.contains(fact), "manca: {fact}");
    }
}

#[test]
fn hostile_profiles_are_clamped_or_rejected() {
    let ctx = shared();
    let settings = ctx.settings();
    assert_eq!(
        person_from_profile(&json!({"name": "x"}), settings, ctx.sealer()).err(),
        Some(ContextError::Invalid)
    );
    assert_eq!(
        person_from_profile(&json!({"slug": "Bad Slug"}), settings, ctx.sealer()).err(),
        Some(ContextError::Invalid)
    );
    let flood: Vec<String> = (0..500).map(|n| format!("cibo {n}")).collect();
    let huge = "x".repeat(10_000);
    let profile = json!({"slug": "z", "name": huge, "food_likes": flood, "age": 999, "mood": {"mood": "ignoto", "intensity": 9, "at": -1}});
    let person =
        person_from_profile(&profile, settings, ctx.sealer()).unwrap_or_else(|_| unreachable!());
    assert_eq!(person.prefs.food_likes.len(), settings.max_list_items);
    assert_eq!(person.name.chars().count(), settings.max_text_chars);
    assert_eq!(person.age, None);
    assert!(person.affect.is_none());
    assert_eq!(person.role, Role::Guest);
    assert!(person.consent);
    assert!(!person.share_health);
}

#[test]
fn consent_false_and_missing_health_consent_are_preserved() {
    let ctx = shared();
    let mut profile = sample();
    if let Some(map) = profile.as_object_mut() {
        map.insert("share_health".to_owned(), json!(false));
        map.insert("consent".to_owned(), json!(false));
    }
    let person = person_from_profile(&profile, ctx.settings(), ctx.sealer())
        .unwrap_or_else(|_| unreachable!());
    assert!(!person.consent);
    assert!(!person.share_health);
}
