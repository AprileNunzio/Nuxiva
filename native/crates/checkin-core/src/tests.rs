use crate::{Daypart, Fact, Kind, Moment, Request, Tone, Turn, daypart, detect, plan};

const NOW: i64 = 1_800_000_000;

fn names() -> Vec<String> {
    vec!["Jarvis".to_owned(), "Nuxiva".to_owned()]
}

fn fact(key: &str, topic: &str, kind: Kind, priority: u8) -> Fact {
    Fact {
        key: key.to_owned(),
        topic: topic.to_owned(),
        kind,
        priority,
        signature: format!("sig-{key}"),
        observed_at: NOW - 30,
        ttl: 600,
        starts_at: None,
        terms: Vec::new(),
    }
}

fn request(hour: u8, facts: Vec<Fact>, history: Vec<Turn>) -> Request {
    Request {
        moment: Moment { now: NOW, hour },
        facts,
        history,
        focus: Vec::new(),
        voice: true,
        seed: 2,
    }
}

fn keys(r: &Request) -> Vec<String> {
    plan(r)
        .expect("plan")
        .facts
        .into_iter()
        .map(|c| c.key)
        .collect()
}

#[test]
fn small_talk_is_recognised_in_many_languages() {
    for text in [
        "Jarvis come va?",
        "ciao jarvis come va? tutto bene?",
        "come stai oggi",
        "tutto ok?",
        "come te la passi Nuxiva",
        "buonasera signore, novità?",
        "how are you doing?",
        "hey Jarvis, what's up?",
        "¿qué tal estás?",
        "hola, ¿cómo va todo?",
        "comment ça va ?",
        "salut, quoi de neuf ?",
    ] {
        let p = detect(text, &names());
        assert!(p.phatic, "{text}: {p:?}");
    }
}

#[test]
fn real_questions_are_not_small_talk() {
    for text in [
        "come va usato questo comando?",
        "come va installato il server su windows",
        "che ore sono",
        "accendi la luce della cucina",
        "come si chiama il presidente",
        "raccontami una storia",
        "how are you supposed to configure the router",
        "what time is it",
        "comment ça marche cette application",
    ] {
        let p = detect(text, &names());
        assert!(!p.phatic, "{text}: {p:?}");
    }
}

#[test]
fn one_extra_word_becomes_the_focus() {
    let p = detect("come vanno i server?", &names());
    assert!(!p.phatic, "{p:?}");
    let p = detect("tutto bene coi satelliti?", &names());
    assert!(p.phatic, "{p:?}");
    assert_eq!(p.focus, vec!["satelliti".to_owned()]);
}

#[test]
fn alerts_lead_and_set_a_formal_tone() {
    let r = request(
        21,
        vec![
            fact("news", "news", Kind::Info, 30),
            fact("node_down", "mesh", Kind::Alert, 85),
            fact("match", "sport", Kind::Interest, 60),
        ],
        Vec::new(),
    );
    let p = plan(&r).expect("plan");
    assert_eq!(p.facts[0].key, "node_down");
    assert_eq!(p.tone, Tone::Formal);
    assert!(!p.humor);
}

#[test]
fn already_told_facts_fade_but_alerts_persist() {
    let told = Turn {
        at: NOW - 300,
        told: vec!["sig-news".to_owned(), "sig-node_down".to_owned()],
        style: "direct".to_owned(),
        humor: false,
    };
    let r = request(
        15,
        vec![
            fact("news", "news", Kind::Info, 30),
            fact("node_down", "mesh", Kind::Alert, 85),
            fact("mail", "email", Kind::Notice, 50),
        ],
        vec![told],
    );
    let chosen = plan(&r).expect("plan").facts;
    assert!(chosen.iter().any(|c| c.key == "node_down" && c.repeat));
    assert!(chosen.iter().any(|c| c.key == "mail" && !c.repeat));
    assert!(!chosen.iter().any(|c| c.key == "news"));
}

#[test]
fn stale_facts_are_never_reported() {
    let mut old = fact("old", "mesh", Kind::Notice, 90);
    old.observed_at = NOW - 4_000;
    let r = request(10, vec![old], Vec::new());
    let p = plan(&r).expect("plan");
    assert!(p.facts.is_empty());
    assert_eq!(p.stale, vec!["old".to_owned()]);
}

#[test]
fn evening_match_beats_old_news() {
    let mut matchday = fact("match", "sport", Kind::Interest, 55);
    matchday.starts_at = Some(NOW + 3_600);
    let r = request(
        19,
        vec![fact("news", "news", Kind::Info, 50), matchday],
        Vec::new(),
    );
    assert_eq!(keys(&r)[0], "match");
}

#[test]
fn night_is_quiet_short_and_without_jokes() {
    let facts = (0..6)
        .map(|i| fact(&format!("n{i}"), &format!("t{i}"), Kind::Notice, 60))
        .collect();
    let p = plan(&request(2, facts, Vec::new())).expect("plan");
    assert_eq!(p.tone, Tone::Quiet);
    assert!(p.facts.len() <= 2);
    assert!(!p.humor);
}

#[test]
fn styles_rotate_and_humor_is_rationed() {
    let history: Vec<Turn> = (0..2)
        .map(|i| Turn {
            at: NOW - 7_200 + i64::from(i) * 60,
            told: Vec::new(),
            style: ["personal", "reassure"][usize::try_from(i).expect("i")].to_owned(),
            humor: true,
        })
        .collect();
    let p = plan(&request(16, Vec::new(), history)).expect("plan");
    assert!(!["personal", "reassure"].contains(&p.style), "{p:?}");
    assert!(!p.humor);
}

#[test]
fn verified_systems_are_reassurance_and_repeat_is_flagged() {
    let ok = fact("systems_ok", "systems", Kind::Ok, 30);
    let p = plan(&request(11, vec![ok.clone()], Vec::new())).expect("plan");
    assert_eq!(p.verified, vec!["systems".to_owned()]);
    assert!(!p.verified_again);
    let told = Turn {
        at: NOW - 120,
        told: vec![ok.signature.clone()],
        style: "direct".to_owned(),
        humor: false,
    };
    let p = plan(&request(11, vec![ok], vec![told])).expect("plan");
    assert!(p.verified_again);
    assert!(p.reuse);
}

#[test]
fn focus_pulls_the_matching_topic_first() {
    let mut sat = fact("sat", "mesh", Kind::Info, 20);
    sat.terms = vec!["satelliti".to_owned(), "nodi".to_owned()];
    let mut r = request(
        16,
        vec![fact("mail", "email", Kind::Notice, 50), sat],
        Vec::new(),
    );
    r.focus = vec!["satelliti".to_owned()];
    assert_eq!(keys(&r)[0], "sat");
}

#[test]
fn dayparts_follow_the_clock() {
    assert_eq!(daypart(3), Daypart::Night);
    assert_eq!(daypart(8), Daypart::Morning);
    assert_eq!(daypart(14), Daypart::Afternoon);
    assert_eq!(daypart(21), Daypart::Evening);
    assert_eq!(daypart(23), Daypart::Late);
}

#[test]
fn oversized_or_hostile_input_is_rejected() {
    let mut r = request(10, Vec::new(), Vec::new());
    r.moment.hour = 24;
    assert!(plan(&r).is_err());
    let mut bad = fact("x", "t", Kind::Info, 10);
    bad.key = "a\u{0}b".to_owned();
    assert!(plan(&request(10, vec![bad], Vec::new())).is_err());
    let many = (0..100)
        .map(|i| fact(&format!("f{i}"), "t", Kind::Info, 10))
        .collect();
    assert!(plan(&request(10, many, Vec::new())).is_err());
}
