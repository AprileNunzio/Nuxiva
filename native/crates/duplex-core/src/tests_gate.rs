use crate::{
    AttributionChain, BargeDetector, Decision, Session, Settings, State, Trigger, Verdict,
    WINDOW_SAMPLES, WindowGate, WindowInput, windowed_settings,
};

const FRAME: usize = 480;

fn input() -> WindowInput {
    WindowInput {
        voiced: true,
        has_match: true,
        score: 0.85,
        runner_up: 0.3,
        limit: 0.6,
        music: false,
        programme: false,
        echo_cancelled: true,
    }
}

fn speaking() -> Session {
    let mut s = Session::new(Settings::default(), 0).expect("session");
    s.trigger(Trigger::VoiceStart, 1).expect("start");
    s.trigger(Trigger::VoiceEnd, 2).expect("end");
    s.begin_reply(3).expect("reply");
    s
}

fn drive(windows: &[(WindowInput, Option<&str>)]) -> (usize, State) {
    let mut session = speaking();
    let mut detector = BargeDetector::new(windowed_settings()).expect("detector");
    let mut chain = AttributionChain::new();
    let mut cuts = 0;
    for (i, (w, slug)) in windows.iter().enumerate() {
        let ev = chain.judge(w, *slug);
        if matches!(
            detector.step(&mut session, &ev, 100 + i as u64 * 250),
            Decision::Cut(_)
        ) {
            cuts += 1;
        }
    }
    (cuts, session.state())
}

#[test]
fn nine_frames_close_one_window_and_the_gate_stays_busy_until_released() {
    let mut gate = WindowGate::new();
    let frame = vec![0.1_f32; FRAME];
    for _ in 0..8 {
        assert!(gate.push(&frame, true).is_none());
    }
    let window = gate.push(&frame, true).expect("window");
    assert_eq!(window.samples.len(), WINDOW_SAMPLES);
    assert!(window.voiced);
    assert!(gate.busy());
    for _ in 0..30 {
        assert!(gate.push(&frame, true).is_none());
    }
    gate.release();
    assert!(gate.push(&frame, true).is_some());
}

#[test]
fn voiced_needs_at_least_half_of_the_frames() {
    let mut gate = WindowGate::new();
    let frame = vec![0.1_f32; FRAME];
    let mut out = None;
    for i in 0..9 {
        out = gate.push(&frame, i < 4);
    }
    assert!(!out.take().expect("window").voiced);
    gate.release();
    for i in 0..9 {
        out = gate.push(&frame, i < 5);
    }
    assert!(out.expect("window").voiced);
}

#[test]
fn hostile_frames_never_panic_and_never_count_as_voice() {
    let mut gate = WindowGate::new();
    let poison = vec![f32::NAN; FRAME];
    let mut out = None;
    for _ in 0..9 {
        out = gate.push(&poison, true);
    }
    let window = out.expect("window");
    assert!(!window.voiced);
    assert!(window.samples.iter().all(|s| s.is_finite()));
    gate.release();
    assert!(gate.push(&[], true).is_none());
    assert!(gate.push(&vec![0.0; 20_000], true).is_none());
}

#[test]
fn three_windows_of_the_same_person_cut_after_the_slug_settles() {
    let strong = (input(), Some("anna"));
    let (cuts, state) = drive(&[strong; 4].map(|(w, s)| (w, s)));
    assert_eq!(cuts, 1);
    assert_eq!(state, State::Interrupted);
}

#[test]
fn alternating_people_never_cut() {
    let mut windows = Vec::new();
    for i in 0..40 {
        windows.push((input(), Some(if i % 2 == 0 { "anna" } else { "luca" })));
    }
    assert_eq!(drive(&windows).0, 0);
}

#[test]
fn a_person_switch_restarts_the_confirmation() {
    let mut windows = vec![(input(), Some("anna")), (input(), Some("anna"))];
    windows.extend(vec![(input(), Some("luca")); 3]);
    assert_eq!(drive(&windows).0, 0);
    windows.push((input(), Some("luca")));
    windows.push((input(), Some("luca")));
    assert_eq!(drive(&windows).0, 1);
}

#[test]
fn a_known_window_without_a_valid_slug_is_uncertain() {
    let mut chain = AttributionChain::new();
    for slug in [None, Some(""), Some("a b"), Some("é")] {
        for _ in 0..4 {
            assert_eq!(chain.judge(&input(), slug).verdict, Verdict::Uncertain);
        }
    }
    let long = "x".repeat(65);
    for _ in 0..4 {
        assert_eq!(
            chain.judge(&input(), Some(&long)).verdict,
            Verdict::Uncertain
        );
    }
}

#[test]
fn broadcast_quarantines_the_owner_for_eight_windows() {
    let mut chain = AttributionChain::new();
    assert_eq!(
        chain.judge(&input(), Some("anna")).verdict,
        Verdict::Uncertain
    );
    assert_eq!(chain.judge(&input(), Some("anna")).verdict, Verdict::Known);
    let radio = WindowInput {
        music: true,
        ..input()
    };
    assert_eq!(chain.judge(&radio, None).verdict, Verdict::Broadcast);
    assert!(chain.quarantined());
    for _ in 0..8 {
        assert_ne!(chain.judge(&input(), Some("anna")).verdict, Verdict::Known);
    }
    assert!(!chain.quarantined());
    assert_eq!(
        chain.judge(&input(), Some("anna")).verdict,
        Verdict::Uncertain
    );
    assert_eq!(chain.judge(&input(), Some("anna")).verdict, Verdict::Known);
}

#[test]
fn radio_mixed_with_the_owner_never_cuts() {
    let mut windows = Vec::new();
    for i in 0..60 {
        let radio = i % 5 == 0;
        windows.push((
            WindowInput {
                programme: radio,
                ..input()
            },
            Some("anna"),
        ));
    }
    assert_eq!(drive(&windows).0, 0);
}

#[test]
fn without_echo_cancellation_nothing_is_ever_known() {
    let windows = vec![
        (
            WindowInput {
                echo_cancelled: false,
                ..input()
            },
            Some("anna"),
        );
        40
    ];
    assert_eq!(drive(&windows).0, 0);
}

#[test]
fn non_finite_scores_are_never_known() {
    let mut chain = AttributionChain::new();
    for bad in [f32::NAN, f32::INFINITY, f32::NEG_INFINITY] {
        for _ in 0..4 {
            let w = WindowInput {
                score: bad,
                ..input()
            };
            assert_eq!(chain.judge(&w, Some("anna")).verdict, Verdict::Uncertain);
        }
    }
}

#[test]
#[allow(clippy::cast_possible_truncation)]
fn randomised_streams_never_cut_without_a_stable_strong_owner() {
    let mut x = 0x9e37_79b9_7f4a_7c15_u64;
    for _ in 0..200 {
        let mut windows = Vec::new();
        for _ in 0..80 {
            x ^= x << 13;
            x ^= x >> 7;
            x ^= x << 17;
            let r = f32::from((x % 1000) as u16) / 1000.0;
            let slug = match x % 3 {
                0 => Some("anna"),
                1 => Some("luca"),
                _ => None,
            };
            windows.push((
                WindowInput {
                    voiced: x % 7 != 0,
                    has_match: x % 5 != 0,
                    score: r,
                    runner_up: f32::from((x % 400) as u16) / 1000.0,
                    limit: 0.6,
                    music: x % 11 == 0,
                    programme: x % 13 == 0,
                    echo_cancelled: x % 17 != 0,
                },
                slug,
            ));
        }
        let mut chain = AttributionChain::new();
        let mut streak = 0;
        for (w, slug) in &windows {
            let ev = chain.judge(w, *slug);
            if ev.verdict == Verdict::Known {
                streak += 1;
                assert!(w.voiced && w.echo_cancelled && !w.music && !w.programme);
                assert!(w.score - w.limit >= 0.12 - f32::EPSILON);
                assert!(streak >= 1);
            } else {
                streak = 0;
            }
        }
    }
}
