use crate::{
    BargeDetector, Decision, Evidence, Session, Settings, State, Trigger, Verdict, WindowInput,
    judge_window, windowed_settings,
};

fn base() -> WindowInput {
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

fn run(inputs: &[WindowInput]) -> (usize, State) {
    let mut s = speaking();
    let mut d = BargeDetector::new(windowed_settings()).expect("detector");
    let mut cuts = 0;
    for (i, input) in inputs.iter().enumerate() {
        let ev: Evidence = judge_window(input);
        if matches!(d.step(&mut s, &ev, 100 + i as u64 * 250), Decision::Cut(_)) {
            cuts += 1;
        }
    }
    (cuts, s.state())
}

#[test]
fn a_strong_owner_voice_is_known_with_margin() {
    let ev = judge_window(&base());
    assert_eq!(ev.verdict, Verdict::Known);
    assert_eq!(ev.margin_permille, 250);
}

#[test]
fn doubtful_cases_are_never_known() {
    let cases = [
        WindowInput {
            score: 0.70,
            ..base()
        },
        WindowInput {
            runner_up: 0.80,
            ..base()
        },
        WindowInput {
            has_match: false,
            ..base()
        },
        WindowInput {
            score: f32::NAN,
            ..base()
        },
        WindowInput {
            echo_cancelled: false,
            ..base()
        },
        WindowInput {
            voiced: false,
            ..base()
        },
    ];
    for c in cases {
        assert_eq!(judge_window(&c).verdict, Verdict::Uncertain, "{c:?}");
    }
}

#[test]
fn music_programme_and_radio_are_broadcast() {
    for c in [
        WindowInput {
            music: true,
            ..base()
        },
        WindowInput {
            programme: true,
            ..base()
        },
    ] {
        assert_eq!(judge_window(&c).verdict, Verdict::Broadcast);
    }
}

#[test]
fn three_consecutive_strong_windows_cut_and_two_do_not() {
    assert_eq!(run(&[base(), base()]), (0, State::Speaking));
    let (cuts, state) = run(&[base(), base(), base()]);
    assert_eq!((cuts, state), (1, State::Interrupted));
}

#[test]
fn one_doubtful_window_breaks_the_streak() {
    let weak = WindowInput {
        score: 0.7,
        ..base()
    };
    assert_eq!(
        run(&[base(), base(), weak, base(), base()]),
        (0, State::Speaking)
    );
}

#[test]
fn radio_with_the_owner_like_voice_never_cuts() {
    let radio = WindowInput {
        programme: true,
        score: 0.95,
        ..base()
    };
    let song = WindowInput {
        music: true,
        score: 0.95,
        ..base()
    };
    let inputs: Vec<WindowInput> = (0..2_000)
        .map(|i| if i % 2 == 0 { radio } else { song })
        .collect();
    assert_eq!(run(&inputs), (0, State::Speaking));
}

#[test]
fn a_guest_or_unmatched_voice_never_cuts() {
    let guest = WindowInput {
        has_match: false,
        score: 0.9,
        ..base()
    };
    let near = WindowInput {
        score: 0.65,
        ..base()
    };
    assert_eq!(run(&vec![guest; 500]), (0, State::Speaking));
    assert_eq!(run(&vec![near; 500]), (0, State::Speaking));
}

#[test]
fn without_echo_cancellation_nothing_cuts() {
    let raw = WindowInput {
        echo_cancelled: false,
        ..base()
    };
    assert_eq!(run(&vec![raw; 500]), (0, State::Speaking));
}
