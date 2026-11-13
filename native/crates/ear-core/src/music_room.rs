use std::collections::BTreeMap;

pub const PRESENCE_ON_MS: u32 = 6_000;
pub const PRESENCE_OFF_MS: u32 = 8_000;
pub const PROBE_MIN_WAIT_MS: u64 = 2_000;
pub const PROBE_MAX_WAIT_MS: u64 = 180_000;
pub const PROBE_BUSY_MS: u64 = 90_000;
pub const MAX_MICS: usize = 64;
const MAX_FRAME_MS: u32 = 1_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RoomChange {
    Steady,
    Started,
    Stopped,
}

impl RoomChange {
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::Steady => "",
            Self::Started => "started",
            Self::Stopped => "stopped",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RoomStep {
    pub playing: bool,
    pub change: RoomChange,
    pub probe: bool,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct MusicPresence {
    heard_ms: u32,
    quiet_ms: u32,
    playing: bool,
}

impl MusicPresence {
    #[must_use]
    pub fn playing(&self) -> bool {
        self.playing
    }

    pub fn feed(&mut self, music: bool, frame_ms: u32) -> RoomChange {
        let frame = frame_ms.clamp(1, MAX_FRAME_MS);
        if music {
            self.heard_ms = self
                .heard_ms
                .saturating_add(frame)
                .min(PRESENCE_ON_MS.saturating_mul(2));
            self.quiet_ms = 0;
        } else {
            self.heard_ms = self.heard_ms.saturating_sub(frame / 2);
            self.quiet_ms = self
                .quiet_ms
                .saturating_add(frame)
                .min(PRESENCE_OFF_MS.saturating_mul(2));
        }
        if !self.playing && self.heard_ms >= PRESENCE_ON_MS {
            self.playing = true;
            return RoomChange::Started;
        }
        if self.playing && self.quiet_ms >= PRESENCE_OFF_MS {
            self.playing = false;
            self.heard_ms = 0;
            return RoomChange::Stopped;
        }
        RoomChange::Steady
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct ProbeClock {
    next_ms: u64,
    busy_since: Option<u64>,
}

impl ProbeClock {
    #[must_use]
    pub fn busy(&self, now_ms: u64) -> bool {
        self.busy_since
            .is_some_and(|t| now_ms.saturating_sub(t) < PROBE_BUSY_MS)
    }

    pub fn due(&mut self, now_ms: u64) -> bool {
        if self.busy(now_ms) || now_ms < self.next_ms {
            return false;
        }
        self.busy_since = Some(now_ms);
        true
    }

    pub fn rearm(&mut self, now_ms: u64) {
        self.next_ms = self.next_ms.min(now_ms);
    }

    pub fn finish(&mut self, now_ms: u64, wait_ms: u64) {
        self.busy_since = None;
        self.next_ms = now_ms.saturating_add(wait_ms.clamp(PROBE_MIN_WAIT_MS, PROBE_MAX_WAIT_MS));
    }
}

#[derive(Debug, Clone, Default)]
pub struct MusicRoom {
    mics: BTreeMap<u32, MusicPresence>,
    clock: ProbeClock,
    playing: bool,
    next_id: u32,
}

impl MusicRoom {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    #[must_use]
    pub fn playing(&self) -> bool {
        self.playing
    }

    #[must_use]
    pub fn mics(&self) -> usize {
        self.mics.len()
    }

    #[must_use]
    pub fn mic_playing(&self, mic: u32) -> bool {
        self.mics.get(&mic).is_some_and(MusicPresence::playing)
    }

    pub fn join(&mut self) -> Option<u32> {
        if self.mics.len() >= MAX_MICS {
            return None;
        }
        let id = self.next_id;
        self.next_id = self.next_id.wrapping_add(1);
        self.mics.insert(id, MusicPresence::default());
        Some(id)
    }

    pub fn leave(&mut self, mic: u32) -> RoomChange {
        self.mics.remove(&mic);
        self.settle()
    }

    fn settle(&mut self) -> RoomChange {
        let any = self.mics.values().any(MusicPresence::playing);
        let change = match (self.playing, any) {
            (false, true) => RoomChange::Started,
            (true, false) => RoomChange::Stopped,
            _ => RoomChange::Steady,
        };
        self.playing = any;
        change
    }

    pub fn feed(
        &mut self,
        mic: u32,
        music: bool,
        idle: bool,
        frame_ms: u32,
        now_ms: u64,
    ) -> RoomStep {
        let Some(presence) = self.mics.get_mut(&mic) else {
            return RoomStep {
                playing: self.playing,
                change: RoomChange::Steady,
                probe: false,
            };
        };
        let mine = presence.feed(music, frame_ms);
        let change = self.settle();
        if change == RoomChange::Started || mine == RoomChange::Started {
            self.clock.rearm(now_ms);
        }
        let probe = presence_probe(self.mics.get(&mic), idle) && self.clock.due(now_ms);
        RoomStep {
            playing: self.playing,
            change,
            probe,
        }
    }

    pub fn finish(&mut self, now_ms: u64, wait_ms: u64) {
        self.clock.finish(now_ms, wait_ms);
    }
}

fn presence_probe(presence: Option<&MusicPresence>, idle: bool) -> bool {
    idle && presence.is_some_and(MusicPresence::playing)
}
