use std::time::{Duration, Instant};

use nuxiva_taskq_core::CancelToken;

use crate::{
    BargeDetector, BargeSettings, ChunkSettings, Chunker, Evidence, Session, Settings, Trigger,
    Verdict,
};

fn speaking() -> Session {
    let mut s = Session::new(Settings::default(), 0).expect("session");
    s.trigger(Trigger::VoiceStart, 1).expect("start");
    s.trigger(Trigger::VoiceEnd, 2).expect("end");
    s.begin_reply(3).expect("reply");
    s
}

#[test]
fn a_cascading_cut_with_many_tokens_stays_far_below_the_budget() {
    let mut worst = Duration::ZERO;
    for round in 0..500u64 {
        let mut s = speaking();
        let e = s.gen_for_test();
        let tokens: Vec<CancelToken> = (0..64).map(|_| CancelToken::new()).collect();
        for t in &tokens {
            s.bind(e, t.clone()).expect("bind");
        }
        let started = Instant::now();
        s.cut(0, 10 + round).expect("cut");
        worst = worst.max(started.elapsed());
        assert!(tokens.iter().all(CancelToken::is_cancelled));
    }
    assert!(worst < Duration::from_millis(20), "{worst:?}");
}

#[test]
fn the_detector_and_the_chunker_are_cheap_per_frame() {
    let mut s = speaking();
    let mut d = BargeDetector::new(BargeSettings::default()).expect("detector");
    let ev = Evidence {
        verdict: Verdict::Broadcast,
        margin_permille: 900,
        voiced: true,
        frame_ms: 20,
    };
    let started = Instant::now();
    for i in 0..50_000u64 {
        d.step(&mut s, &ev, i * 20);
    }
    assert!(
        started.elapsed() < Duration::from_secs(2),
        "{:?}",
        started.elapsed()
    );
    let mut c = Chunker::new(ChunkSettings::default()).expect("chunker");
    let started = Instant::now();
    for i in 0..20_000u64 {
        c.push("parola ", i);
    }
    assert!(
        started.elapsed() < Duration::from_secs(3),
        "{:?}",
        started.elapsed()
    );
}
