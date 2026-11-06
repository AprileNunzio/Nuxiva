use crate::{AddresseeRules, Context};

fn rules() -> AddresseeRules {
    AddresseeRules::new("Ehi Nuxiva", &[]).unwrap_or_else(|_| unreachable!())
}

fn ctx() -> Context {
    Context {
        alone_score: 0.35,
        threshold: 0.5,
        since_reply: 1e9,
        ..Context::default()
    }
}

#[test]
fn name_and_answers_decide_at_once() {
    let r = rules();
    let j = r.judge("nuxiva accendi la luce", &ctx());
    assert!(j.directed && (j.score - 1.0).abs() < 1e-12);
    assert_eq!(j.reason(), "mi ha chiamato per nome");
    assert!(!r.judge("nuxiva è lenta oggi", &ctx()).directed || r.named("nuxiva è lenta oggi"));
    let asked = Context {
        asked_question: true,
        ..ctx()
    };
    assert_eq!(
        r.judge("sì grazie", &asked).reason(),
        "risposta alla mia domanda"
    );
    assert_eq!(r.judge("mah", &ctx()).reason(), "intercalare");
    assert!(r.named("ATTENA spegni"));
}

#[test]
fn alone_commands_are_directed_and_talking_to_others_is_not() {
    let r = rules();
    let alone = Context {
        alone: true,
        ..ctx()
    };
    let j = r.judge("accendi la luce in cucina", &alone);
    assert!(j.directed);
    assert_eq!(j.reason(), "comando");
    let crowd = Context {
        present_names: vec!["Marco".into()],
        ..ctx()
    };
    let j = r.judge("Marco, hai visto le chiavi?", &crowd);
    assert!(!j.directed);
    assert!(j.reason().contains("parla con un'altra persona"));
}

#[test]
fn voice_signals_shift_the_score() {
    let r = rules();
    let base = Context {
        since_reply: 5.0,
        ..ctx()
    };
    let plain = r.judge("e domani invece", &base).score;
    let same = r
        .judge(
            "e domani invece",
            &Context {
                same_speaker: Some(true),
                ..base.clone()
            },
        )
        .score;
    let crowd = r
        .judge(
            "e domani invece",
            &Context {
                voices_active: Some(3),
                mixed_speakers: Some(true),
                ..base
            },
        )
        .score;
    assert!((same - plain - 0.15).abs() < 1e-9);
    assert!((plain - crowd - 0.25).abs() < 1e-9);
}

#[test]
fn overlap_counts_shared_words() {
    let r = rules();
    assert!(
        (r.overlap("che tempo fa domani a Roma", "e domani a Milano che tempo") - 2.0 / 3.0).abs()
            < 1e-9
    );
    assert!(r.overlap("", "ciao").abs() < 1e-12);
    let long = "a".repeat(5000);
    assert!(!r.judge(&long, &ctx()).directed);
}
