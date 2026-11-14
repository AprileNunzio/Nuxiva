use crate::{
    Backchannel, BargeDetector, BargeSettings, Decision, DuplexError, Evidence, PreRoll, Risk,
    Session, Settings, State, Trigger, Verdict, may_command,
};

fn speaking() -> Session {
    let mut s = Session::new(Settings::default(), 0).expect("session");
    s.trigger(Trigger::VoiceStart, 1).expect("start");
    s.trigger(Trigger::VoiceEnd, 2).expect("end");
    s.begin_reply(3).expect("reply");
    s
}

fn ev(verdict: Verdict, margin: u16, voiced: bool) -> Evidence {
    Evidence {
        verdict,
        margin_permille: margin,
        voiced,
        frame_ms: 50,
    }
}

fn detector() -> BargeDetector {
    BargeDetector::new(BargeSettings::default()).expect("detector")
}

#[test]
fn the_owner_voice_cuts_after_the_short_window() {
    let mut s = speaking();
    let mut d = detector();
    let mut now = 100;
    let mut cut = None;
    let mut ducked = false;
    for _ in 0..10 {
        match d.step(&mut s, &ev(Verdict::Known, 900, true), now) {
            Decision::Duck => ducked = true,
            Decision::Cut(r) => {
                cut = Some(r);
                break;
            }
            _ => {}
        }
        now += 50;
    }
    let report = cut.expect("cut");
    assert!(ducked);
    assert_eq!(report.state, State::Interrupted);
    assert_eq!(now, 100 + 4 * 50);
    assert_eq!(d.stats().cuts, 1);
}

#[test]
fn radio_tv_and_unknown_voices_never_cut() {
    let mut s = speaking();
    let mut d = detector();
    for i in 0..100_000u64 {
        let verdict = if i % 2 == 0 {
            Verdict::Broadcast
        } else {
            Verdict::Uncertain
        };
        assert_eq!(
            d.step(&mut s, &ev(verdict, 1_000, true), i * 50),
            Decision::Hold
        );
    }
    assert_eq!(s.state(), State::Speaking);
    assert_eq!(d.stats().cuts, 0);
    assert!(d.stats().ignored_broadcast > 0 && d.stats().ignored_uncertain > 0);
}

#[test]
fn a_broadcast_frame_resets_the_accumulated_voice() {
    let mut s = speaking();
    let mut d = detector();
    for i in 0..3 {
        d.step(&mut s, &ev(Verdict::Known, 900, true), 100 + i * 50);
    }
    d.step(&mut s, &ev(Verdict::Broadcast, 900, true), 250);
    for i in 0..3 {
        let step = d.step(&mut s, &ev(Verdict::Known, 900, true), 300 + i * 50);
        assert!(!matches!(step, Decision::Cut(_)));
    }
    assert_eq!(s.state(), State::Speaking);
}

#[test]
fn weak_margin_and_silence_reset_the_window() {
    let mut s = speaking();
    let mut d = detector();
    for i in 0..3 {
        d.step(&mut s, &ev(Verdict::Known, 900, true), 100 + i * 50);
    }
    d.step(&mut s, &ev(Verdict::Known, 900, false), 250);
    for i in 0..3 {
        let step = d.step(&mut s, &ev(Verdict::Known, 900, true), 300 + i * 50);
        assert!(!matches!(step, Decision::Cut(_)));
    }
    let mut s = speaking();
    let mut d = detector();
    for i in 0..50 {
        assert_eq!(
            d.step(&mut s, &ev(Verdict::Known, 599, true), 100 + i * 50),
            Decision::Hold
        );
    }
    assert!(d.stats().ignored_weak >= 50);
}

#[test]
fn guests_cut_only_when_allowed() {
    let mut s = speaking();
    let settings = BargeSettings {
        guest_may_interrupt: false,
        ..BargeSettings::default()
    };
    let mut d = BargeDetector::new(settings).expect("detector");
    for i in 0..20 {
        assert_eq!(
            d.step(&mut s, &ev(Verdict::Guest, 900, true), 100 + i * 50),
            Decision::Hold
        );
    }
    assert_eq!(d.stats().ignored_guest, 20);
    let mut s = speaking();
    let mut d = detector();
    let cut = (0..10).any(|i| {
        matches!(
            d.step(&mut s, &ev(Verdict::Guest, 900, true), 100 + i * 50),
            Decision::Cut(_)
        )
    });
    assert!(cut);
}

#[test]
fn nothing_happens_unless_nuxiva_is_speaking() {
    let mut s = Session::new(Settings::default(), 0).expect("session");
    let mut d = detector();
    for i in 0..20 {
        assert_eq!(
            d.step(&mut s, &ev(Verdict::Known, 1_000, true), i * 50),
            Decision::Hold
        );
    }
    assert_eq!(d.stats().cuts, 0);
}

#[test]
fn ducking_is_restored_when_no_cut_follows() {
    let mut s = speaking();
    let mut d = detector();
    assert_eq!(
        d.step(&mut s, &ev(Verdict::Known, 900, true), 100),
        Decision::Hold
    );
    assert_eq!(
        d.step(&mut s, &ev(Verdict::Known, 900, true), 150),
        Decision::Duck
    );
    assert_eq!(
        d.step(&mut s, &ev(Verdict::Known, 900, false), 200),
        Decision::Hold
    );
    assert_eq!(d.tick(3_149), Decision::Hold);
    assert_eq!(d.tick(3_150), Decision::Restore);
    assert_eq!(d.tick(9_000), Decision::Hold);
}

#[test]
fn the_cooldown_prevents_a_second_cut_straight_away() {
    let mut s = speaking();
    let mut d = detector();
    let mut now = 100;
    while !matches!(
        d.step(&mut s, &ev(Verdict::Known, 900, true), now),
        Decision::Cut(_)
    ) {
        now += 50;
    }
    let cut_at = now;
    s.trigger(Trigger::Resume, now + 1).expect("resume");
    s.trigger(Trigger::VoiceEnd, now + 2).expect("end");
    s.begin_reply(now + 3).expect("reply");
    for _ in 0..20 {
        now += 10;
        if now >= cut_at + 400 {
            break;
        }
        let step = d.step(&mut s, &ev(Verdict::Known, 900, true), now);
        assert!(!matches!(step, Decision::Cut(_)));
    }
    let mut again = false;
    for _ in 0..10 {
        now += 50;
        again |= matches!(
            d.step(&mut s, &ev(Verdict::Known, 900, true), now),
            Decision::Cut(_)
        );
    }
    assert!(again);
}

#[test]
fn risky_commands_need_the_owner() {
    assert!(may_command(Verdict::Known, Risk::High));
    assert!(may_command(Verdict::Guest, Risk::Low));
    assert!(!may_command(Verdict::Guest, Risk::High));
    for v in [Verdict::Broadcast, Verdict::Uncertain] {
        assert!(!may_command(v, Risk::Low) && !may_command(v, Risk::High));
    }
}

#[test]
fn backchannels_are_recognised_and_real_requests_are_not() {
    let b = Backchannel::builtin().expect("catalog");
    for yes in [
        "mh", "Sì.", "ok", "certo", "ah sì", "va bene", "Esatto!", "mhm mhm", "capito",
    ] {
        assert!(b.is_backchannel(yes), "{yes}");
    }
    for no in [
        "no aspetta",
        "continua",
        "fammi un'altra versione",
        "sì però",
        "dimmi il meteo",
        "ok ok ok ok",
        "",
        "...",
    ] {
        assert!(!b.is_backchannel(no), "{no}");
    }
    assert_eq!(Backchannel::from_json("{}").err(), Some(DuplexError::Parse));
    assert_eq!(
        Backchannel::from_json(r#"{"max_words":0,"fillers":["a"]}"#).err(),
        Some(DuplexError::Invalid)
    );
}

#[test]
fn the_pre_roll_keeps_only_the_latest_audio() {
    let mut p = PreRoll::new(16_000, 600, 2).expect("preroll");
    assert_eq!(p.capacity(), 19_200);
    p.push(&vec![1u8; 30_000]);
    assert_eq!(p.snapshot().len(), 19_200);
    p.push(&[9u8; 100]);
    let snap = p.snapshot();
    assert_eq!(snap.len(), 19_200);
    assert_eq!(
        snap.iter().rev().take(100).copied().collect::<Vec<_>>(),
        vec![9u8; 100]
    );
    p.clear();
    assert!(p.snapshot().is_empty());
    assert!(PreRoll::new(100, 600, 2).is_err());
}

#[test]
fn barge_settings_are_validated() {
    let mut s = BargeSettings::default();
    s.duck_after_ms = s.min_voiced_ms + 1;
    assert_eq!(s.validate(), Err(DuplexError::Settings));
    assert!(BargeSettings::from_json("{}").is_err());
    let text = serde_json::to_string(&BargeSettings::default()).expect("json");
    assert!(BargeSettings::from_json(&text).is_ok());
}
