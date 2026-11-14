use nuxiva_taskq_core::CancelToken;

use crate::{
    Audio, Control, DuplexError, EventKind, PROTOCOL_VERSION, Session, Settings, State, Trigger,
};

fn session() -> Session {
    Session::new(Settings::default(), 0).expect("session")
}

fn speaking() -> (Session, u32) {
    let mut s = session();
    s.trigger(Trigger::VoiceStart, 1).expect("start");
    s.trigger(Trigger::VoiceEnd, 2).expect("end");
    let epoch = s.begin_reply(3).expect("reply");
    (s, epoch)
}

#[test]
fn the_happy_path_walks_every_state() {
    let (mut s, epoch) = speaking();
    assert_eq!(s.state(), State::Speaking);
    assert_eq!(epoch, 1);
    assert_eq!(s.finish_reply(epoch, 10).expect("finish"), State::Idle);
}

#[test]
fn illegal_transitions_are_rejected_and_leave_state_alone() {
    let mut s = session();
    for t in [
        Trigger::VoiceEnd,
        Trigger::ReplyEnd,
        Trigger::Interrupt,
        Trigger::Resume,
    ] {
        assert_eq!(s.trigger(t, 1), Err(DuplexError::Transition));
        assert_eq!(s.state(), State::Idle);
    }
    s.trigger(Trigger::VoiceStart, 1).expect("start");
    assert_eq!(s.begin_reply(2), Err(DuplexError::Transition));
    assert_eq!(s.state(), State::Listening);
}

#[test]
fn the_transition_table_is_closed_and_reset_always_works() {
    let states = [
        State::Idle,
        State::Listening,
        State::Thinking,
        State::Speaking,
        State::Interrupted,
    ];
    let triggers = [
        Trigger::VoiceStart,
        Trigger::VoiceEnd,
        Trigger::ReplyStart,
        Trigger::ReplyEnd,
        Trigger::Interrupt,
        Trigger::Resume,
        Trigger::Reset,
    ];
    let mut legal = 0;
    for state in states {
        assert_eq!(state.next(Trigger::Reset), Some(State::Idle));
        legal += triggers
            .iter()
            .filter(|t| state.next(**t).is_some())
            .count();
    }
    assert_eq!(legal, 13);
}

#[test]
fn a_cut_discards_the_generation_and_cancels_bound_tokens() {
    let (mut s, epoch) = speaking();
    let llm = CancelToken::new();
    let child = CancelToken::new();
    s.bind(epoch, llm.clone()).expect("bind");
    s.bind(epoch, child.clone()).expect("bind");
    s.mark_spoken(epoch, 17).expect("spoken");
    let report = s.cut(epoch, 50).expect("cut");
    assert_eq!(report.cancelled, 2);
    assert_eq!(report.state, State::Interrupted);
    let note = report.interruption.expect("note");
    assert_eq!(
        (note.epoch, note.spoken_chars, note.fade_ms),
        (epoch, 17, 30)
    );
    assert!(llm.is_cancelled() && child.is_cancelled());
    assert!(!s.is_live(epoch));
    assert_eq!(s.next_out_seq(epoch), Err(DuplexError::Stale));
    assert_eq!(s.admit(epoch, 1, 51), Err(DuplexError::Stale));
    assert_eq!(s.mark_spoken(epoch, 1), Err(DuplexError::Stale));
}

#[test]
fn a_late_binding_to_a_cut_generation_is_cancelled_at_once() {
    let (mut s, epoch) = speaking();
    s.cut(0, 10).expect("cut");
    let late = CancelToken::new();
    assert_eq!(s.bind(epoch, late.clone()), Err(DuplexError::Stale));
    assert!(late.is_cancelled());
    assert_eq!(
        s.bind(epoch + 5, CancelToken::new()),
        Err(DuplexError::Stale)
    );
}

#[test]
fn a_cut_does_not_touch_a_newer_generation() {
    let (mut s, first) = speaking();
    s.cut(first, 10).expect("cut");
    s.trigger(Trigger::Resume, 11).expect("resume");
    s.trigger(Trigger::VoiceEnd, 12).expect("end");
    let second = s.begin_reply(13).expect("reply");
    assert!(second > first);
    let token = CancelToken::new();
    s.bind(second, token.clone()).expect("bind");
    assert_eq!(s.cut(first, 14).expect("cut").cancelled, 0);
    assert!(!token.is_cancelled());
    assert!(s.is_live(second));
    assert_eq!(s.state(), State::Speaking);
}

#[test]
fn cutting_the_future_is_invalid() {
    let (mut s, epoch) = speaking();
    assert_eq!(s.cut(epoch + 1, 5).err(), Some(DuplexError::Invalid));
}

#[test]
fn interrupt_trigger_goes_through_the_cut() {
    let (mut s, epoch) = speaking();
    let token = CancelToken::new();
    s.bind(epoch, token.clone()).expect("bind");
    assert_eq!(s.trigger(Trigger::Interrupt, 9), Ok(State::Interrupted));
    assert!(token.is_cancelled());
    assert!(s.interruption().is_some());
}

#[test]
fn sequences_must_increase_per_stream() {
    let mut s = session();
    s.admit(0, 1, 0).expect("one");
    s.admit(0, 2, 0).expect("two");
    assert_eq!(s.admit(0, 2, 0), Err(DuplexError::Sequence));
    assert_eq!(s.admit(0, 1, 0), Err(DuplexError::Sequence));
    s.admit(0, 9, 0).expect("gap allowed");
}

#[test]
fn the_rate_limiter_has_a_burst_and_refills() {
    let mut s = session();
    let mut ok = 0u32;
    for seq in 1..=1_000 {
        if s.admit(0, seq, 0).is_ok() {
            ok += 1;
        }
    }
    assert_eq!(ok, 200);
    assert!(
        s.drain_events()
            .iter()
            .any(|e| e.kind == EventKind::RateLimited)
    );
    s.admit(0, 5_000, 1_000).expect("refilled after a second");
}

#[test]
fn timeouts_return_to_a_safe_state_and_release_tokens() {
    let (mut s, epoch) = speaking();
    let token = CancelToken::new();
    s.bind(epoch, token.clone()).expect("bind");
    assert_eq!(s.tick(3 + 299_999), None);
    assert_eq!(s.tick(3 + 300_000), Some(State::Idle));
    assert!(token.is_cancelled());
    assert!(!s.is_live(epoch));
    assert_eq!(s.tick(9_999_999), None);
}

#[test]
fn interrupted_falls_back_to_listening() {
    let (mut s, _) = speaking();
    s.cut(0, 100).expect("cut");
    assert_eq!(s.tick(2_100), Some(State::Listening));
}

#[test]
fn reset_cancels_everything_from_any_state() {
    let (mut s, epoch) = speaking();
    let token = CancelToken::new();
    s.bind(epoch, token.clone()).expect("bind");
    assert_eq!(s.trigger(Trigger::Reset, 4), Ok(State::Idle));
    assert!(token.is_cancelled());
    assert_eq!(s.snapshot().bound_tokens, 0);
}

#[test]
fn token_and_event_capacity_are_bounded() {
    let settings = Settings {
        max_cancel_tokens: 2,
        event_cap: 8,
        ..Settings::default()
    };
    let mut s = Session::new(settings, 0).expect("session");
    s.trigger(Trigger::VoiceStart, 1).expect("start");
    s.trigger(Trigger::VoiceEnd, 2).expect("end");
    let epoch = s.begin_reply(3).expect("reply");
    s.bind(epoch, CancelToken::new()).expect("a");
    s.bind(epoch, CancelToken::new()).expect("b");
    assert_eq!(
        s.bind(epoch, CancelToken::new()),
        Err(DuplexError::Capacity)
    );
    for t in 0..50 {
        s.trigger(Trigger::Reset, 10 + t).expect("reset");
    }
    assert!(s.drain_events().len() <= 8);
}

#[test]
fn output_sequences_restart_per_generation() {
    let (mut s, epoch) = speaking();
    assert_eq!(s.next_out_seq(epoch), Ok(1));
    assert_eq!(s.next_out_seq(epoch), Ok(2));
    assert_eq!(s.next_out_seq(epoch + 1), Err(DuplexError::Stale));
    s.finish_reply(epoch, 5).expect("finish");
    s.trigger(Trigger::VoiceStart, 6).expect("start");
    s.trigger(Trigger::VoiceEnd, 7).expect("end");
    let next = s.begin_reply(8).expect("reply");
    assert_eq!(s.next_out_seq(next), Ok(1));
    assert_eq!(s.next_out_seq(epoch), Err(DuplexError::Stale));
}

#[test]
fn control_frames_round_trip_and_reject_unknown_fields() {
    let settings = Settings::default();
    let frames = [
        Control::Hello {
            version: PROTOCOL_VERSION,
        },
        Control::State {
            state: State::Speaking,
            epoch: 3,
        },
        Control::Text {
            epoch: 1,
            seq: 2,
            text: "ciao".into(),
        },
        Control::Cut { epoch: 4 },
        Control::Spoken { epoch: 1, chars: 9 },
        Control::Error {
            code: "duplex.stale".into(),
        },
    ];
    for frame in frames {
        let text = frame.encode().expect("encode");
        assert_eq!(Control::parse(&text, &settings).expect("parse"), frame);
    }
    assert_eq!(
        Control::parse(r#"{"type":"cut","gen":1,"x":2}"#, &settings),
        Err(DuplexError::Parse)
    );
    assert_eq!(
        Control::parse(r#"{"type":"hello","version":99}"#, &settings),
        Err(DuplexError::Version)
    );
    assert_eq!(Control::parse("nope", &settings), Err(DuplexError::Parse));
}

#[test]
fn oversized_frames_are_refused() {
    let settings = Settings::default();
    let big = "a".repeat(settings.max_text_bytes + 1);
    let json = format!(r#"{{"type":"text","gen":1,"seq":1,"text":"{big}"}}"#);
    assert_eq!(Control::parse(&json, &settings), Err(DuplexError::TooLarge));
    let huge = vec![1u8; settings.max_audio_bytes + 10];
    assert_eq!(Audio::decode(&huge, &settings), Err(DuplexError::TooLarge));
}

#[test]
fn audio_frames_round_trip_and_reject_garbage() {
    let settings = Settings::default();
    let frame = Audio {
        epoch: 7,
        seq: 42,
        pcm: vec![1, 2, 3, 4],
    };
    assert_eq!(
        Audio::decode(&frame.encode(), &settings).expect("decode"),
        frame
    );
    assert_eq!(Audio::decode(&[], &settings), Err(DuplexError::Parse));
    assert_eq!(
        Audio::decode(&[1, 0, 0], &settings),
        Err(DuplexError::Parse)
    );
    let mut bad = frame.encode();
    bad[0] = 9;
    assert_eq!(Audio::decode(&bad, &settings), Err(DuplexError::Invalid));
    let empty = Audio {
        epoch: 1,
        seq: 1,
        pcm: vec![],
    };
    assert_eq!(
        Audio::decode(&empty.encode(), &settings),
        Err(DuplexError::TooLarge)
    );
}

#[test]
fn settings_are_validated() {
    assert!(Settings::from_json("{}").is_err());
    let mut s = Settings::default();
    s.fade_ms = 31;
    assert_eq!(s.validate(), Err(DuplexError::Settings));
    let mut s = Settings::default();
    s.rate_burst = 1;
    assert_eq!(s.validate(), Err(DuplexError::Settings));
    let text = serde_json::to_string(&Settings::default()).expect("json");
    assert_eq!(Settings::from_json(&text).expect("ok"), Settings::default());
    assert_eq!(
        Settings::from_json(&"x".repeat(20_000)),
        Err(DuplexError::TooLarge)
    );
}

#[test]
fn error_codes_are_unique_and_namespaced() {
    let mut codes: Vec<_> = DuplexError::ALL.iter().map(|e| e.code()).collect();
    assert!(codes.iter().all(|c| c.starts_with("duplex.")));
    codes.sort_unstable();
    codes.dedup();
    assert_eq!(codes.len(), DuplexError::ALL.len());
}

#[test]
fn a_fuzzed_storm_never_breaks_invariants() {
    let mut s = session();
    let mut x: u64 = 0x9E37_79B9_7F4A_7C15;
    let mut now = 0u64;
    let triggers = [
        Trigger::VoiceStart,
        Trigger::VoiceEnd,
        Trigger::ReplyStart,
        Trigger::ReplyEnd,
        Trigger::Interrupt,
        Trigger::Resume,
        Trigger::Reset,
    ];
    for _ in 0..20_000 {
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        now += x % 400;
        match x % 6 {
            0 => {
                let _ = s.trigger(triggers[(x >> 8) as usize % triggers.len()], now);
            }
            1 => {
                let _ = s.begin_reply(now);
            }
            2 => {
                let _ = s.cut((x >> 8) as u32 % 4, now);
            }
            3 => {
                let _ = s.admit((x >> 8) as u32 % 3, (x >> 16) as u32 % 50, now);
            }
            4 => {
                let _ = s.bind(s.epoch(), CancelToken::new());
            }
            _ => {
                let _ = s.tick(now);
            }
        }
        let snap = s.snapshot();
        assert!(snap.cut_upto <= snap.epoch);
        assert!(snap.bound_tokens <= 64);
        if snap.state == State::Idle {
            assert!(s.drain_events().len() <= 256);
        }
    }
}
