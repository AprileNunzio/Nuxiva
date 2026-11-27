use crate::{Daypart, Entry, Fact, Kind, Moment, Observe, Request, Told, observe, plan, weight};

const NOW: i64 = 1_800_000_000;

fn told(topic: &str, terms: &[&str]) -> Told {
    Told {
        topic: topic.to_owned(),
        terms: terms.iter().map(|t| (*t).to_owned()).collect(),
    }
}

fn after(reply: &str, affinity: Vec<Entry>, seconds: i64, hour: u8) -> crate::Observation {
    observe(&Observe {
        at: NOW.saturating_sub(seconds),
        now: NOW,
        hour,
        reply: reply.to_owned(),
        told: vec![
            told("sport", &["partita", "Napoli"]),
            told("news", &["notizie"]),
        ],
        interrupted: false,
        affinity,
    })
    .expect("observe")
}

fn fact(key: &str, topic: &str, priority: u8) -> Fact {
    Fact {
        key: key.to_owned(),
        topic: topic.to_owned(),
        kind: Kind::Info,
        priority,
        signature: format!("sig-{key}"),
        observed_at: NOW,
        ttl: 600,
        starts_at: None,
        terms: Vec::new(),
    }
}

#[test]
fn following_up_raises_a_topic_and_ignoring_lowers_it() {
    let o = after("a che ora gioca il Napoli stasera?", Vec::new(), 30, 21);
    assert!(o.counted);
    assert_eq!(o.engaged, vec!["sport".to_owned()]);
    assert_eq!(o.ignored, vec!["news".to_owned()]);
    assert!(weight(&o.affinity, "sport", Daypart::Evening) > 1.0);
    assert!(weight(&o.affinity, "news", Daypart::Evening) < 1.0);
}

#[test]
fn late_replies_teach_nothing() {
    let o = after("dimmi del Napoli", Vec::new(), 600, 21);
    assert!(!o.counted);
    assert!(o.affinity.is_empty());
}

#[test]
fn an_interruption_counts_against_everything_said() {
    let o = observe(&Observe {
        at: NOW - 5,
        now: NOW,
        hour: 10,
        reply: "basta".to_owned(),
        told: vec![told("news", &["notizie"])],
        interrupted: true,
        affinity: Vec::new(),
    })
    .expect("observe");
    assert!(weight(&o.affinity, "news", Daypart::Morning) < 0.95);
}

#[test]
fn habits_are_learned_per_time_of_day() {
    let mut affinity = Vec::new();
    for _ in 0..8 {
        affinity = after("e il Napoli?", affinity, 20, 20).affinity;
    }
    let evening = weight(&affinity, "sport", Daypart::Evening);
    let morning = weight(&affinity, "sport", Daypart::Morning);
    assert!(evening > morning, "{evening} {morning}");
    assert!(evening <= crate::affinity::MAX_WEIGHT);
}

#[test]
fn learned_interest_reorders_the_report() {
    let mut affinity = Vec::new();
    for _ in 0..6 {
        affinity = after("e il Napoli?", affinity, 20, 15).affinity;
    }
    let request = Request {
        moment: Moment { now: NOW, hour: 15 },
        facts: vec![fact("news", "news", 50), fact("match", "sport", 45)],
        history: Vec::new(),
        focus: Vec::new(),
        voice: true,
        seed: 1,
        affinity,
    };
    assert_eq!(plan(&request).expect("plan").facts[0].key, "match");
}

#[test]
fn hostile_learning_input_is_rejected() {
    let bad = Entry {
        topic: "x".to_owned(),
        when: "any".to_owned(),
        weight: f64::NAN,
        samples: 1,
    };
    assert!(
        observe(&Observe {
            at: NOW,
            now: NOW,
            hour: 10,
            reply: String::new(),
            told: Vec::new(),
            interrupted: false,
            affinity: vec![bad],
        })
        .is_err()
    );
}
