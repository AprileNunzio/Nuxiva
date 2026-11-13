use crate::{
    Affect, ContextError, ContextSettings, Delta, Lang, Listen, Person, PersonId, Prefs, Relation,
    Request, Role, Sealer, SharedContext, Vitals,
};

pub(crate) fn pid(text: &str) -> PersonId {
    PersonId::new(text).unwrap_or_else(|_| unreachable!("fixture id"))
}

pub(crate) fn shared() -> SharedContext {
    SharedContext::new(ContextSettings::default(), Sealer::from_key([7; 32]))
        .unwrap_or_else(|_| unreachable!("settings"))
}

pub(crate) fn person(ctx: &SharedContext, id: &str, name: &str, role: Role) -> Person {
    Person {
        id: pid(id),
        name: name.to_owned(),
        role,
        consent: true,
        share_health: true,
        nickname: None,
        age: Some(34),
        work: Some("ingegnere".to_owned()),
        languages: vec!["it".to_owned()],
        relations: Vec::new(),
        prefs: Prefs {
            food_likes: vec!["salato".to_owned()],
            music: vec!["jazz".to_owned()],
            ..Prefs::default()
        },
        listening: vec![Listen {
            title: "Blue".to_owned(),
            artist: "Joni".to_owned(),
            at_ms: 1,
        }],
        today: Vec::new(),
        affect: None,
        vitals: ctx
            .sealer()
            .seal(&Vitals {
                allergies: vec!["funghi".to_owned()],
                diet: None,
                notes: None,
            })
            .ok(),
        stale: false,
    }
}

fn request(subjects: &[&str], present: &[&str]) -> Request {
    Request {
        subjects: subjects.iter().map(|s| pid(s)).collect(),
        present: present.iter().map(|s| pid(s)).collect(),
        lang: Lang::It,
        budget_chars: 0,
        now_ms: 1_000,
    }
}

fn family(ctx: &SharedContext) {
    let mut anna = person(ctx, "anna", "Anna", Role::Family);
    anna.relations = vec![Relation {
        kind: "madre di".to_owned(),
        with: pid("luca"),
    }];
    let luca = person(ctx, "luca", "Luca", Role::Family);
    let ospite = person(ctx, "ospite_1", "Ospite 1", Role::Guest);
    let result = ctx.apply_all(vec![
        Delta::Upsert(Box::new(anna)),
        Delta::Upsert(Box::new(luca)),
        Delta::Upsert(Box::new(ospite)),
    ]);
    assert!(result.is_ok());
}

#[test]
fn family_sees_preferences_and_the_allergy() {
    let ctx = shared();
    family(&ctx);
    let text = ctx.render(&request(&["anna"], &["anna", "luca"]));
    assert!(text.contains("Anna (famiglia)"));
    assert!(text.contains("funghi"));
    assert!(text.contains("jazz"));
    assert!(text.contains("madre di Luca"));
}

#[test]
fn a_guest_in_the_room_hides_family_details_but_not_the_name() {
    let ctx = shared();
    family(&ctx);
    let text = ctx.render(&request(&["anna"], &["anna", "ospite_1"]));
    assert!(text.contains("Anna (famiglia)"));
    assert!(!text.contains("funghi"));
    assert!(!text.contains("jazz"));
    assert!(!text.contains("Luca"));
    assert!(!text.contains("ingegnere"));
}

#[test]
fn an_unknown_present_person_is_treated_as_a_guest() {
    let ctx = shared();
    family(&ctx);
    let text = ctx.render(&request(&["anna"], &["anna", "sconosciuto"]));
    assert!(!text.contains("funghi"));
}

#[test]
fn consent_and_share_health_are_enforced() {
    let ctx = shared();
    let mut quiet = person(&ctx, "anna", "Anna", Role::Family);
    quiet.share_health = false;
    let mut private = person(&ctx, "luca", "Luca", Role::Family);
    private.consent = false;
    assert!(ctx.apply(Delta::Upsert(Box::new(quiet))).is_ok());
    assert!(ctx.apply(Delta::Upsert(Box::new(private))).is_ok());
    let text = ctx.render(&request(&["anna", "luca"], &["anna"]));
    assert!(text.contains("Anna"));
    assert!(!text.contains("funghi"));
    assert!(!text.contains("Luca"));
}

#[test]
fn safety_fields_survive_a_tight_budget() {
    let ctx = shared();
    family(&ctx);
    let mut tight = request(&["anna"], &["anna"]);
    tight.budget_chars = 60;
    let text = ctx.render(&tight);
    assert!(text.contains("Anna (famiglia)"));
    assert!(text.contains("funghi"));
    assert!(!text.contains("jazz"));
}

#[test]
fn sealed_fields_never_appear_in_serialized_or_debug_output() {
    let ctx = shared();
    let anna = person(&ctx, "anna", "Anna", Role::Family);
    let json = serde_json::to_string(&anna).unwrap_or_default();
    assert!(!json.contains("funghi"));
    assert!(!format!("{anna:?}").contains("Anna"));
    let sealed = anna
        .vitals
        .clone()
        .unwrap_or_else(|| unreachable!("sealed"));
    let other = Sealer::from_key([9; 32]);
    assert_eq!(other.open(&sealed).err(), Some(ContextError::Seal));
    let mut tampered = sealed;
    if let Some(byte) = tampered.data.first_mut() {
        *byte ^= 1;
    }
    assert_eq!(ctx.sealer().open(&tampered).err(), Some(ContextError::Seal));
}

#[test]
fn emotion_decays_and_expires() {
    let ctx = shared();
    let mut anna = person(&ctx, "anna", "Anna", Role::Family);
    anna.affect = Some(Affect {
        valence: 800,
        arousal: 100,
        at_ms: 0,
    });
    assert!(ctx.apply(Delta::Upsert(Box::new(anna))).is_ok());
    let mut now = request(&["anna"], &["anna"]);
    now.now_ms = 1_000;
    assert!(ctx.render(&now).contains("umore: positivo"));
    now.now_ms = 3_700_000;
    assert!(ctx.render(&now).contains("umore: neutro"));
    now.now_ms = 8_000_000;
    assert!(!ctx.render(&now).contains("umore"));
}

#[test]
fn render_is_cached_per_version_and_invalidated_by_updates() {
    let ctx = shared();
    family(&ctx);
    let req = request(&["anna"], &["anna"]);
    let first = ctx.render(&req);
    let second = ctx.render(&req);
    assert!(std::sync::Arc::ptr_eq(&first, &second));
    let mut changed = person(&ctx, "anna", "Anna", Role::Family);
    changed.work = Some("medico".to_owned());
    assert!(ctx.apply(Delta::Upsert(Box::new(changed))).is_ok());
    let third = ctx.render(&req);
    assert!(third.contains("medico"));
    assert!(!std::sync::Arc::ptr_eq(&first, &third));
}

#[test]
fn removing_a_person_clears_snapshot_presence_and_render() {
    let ctx = shared();
    family(&ctx);
    assert!(
        ctx.apply(Delta::SetPresence {
            present: vec![pid("anna"), pid("luca")],
            at_ms: 5
        })
        .is_ok()
    );
    let req = request(&["luca"], &["luca"]);
    assert!(ctx.render(&req).contains("Luca"));
    assert!(ctx.apply(Delta::Remove(pid("luca"))).is_ok());
    let snapshot = ctx.snapshot();
    assert!(snapshot.person(&pid("luca")).is_none());
    assert_eq!(snapshot.present(), [pid("anna")]);
    assert!(ctx.render(&req).is_empty());
    assert_eq!(
        ctx.apply(Delta::Remove(pid("luca"))).err(),
        Some(ContextError::Unknown)
    );
}

#[test]
fn invalid_updates_are_rejected_and_leave_state_untouched() {
    let ctx = shared();
    family(&ctx);
    let before = ctx.snapshot().version();
    let mut bad = person(&ctx, "anna", "Anna\u{7}", Role::Family);
    assert_eq!(
        ctx.apply(Delta::Upsert(Box::new(bad.clone()))).err(),
        Some(ContextError::Invalid)
    );
    bad.name = "x".repeat(401);
    assert_eq!(
        ctx.apply(Delta::Upsert(Box::new(bad.clone()))).err(),
        Some(ContextError::TooLarge)
    );
    bad.name = "Anna".to_owned();
    bad.age = Some(200);
    assert_eq!(
        ctx.apply(Delta::Upsert(Box::new(bad))).err(),
        Some(ContextError::Invalid)
    );
    assert_eq!(ctx.snapshot().version(), before);
    assert_eq!(
        PersonId::new("Anna Rossi").err(),
        Some(ContextError::Invalid)
    );
}

#[test]
fn capacity_and_settings_are_enforced() {
    let settings = ContextSettings {
        max_persons: 2,
        ..ContextSettings::default()
    };
    let ctx =
        SharedContext::new(settings, Sealer::from_key([1; 32])).unwrap_or_else(|_| unreachable!());
    for name in ["a1", "a2"] {
        assert!(
            ctx.apply(Delta::Upsert(Box::new(person(
                &ctx,
                name,
                "N",
                Role::Family
            ))))
            .is_ok()
        );
    }
    assert_eq!(
        ctx.apply(Delta::Upsert(Box::new(person(
            &ctx,
            "a3",
            "N",
            Role::Family
        ))))
        .err(),
        Some(ContextError::Capacity)
    );
    assert_eq!(
        ContextSettings::from_json(r#"{"max_persons":0}"#).err(),
        Some(ContextError::Settings)
    );
    assert_eq!(
        ContextSettings::from_json(r#"{"inventato":1}"#).err(),
        Some(ContextError::Settings)
    );
    assert_eq!(
        ContextSettings::from_json(r#"{"default_budget_chars":99999999}"#).err(),
        Some(ContextError::Settings)
    );
    assert!(ContextSettings::from_json(r#"{"max_persons":10}"#).is_ok());
}

#[test]
fn a_person_stays_within_the_memory_budget() {
    let ctx = shared();
    let mut anna = person(&ctx, "anna", "Anna", Role::Family);
    anna.prefs.hobbies = (0..16).map(|n| format!("hobby numero {n}")).collect();
    anna.prefs.music = (0..16).map(|n| format!("artista {n}")).collect();
    assert!(anna.approx_bytes() <= 8 * 1024);
}

#[test]
fn policy_defaults_to_the_most_restrictive_audience_for_unknown_keys() {
    use crate::{Audience, FieldKey, Policy};
    let mut policy = Policy::default();
    policy.audience.remove(&FieldKey::Music);
    assert_eq!(policy.audience_of(FieldKey::Music), Audience::SelfOnly);
    assert_eq!(policy.audience_of(FieldKey::Identity), Audience::Anyone);
}

#[test]
fn every_language_renders_without_leaking_other_languages() {
    let ctx = shared();
    family(&ctx);
    for (lang, marker) in [
        (Lang::En, "family"),
        (Lang::Fr, "famille"),
        (Lang::Es, "familia"),
    ] {
        let mut req = request(&["anna"], &["anna"]);
        req.lang = lang;
        let text = ctx.render(&req);
        assert!(text.contains(marker), "{marker}");
        assert!(!text.contains("famiglia"));
    }
}
