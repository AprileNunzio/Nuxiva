use crate::music_room::{
    MAX_MICS, MusicPresence, MusicRoom, PRESENCE_OFF_MS, PRESENCE_ON_MS, PROBE_MAX_WAIT_MS,
    ProbeClock, RoomChange,
};

const FRAME: u32 = 30;

fn run(
    room: &mut MusicRoom,
    mic: u32,
    music: bool,
    idle: bool,
    ms: u32,
    now: &mut u64,
) -> Vec<(RoomChange, bool)> {
    let mut out = Vec::new();
    let mut left = ms;
    while left > 0 {
        let step = room.feed(mic, music, idle, FRAME, *now);
        out.push((step.change, step.probe));
        *now = now.saturating_add(u64::from(FRAME));
        left = left.saturating_sub(FRAME);
    }
    out
}

#[test]
fn presence_needs_sustained_music() {
    let mut p = MusicPresence::default();
    let mut started = false;
    for _ in 0..(PRESENCE_ON_MS / FRAME - 2) {
        started |= p.feed(true, FRAME) == RoomChange::Started;
    }
    assert!(!started);
    for _ in 0..4 {
        started |= p.feed(true, FRAME) == RoomChange::Started;
    }
    assert!(started && p.playing());
}

#[test]
fn presence_tolerates_vocal_gaps() {
    let mut p = MusicPresence::default();
    let mut changes = Vec::new();
    for i in 0..1_000u32 {
        let music = i % 10 < 7;
        changes.push(p.feed(music, FRAME));
    }
    assert!(changes.contains(&RoomChange::Started));
    assert!(!changes.contains(&RoomChange::Stopped));
    assert!(p.playing());
}

#[test]
fn presence_stops_after_silence() {
    let mut p = MusicPresence::default();
    for _ in 0..400 {
        p.feed(true, FRAME);
    }
    let mut stopped_at = None;
    for i in 0..400u32 {
        if p.feed(false, FRAME) == RoomChange::Stopped {
            stopped_at = Some(i.saturating_add(1).saturating_mul(FRAME));
            break;
        }
    }
    let at = stopped_at.unwrap_or_default();
    assert!(at >= PRESENCE_OFF_MS && at < PRESENCE_OFF_MS.saturating_add(FRAME));
    assert!(!p.playing());
}

#[test]
fn room_probes_once_when_music_starts() {
    let mut room = MusicRoom::new();
    let mic = room.join().unwrap_or_default();
    let mut now = 1_000_000;
    let steps = run(&mut room, mic, true, true, 12_000, &mut now);
    assert_eq!(
        steps.iter().filter(|s| s.0 == RoomChange::Started).count(),
        1
    );
    assert_eq!(steps.iter().filter(|s| s.1).count(), 1);
    assert!(room.playing());
}

#[test]
fn room_waits_for_finish_and_backoff() {
    let mut room = MusicRoom::new();
    let mic = room.join().unwrap_or_default();
    let mut now = 5_000;
    run(&mut room, mic, true, true, 7_000, &mut now);
    room.finish(now, 30_000);
    let soon = run(&mut room, mic, true, true, 29_000, &mut now);
    assert!(!soon.iter().any(|s| s.1));
    let later = run(&mut room, mic, true, true, 2_000, &mut now);
    assert_eq!(later.iter().filter(|s| s.1).count(), 1);
}

#[test]
fn room_never_probes_while_busy_with_conversation() {
    let mut room = MusicRoom::new();
    let mic = room.join().unwrap_or_default();
    let mut now = 0;
    let steps = run(&mut room, mic, true, false, 20_000, &mut now);
    assert!(!steps.iter().any(|s| s.1));
    let after = run(&mut room, mic, true, true, 60, &mut now);
    assert!(after.iter().any(|s| s.1));
}

#[test]
fn room_stops_only_when_every_mic_is_quiet() {
    let mut room = MusicRoom::new();
    let a = room.join().unwrap_or_default();
    let b = room.join().unwrap_or(1);
    let mut now = 0;
    run(&mut room, a, true, true, 8_000, &mut now);
    run(&mut room, b, true, true, 8_000, &mut now);
    let quiet_a = run(
        &mut room,
        a,
        false,
        true,
        PRESENCE_OFF_MS.saturating_add(600),
        &mut now,
    );
    assert!(!quiet_a.iter().any(|s| s.0 == RoomChange::Stopped));
    assert!(room.playing());
    assert_eq!(room.leave(b), RoomChange::Stopped);
    assert!(!room.playing());
}

#[test]
fn room_rearms_probe_on_new_music() {
    let mut room = MusicRoom::new();
    let mic = room.join().unwrap_or_default();
    let mut now = 0;
    run(&mut room, mic, true, true, 7_000, &mut now);
    room.finish(now, PROBE_MAX_WAIT_MS);
    run(&mut room, mic, false, true, 9_000, &mut now);
    let again = run(&mut room, mic, true, true, 7_000, &mut now);
    assert!(again.iter().any(|s| s.0 == RoomChange::Started));
    assert!(again.iter().any(|s| s.1));
}

#[test]
fn unknown_mic_is_ignored() {
    let mut room = MusicRoom::new();
    let step = room.feed(42, true, true, FRAME, 0);
    assert!(!step.probe && !step.playing && step.change == RoomChange::Steady);
}

#[test]
fn mic_limit_is_enforced() {
    let mut room = MusicRoom::new();
    for _ in 0..MAX_MICS {
        assert!(room.join().is_some());
    }
    assert!(room.join().is_none());
    assert_eq!(room.mics(), MAX_MICS);
}

#[test]
fn busy_probe_expires() {
    let mut clock = ProbeClock::default();
    assert!(clock.due(0));
    assert!(!clock.due(1_000));
    assert!(clock.due(90_000));
}
