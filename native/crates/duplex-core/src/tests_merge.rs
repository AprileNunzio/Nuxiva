use crate::{
    ChunkSettings, DuplexError, Intent, IntentCatalog, InterruptedReply, Pipeline, Session,
    Settings, Synth, Trigger, words,
};

fn catalog() -> IntentCatalog {
    IntentCatalog::builtin().expect("catalog")
}

fn note() -> crate::Interruption {
    crate::Interruption {
        epoch: 1,
        spoken_chars: 20,
        at_ms: 500,
        fade_ms: 30,
    }
}

#[test]
fn italian_corpus_is_classified_from_the_catalog() {
    let c = catalog();
    let cases = [
        ("no aspetta", Intent::Cancel),
        ("Stop!", Intent::Cancel),
        ("basta così", Intent::Cancel),
        ("lascia stare", Intent::Cancel),
        ("continua", Intent::Continue),
        ("Vai avanti pure", Intent::Continue),
        ("scusa continua", Intent::Continue),
        ("fammi un'altra versione", Intent::Modify),
        ("fammi un’altra versione", Intent::Modify),
        ("più breve per favore", Intent::Modify),
        ("no aspetta fammi un'altra versione", Intent::Modify),
        ("ripeti", Intent::Modify),
        (
            "no aspetta dimmi che tempo fa domani a Milano",
            Intent::Replace,
        ),
        (
            "continua a leggermi le notizie sportive di oggi",
            Intent::Unrelated,
        ),
        ("che ore sono", Intent::Unrelated),
        ("", Intent::Unrelated),
        ("...", Intent::Unrelated),
    ];
    for (text, intent) in cases {
        assert_eq!(c.classify(text), intent, "{text}");
    }
}

#[test]
fn the_plan_follows_the_intent_and_the_reference() {
    let c = catalog();
    let reply = InterruptedReply::new(&note(), "Ecco la ricetta: prendi", Some("fasc:r1".into()))
        .expect("reply");
    let cancel = c.plan(&reply, "no aspetta");
    assert!(cancel.drop_previous && cancel.resume_ref.is_none() && cancel.regenerate_ref.is_none());
    let cont = c.plan(&reply, "continua");
    assert_eq!(cont.resume_ref.as_deref(), Some("fasc:r1"));
    assert!(!cont.drop_previous);
    let modify = c.plan(&reply, "più breve");
    assert_eq!(modify.regenerate_ref.as_deref(), Some("fasc:r1"));
    let replace = c.plan(&reply, "no aspetta dimmi il meteo di domani");
    assert!(replace.drop_previous && replace.resume_ref.is_none());
    let other = c.plan(&reply, "che ore sono");
    assert_eq!(other.intent, Intent::Unrelated);
    assert!(!other.drop_previous);
}

#[test]
fn the_interrupted_reply_is_bounded_and_the_reference_is_checked() {
    let long = "a".repeat(10_000);
    let reply = InterruptedReply::new(&note(), &long, None).expect("reply");
    assert_eq!(reply.spoken_text.chars().count(), 4_096);
    assert_eq!(reply.spoken_chars, 20);
    for bad in ["x y", "../etc", &"a".repeat(129)] {
        assert_eq!(
            InterruptedReply::new(&note(), "t", Some(bad.to_owned())).err(),
            Some(DuplexError::Invalid)
        );
    }
}

#[test]
fn catalogs_are_validated() {
    assert_eq!(
        IntentCatalog::from_json("{}").err(),
        Some(DuplexError::Parse)
    );
    assert_eq!(
        IntentCatalog::from_json(r#"{"cancel":[],"continue":["a"],"modify":["b"]}"#).err(),
        Some(DuplexError::Invalid)
    );
    assert_eq!(
        IntentCatalog::from_json(r#"{"cancel":["..."],"continue":["a"],"modify":["b"]}"#).err(),
        Some(DuplexError::Invalid)
    );
    assert_eq!(words("Dov’è, l'uscita?"), vec!["dov'è", "l'uscita"]);
}

#[derive(Debug, Default)]
struct Quiet;

impl Synth for Quiet {
    fn speak(&mut self, _: u32, _: u32, _: &str) -> crate::DuplexResult<()> {
        Ok(())
    }

    fn cancel(&mut self, _: u32) {}
}

#[test]
fn only_played_text_ends_up_in_the_interrupted_reply() {
    let mut s = Session::new(Settings::default(), 0).expect("session");
    s.trigger(Trigger::VoiceStart, 1).expect("start");
    s.trigger(Trigger::VoiceEnd, 2).expect("end");
    let e = s.begin_reply(3).expect("reply");
    let mut p = Pipeline::new(e, Quiet, ChunkSettings::default()).expect("pipeline");
    p.on_token(
        &mut s,
        "Prima parte della risposta. Seconda parte lunga. Terza parte. ",
        10,
    )
    .expect("tokens");
    p.on_chunk_played(&mut s, 1).expect("played");
    p.on_chunk_played(&mut s, 2).expect("played");
    let report = s.cut(e, 40).expect("cut");
    p.on_cut();
    let note = report.interruption.expect("note");
    let reply =
        InterruptedReply::new(&note, p.spoken_text(), Some("fasc:x".into())).expect("reply");
    assert_eq!(
        reply.spoken_text,
        "Prima parte della risposta. Seconda parte lunga."
    );
    assert_eq!(
        note.spoken_chars as usize,
        reply.spoken_text.chars().count() - 1
    );
}
