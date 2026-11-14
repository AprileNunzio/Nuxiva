use crate::{
    ChunkSettings, Chunker, DuplexError, DuplexResult, Pipeline, Session, Settings, State, Synth,
    Trigger,
};

fn chunker() -> Chunker {
    Chunker::new(ChunkSettings::default()).expect("chunker")
}

fn feed(tokens: &[&str]) -> Vec<String> {
    let mut c = chunker();
    let mut out = Vec::new();
    for (i, t) in tokens.iter().enumerate() {
        out.extend(c.push(t, i as u64));
    }
    out.extend(c.flush(1_000));
    out
}

#[test]
fn sentences_close_on_punctuation_with_lookahead() {
    let out = feed(&["Ciao, sono ", "Nuxiva. ", "Come ", "stai", "? ", "Bene"]);
    assert_eq!(out, vec!["Ciao, sono Nuxiva.", "Come stai?", "Bene"]);
}

#[test]
fn a_terminator_waits_for_the_next_character() {
    let mut c = chunker();
    assert!(c.push("Ho finito.", 0).is_empty());
    assert_eq!(c.push(" Poi", 1), vec!["Ho finito."]);
}

#[test]
fn numbers_dates_and_acronyms_are_never_split() {
    let out = feed(&["Costa 3.5 euro e arriva alle 10.30 con la U.S.A. Express. Fine"]);
    assert_eq!(
        out,
        vec![
            "Costa 3.5 euro e arriva alle 10.30 con la U.S.A. Express.",
            "Fine"
        ]
    );
    let out = feed(&["Il 12. maggio ci vediamo. Ciao"]);
    assert_eq!(out, vec!["Il 12. maggio ci vediamo.", "Ciao"]);
}

#[test]
fn abbreviations_and_initials_do_not_end_a_sentence() {
    let out = feed(&["Parla il dott. Rossi con A. Bianchi ecc. e poi esce. Fine"]);
    assert_eq!(
        out,
        vec![
            "Parla il dott. Rossi con A. Bianchi ecc. e poi esce.",
            "Fine"
        ]
    );
}

#[test]
fn clauses_close_only_after_enough_text() {
    let out = feed(&[
        "Si, ",
        "certo che posso aiutarti con questo, ",
        "dimmi pure",
    ]);
    assert_eq!(
        out,
        vec!["Si, certo che posso aiutarti con questo,", "dimmi pure"]
    );
}

#[test]
fn decimal_commas_are_kept() {
    let out = feed(&["Misura 3,5 metri di lunghezza totale. Fine"]);
    assert_eq!(out, vec!["Misura 3,5 metri di lunghezza totale.", "Fine"]);
}

#[test]
fn waiting_too_long_flushes_at_a_word_boundary() {
    let mut c = chunker();
    assert!(
        c.push("questa frase non finisce mai e continua ancora un po", 0)
            .is_empty()
    );
    assert!(c.poll(349).is_empty());
    let out = c.poll(350);
    assert_eq!(
        out,
        vec!["questa frase non finisce mai e continua ancora un"]
    );
    assert_eq!(c.flush(400), vec!["po"]);
}

#[test]
fn soft_splits_never_cut_between_digit_groups() {
    let mut c = chunker();
    c.push("il numero e 1 000 000 euro tondi tondi", 0);
    let out = c.poll(1_000);
    assert_eq!(out.len(), 1);
    assert!(!out[0].ends_with(" 1") && !out[0].ends_with("000"));
}

#[test]
fn very_long_text_is_capped() {
    let mut c = chunker();
    let long = "parola ".repeat(200);
    let out = c.push(&long, 0);
    assert!(out.len() >= 5);
    assert!(out.iter().all(|s| s.chars().count() <= 240));
    let joined: Vec<String> = out.into_iter().chain(c.flush(1)).collect();
    assert_eq!(joined.join(" "), long.trim());
    let mut c = chunker();
    let blob = "x".repeat(1_000);
    let out = c.push(&blob, 0);
    assert!(out.iter().all(|s| s.chars().count() <= 240));
}

#[test]
fn multibyte_text_is_safe() {
    let out = feed(&["Perché è già così… davvero? Sì, però ", "più tardi"]);
    assert_eq!(
        out,
        vec!["Perché è già così…", "davvero?", "Sì, però più tardi"]
    );
}

#[test]
fn nothing_is_lost_or_duplicated_across_random_splits() {
    let text = "Buongiorno a tutti. Oggi il meteo prevede sole, con 21,5 gradi alle 10.30; domani invece pioggia. Il dott. Verdi ha detto: tutto bene! Davvero? Sì.";
    let mut x: u64 = 0x1234_5678_9ABC_DEF1;
    for _ in 0..300 {
        let mut c = chunker();
        let mut out = Vec::new();
        let mut rest = text;
        let mut t = 0u64;
        while !rest.is_empty() {
            x ^= x << 13;
            x ^= x >> 7;
            x ^= x << 17;
            let mut n = (x % 9 + 1) as usize;
            while !rest.is_char_boundary(n.min(rest.len())) {
                n += 1;
            }
            let (head, tail) = rest.split_at(n.min(rest.len()));
            out.extend(c.push(head, t));
            t += 5;
            rest = tail;
        }
        out.extend(c.flush(t));
        let squashed: String = out
            .join(" ")
            .split_whitespace()
            .collect::<Vec<_>>()
            .join(" ");
        assert_eq!(squashed, text);
    }
}

#[test]
fn settings_are_validated() {
    let mut s = ChunkSettings::default();
    s.min_chars = 0;
    assert_eq!(s.validate(), Err(DuplexError::Settings));
    assert!(ChunkSettings::from_json("{\"x\":1}").is_err());
    assert_eq!(
        ChunkSettings::from_json(&"x".repeat(5_000)),
        Err(DuplexError::TooLarge)
    );
}

#[derive(Debug, Default)]
struct Fake {
    spoken: Vec<(u32, u32, String)>,
    cancelled: Vec<u32>,
    fail: bool,
}

impl Synth for Fake {
    fn speak(&mut self, epoch: u32, seq: u32, text: &str) -> DuplexResult<()> {
        if self.fail {
            return Err(DuplexError::Invalid);
        }
        self.spoken.push((epoch, seq, text.to_owned()));
        Ok(())
    }

    fn cancel(&mut self, epoch: u32) {
        self.cancelled.push(epoch);
    }
}

fn speaking_session() -> (Session, u32) {
    let mut s = Session::new(Settings::default(), 0).expect("session");
    s.trigger(Trigger::VoiceStart, 1).expect("start");
    s.trigger(Trigger::VoiceEnd, 2).expect("end");
    let e = s.begin_reply(3).expect("reply");
    (s, e)
}

#[test]
fn the_first_chunk_reaches_the_synth_without_waiting_for_the_whole_reply() {
    let (mut s, e) = speaking_session();
    let mut p = Pipeline::new(e, Fake::default(), ChunkSettings::default()).expect("pipeline");
    p.on_token(&mut s, "Ciao a ", 100).expect("t");
    p.on_token(&mut s, "tutti. ", 120).expect("t");
    assert_eq!(p.synth().spoken, vec![(e, 1, "Ciao a tutti.".to_owned())]);
    p.on_audio_started(380);
    assert_eq!(p.metrics().ttfb_ms, Some(280));
    p.on_audio_started(900);
    assert_eq!(p.metrics().ttfb_ms, Some(280));
    p.on_token(&mut s, "Come stai? ", 400).expect("t");
    p.finish(&mut s, 450).expect("finish");
    assert_eq!(p.synth().spoken.len(), 2);
    assert_eq!(p.metrics().chunks, 2);
    assert_eq!(p.metrics().max_gap_ms, 280);
}

#[test]
fn a_cut_stops_synthesis_and_drops_what_is_waiting() {
    let (mut s, e) = speaking_session();
    let mut p = Pipeline::new(e, Fake::default(), ChunkSettings::default()).expect("pipeline");
    p.on_token(&mut s, "Prima frase. Seconda frase ancora. Terza", 10)
        .expect("t");
    assert_eq!(p.synth().spoken.len(), 2);
    s.cut(e, 20).expect("cut");
    p.on_cut();
    assert_eq!(p.synth().cancelled, vec![e]);
    assert_eq!(p.on_token(&mut s, " e ancora", 30), Err(DuplexError::Stale));
    assert_eq!(p.finish(&mut s, 31), Err(DuplexError::Stale));
    assert_eq!(p.synth().spoken.len(), 2);
    assert_eq!(s.snapshot().state, State::Interrupted);
}

#[test]
fn only_played_chunks_count_as_spoken() {
    let (mut s, e) = speaking_session();
    let mut p = Pipeline::new(e, Fake::default(), ChunkSettings::default()).expect("pipeline");
    p.on_token(&mut s, "Uno due tre. Quattro cinque sei. ", 10)
        .expect("t");
    p.on_chunk_played(&mut s, 1).expect("played");
    assert_eq!(s.snapshot().spoken_chars, 12);
    assert_eq!(p.unspoken(), vec!["Quattro cinque sei."]);
    assert_eq!(p.on_chunk_played(&mut s, 9), Err(DuplexError::Invalid));
    let report = s.cut(e, 20).expect("cut");
    assert_eq!(report.interruption.expect("note").spoken_chars, 12);
}

#[test]
fn a_full_playback_queue_applies_backpressure_and_a_failing_synth_is_reported() {
    let (mut s, e) = speaking_session();
    let settings = ChunkSettings {
        queue_cap: 1,
        ..ChunkSettings::default()
    };
    let mut p = Pipeline::new(
        e,
        Fake {
            fail: true,
            ..Fake::default()
        },
        settings,
    )
    .expect("pipeline");
    assert_eq!(
        p.on_token(&mut s, "Prima frase. Seconda frase lunga. ", 1),
        Err(DuplexError::Capacity)
    );
    let mut p = Pipeline::new(
        e,
        Fake {
            fail: true,
            ..Fake::default()
        },
        ChunkSettings::default(),
    )
    .expect("pipeline");
    assert_eq!(
        p.on_token(&mut s, "Una frase intera. ", 1),
        Err(DuplexError::Invalid)
    );
}

#[test]
fn underruns_are_counted() {
    let (mut s, e) = speaking_session();
    let mut p = Pipeline::new(e, Fake::default(), ChunkSettings::default()).expect("pipeline");
    p.on_underrun();
    p.on_underrun();
    p.on_tick(&mut s, 5).expect("tick");
    assert_eq!(p.metrics().underruns, 2);
}
