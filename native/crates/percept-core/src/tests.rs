use nuxiva_context_core::{
    ContextSettings, Delta, Lang, Person, PersonId, Prefs, Role, Sealer, SharedContext, Vitals,
};
use nuxiva_swarm_core::{Channel, Ident, Settings};

use crate::{Fuser, Fusion, Observation, PerceptSettings, PerceptSource, QueueSource};

fn ident(text: &str) -> Ident {
    Ident::new(text).expect("ident")
}

fn pid(text: &str) -> PersonId {
    PersonId::new(text).expect("person")
}

fn shared() -> SharedContext {
    SharedContext::new(ContextSettings::default(), Sealer::from_key([9; 32])).expect("context")
}

fn person(ctx: &SharedContext, id: &str, role: Role, allergy: &str, music: &str) -> Person {
    Person {
        id: pid(id),
        name: id.to_owned(),
        role,
        consent: true,
        share_health: true,
        nickname: None,
        age: None,
        work: None,
        notes: None,
        habits: None,
        languages: vec!["it".to_owned()],
        relations: Vec::new(),
        prefs: Prefs {
            music: vec![music.to_owned()],
            ..Prefs::default()
        },
        listening: Vec::new(),
        today: Vec::new(),
        affect: None,
        vitals: ctx
            .sealer()
            .seal(&Vitals {
                allergies: vec![allergy.to_owned()],
                diet: None,
                notes: None,
            })
            .ok(),
        stale: false,
    }
}

fn household() -> SharedContext {
    let ctx = shared();
    let deltas = vec![
        Delta::Upsert(Box::new(person(
            &ctx,
            "anna",
            Role::Family,
            "arachidi",
            "jazz",
        ))),
        Delta::Upsert(Box::new(person(
            &ctx,
            "luca",
            Role::Family,
            "glutine",
            "rock",
        ))),
        Delta::Upsert(Box::new(person(&ctx, "ospite", Role::Guest, "kiwi", "pop"))),
    ];
    ctx.apply_all(deltas).expect("seed");
    ctx
}

fn fuser() -> Fuser {
    Fuser::new(PerceptSettings::default()).expect("fuser")
}

fn speaker(person: &str, permille: u16, at_ms: u64) -> Observation {
    Observation::Speaker {
        person: ident(person),
        permille,
        at_ms,
    }
}

fn presence(people: &[&str], at_ms: u64) -> Observation {
    Observation::Presence {
        people: people.iter().map(|p| ident(p)).collect(),
        at_ms,
    }
}

fn emotion(person: &str, valence: i16, at_ms: u64) -> Observation {
    Observation::Emotion {
        person: ident(person),
        valence,
        arousal: 700,
        source: ident("voce"),
        at_ms,
    }
}

fn fuse(f: &Fuser, now: u64) -> nuxiva_swarm_core::Percept {
    f.fuse(
        ident("p1"),
        Channel::Voice,
        "cosa cucino stasera".to_owned(),
        now,
        &Settings::default(),
    )
    .expect("percept")
}

#[test]
fn known_speaker_with_allergy_reaches_the_prompt() {
    let fusion = Fusion::new(household());
    let mut f = fuser();
    f.observe(speaker("anna", 950, 1_000), 1_000).expect("obs");
    let percept = fuse(&f, 2_000);
    assert_eq!(percept.addressee_permille, 950);
    let view = fusion.view(&percept, Lang::It, 0).expect("view");
    assert!(view.contains("arachidi"));
    assert!(!view.contains("glutine"));
}

#[test]
fn guest_presence_hides_family_personal_data() {
    let fusion = Fusion::new(household());
    let mut f = fuser();
    f.observe(speaker("anna", 950, 1_000), 1_000).expect("obs");
    f.observe(presence(&["ospite"], 1_000), 1_000).expect("obs");
    let percept = fuse(&f, 2_000);
    let view = fusion.view(&percept, Lang::It, 0).expect("view");
    assert!(view.contains("anna"));
    assert!(!view.contains("jazz"));
    assert!(!view.contains("luca"));
    assert!(!view.contains("rock"));
    assert!(!view.contains("pop"));
}

#[test]
fn unknown_person_present_is_treated_as_outsider() {
    let fusion = Fusion::new(household());
    let mut f = fuser();
    f.observe(speaker("anna", 950, 1_000), 1_000).expect("obs");
    f.observe(presence(&["sconosciuto"], 1_000), 1_000)
        .expect("obs");
    let percept = fuse(&f, 2_000);
    let view = fusion.view(&percept, Lang::It, 0).expect("view");
    assert!(!view.contains("jazz"));
}

#[test]
fn low_confidence_speaker_is_not_personalised() {
    let fusion = Fusion::new(household());
    let mut f = fuser();
    f.observe(speaker("anna", 300, 1_000), 1_000).expect("obs");
    let percept = fuse(&f, 2_000);
    assert!(percept.speaker.is_none());
    assert_eq!(percept.addressee_permille, 0);
    assert!(fusion.view(&percept, Lang::It, 0).expect("view").is_empty());
}

#[test]
fn expired_speaker_and_scene_are_dropped() {
    let mut f = fuser();
    f.observe(speaker("anna", 950, 1_000), 1_000).expect("obs");
    f.observe(
        Observation::Scene {
            reference: ident("scena_1"),
            at_ms: 1_000,
        },
        1_000,
    )
    .expect("obs");
    let percept = fuse(&f, 1_000 + 31_000);
    assert!(percept.speaker.is_none());
    assert!(percept.scene_ref.is_none());
}

#[test]
fn emotion_must_belong_to_the_speaker_and_be_fresh() {
    let mut f = fuser();
    f.observe(speaker("anna", 950, 1_000), 1_000).expect("obs");
    f.observe(emotion("luca", 800, 1_000), 1_000).expect("obs");
    assert!(fuse(&f, 2_000).emotion.is_none());
    f.observe(emotion("anna", 800, 1_500), 1_500).expect("obs");
    assert!(fuse(&f, 2_000).emotion.is_some());
    f.observe(speaker("anna", 950, 700_000), 700_000)
        .expect("obs");
    assert!(fuse(&f, 700_100).emotion.is_none());
}

#[test]
fn stale_emotion_is_not_presented_as_current() {
    let ctx = household();
    let fusion = Fusion::new(ctx.clone());
    let mut f = fuser();
    f.observe(speaker("anna", 950, 1_000), 1_000).expect("obs");
    f.observe(emotion("anna", 900, 1_000), 1_000).expect("obs");
    let fresh_view = fusion.view(&fuse(&f, 2_000), Lang::It, 0).expect("view");
    let settings = ContextSettings::default();
    let later = settings.affect_max_age_ms + 10_000;
    f.observe(speaker("anna", 950, later), later).expect("obs");
    let old = fusion.view(&fuse(&f, later), Lang::It, 0).expect("view");
    assert_ne!(fresh_view, old);
    assert!(!old.to_lowercase().contains("energ"));
}

#[test]
fn future_and_invalid_observations_are_rejected() {
    let mut f = fuser();
    assert!(f.observe(speaker("anna", 900, 1_000_000), 1_000).is_err());
    assert!(f.observe(speaker("anna", 1_500, 1_000), 1_000).is_err());
    let many: Vec<String> = (0..40).map(|i| format!("p{i}")).collect();
    let refs: Vec<&str> = many.iter().map(String::as_str).collect();
    assert!(f.observe(presence(&refs, 1_000), 1_000).is_err());
}

#[test]
fn older_observation_does_not_overwrite_newer() {
    let mut f = fuser();
    f.observe(speaker("luca", 900, 2_000), 2_000).expect("obs");
    f.observe(speaker("anna", 900, 1_000), 2_000).expect("obs");
    let percept = fuse(&f, 2_500);
    assert_eq!(percept.speaker, Some(ident("luca")));
}

#[test]
fn queue_source_validates_json_and_bounds_memory() {
    let source = QueueSource::new(2);
    assert!(source.push_json("{\"kind\":\"nope\"}").is_err());
    assert!(
        source
            .push_json(
                "{\"kind\":\"speaker\",\"person\":\"anna\",\"permille\":900,\"at_ms\":1,\"x\":1}"
            )
            .is_err()
    );
    for at in 1..=5 {
        source
            .push_json(&format!(
                "{{\"kind\":\"scene\",\"reference\":\"s{at}\",\"at_ms\":{at}}}"
            ))
            .expect("push");
    }
    let drained = source.drain();
    assert_eq!(drained.len(), 2);
    assert!(source.drain().is_empty());
}

#[test]
fn settings_reject_nonsense() {
    assert!(PerceptSettings::from_json("{\"speaker_ttl_ms\":0}").is_err());
    assert!(PerceptSettings::from_json("{\"unknown\":1}").is_err());
    assert!(PerceptSettings::from_json("{\"min_speaker_permille\":1200}").is_err());
    assert!(PerceptSettings::from_json("{}").is_ok());
}
