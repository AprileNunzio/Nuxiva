use std::collections::{BTreeMap, VecDeque};

pub const MAX_CAMERAS: usize = 16;
pub const MAX_TRACKS: usize = 16;
pub const MAX_BODIES: usize = 32;
pub const MAX_SAMPLES: usize = 96;
pub const UPRIGHT: f64 = 1.4;
pub const LOW_ASPECT: f64 = 1.0;
pub const LOW_SHRINK: f64 = 0.4;
pub const MIN_DROP: f64 = 0.35;
pub const MATCH_IOU: f64 = 0.15;
pub const HISTORY_S: f64 = 30.0;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PostureConfig {
    pub fall_window_s: f64,
    pub confirm_s: f64,
    pub immobile_s: f64,
    pub still_frac: f64,
    pub max_gap_s: f64,
}

impl Default for PostureConfig {
    fn default() -> Self {
        Self {
            fall_window_s: 2.5,
            confirm_s: 4.0,
            immobile_s: 60.0,
            still_frac: 0.04,
            max_gap_s: 6.0,
        }
    }
}

impl PostureConfig {
    #[must_use]
    pub fn valid(&self) -> bool {
        let ok = |v: f64, lo: f64, hi: f64| v.is_finite() && v >= lo && v <= hi;
        ok(self.fall_window_s, 0.5, 6.0)
            && ok(self.confirm_s, 1.0, 30.0)
            && ok(self.immobile_s, 10.0, 3600.0)
            && ok(self.still_frac, 0.005, 0.3)
            && ok(self.max_gap_s, 1.0, 60.0)
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Body {
    pub x: f64,
    pub y: f64,
    pub w: f64,
    pub h: f64,
    pub score: f64,
    pub rest: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PostureKind {
    Fall,
    Immobility,
}

impl PostureKind {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Fall => "fall",
            Self::Immobility => "immobility",
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct PostureEvent {
    pub camera: String,
    pub track: u32,
    pub kind: PostureKind,
    pub probability: f64,
    pub confidence: f64,
    pub at: f64,
}

#[derive(Debug, Clone, Copy, PartialEq)]
struct Sample {
    t: f64,
    cx: f64,
    cy: f64,
    top: f64,
    w: f64,
    h: f64,
    aspect: f64,
    score: f64,
    rest: bool,
}

impl Sample {
    fn iou(&self, other: &Self) -> f64 {
        let (ax0, ax1, ay0, ay1) = (
            self.cx - self.w / 2.0,
            self.cx + self.w / 2.0,
            self.top,
            self.top + self.h,
        );
        let (bx0, bx1, by0, by1) = (
            other.cx - other.w / 2.0,
            other.cx + other.w / 2.0,
            other.top,
            other.top + other.h,
        );
        let iw = (ax1.min(bx1) - ax0.max(bx0)).max(0.0);
        let ih = (ay1.min(by1) - ay0.max(by0)).max(0.0);
        let inter = iw * ih;
        let union = self.w * self.h + other.w * other.h - inter;
        if union > 0.0 { inter / union } else { 0.0 }
    }
}

#[derive(Debug, Clone)]
struct Track {
    id: u32,
    samples: VecDeque<Sample>,
    candidate: Option<(f64, f64)>,
    fell: bool,
    fall_sent: bool,
    anchor: Option<Sample>,
    immobile_sent: bool,
}

impl Track {
    fn last(&self) -> Option<&Sample> {
        self.samples.back()
    }

    fn upright_ref(&self, now: f64, window: f64) -> Option<Sample> {
        self.samples
            .iter()
            .rev()
            .skip(1)
            .filter(|s| now - s.t <= window)
            .find(|s| s.aspect >= UPRIGHT)
            .copied()
    }

    fn low(&self, s: &Sample) -> bool {
        let tallest = self
            .samples
            .iter()
            .filter(|p| p.aspect >= UPRIGHT)
            .map(|p| p.h)
            .fold(0.0_f64, f64::max);
        s.aspect <= LOW_ASPECT || (tallest > 0.0 && s.h <= tallest * LOW_SHRINK)
    }

    fn confidence(&self) -> f64 {
        let recent: Vec<f64> = self.samples.iter().rev().take(5).map(|s| s.score).collect();
        if recent.is_empty() {
            return 0.0;
        }
        #[allow(clippy::cast_precision_loss)]
        let n = recent.len() as f64;
        (recent.iter().sum::<f64>() / n * 0.9).clamp(0.0, 1.0)
    }
}

#[derive(Debug, Default)]
struct Camera {
    tracks: Vec<Track>,
    next: u32,
}

#[derive(Debug)]
pub struct Posture {
    config: PostureConfig,
    cameras: BTreeMap<String, Camera>,
}

fn label_ok(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 96
        && value
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '_' | '-' | '.' | ':' | '/'))
}

fn sample_of(b: &Body, fw: f64, fh: f64, t: f64) -> Option<Sample> {
    let finite = [b.x, b.y, b.w, b.h, b.score].iter().all(|v| v.is_finite());
    if !finite
        || b.w <= 1.0
        || b.h <= 1.0
        || b.x < -fw
        || b.y < -fh
        || b.x > fw * 2.0
        || b.y > fh * 2.0
    {
        return None;
    }
    Some(Sample {
        t,
        cx: (b.x + b.w / 2.0) / fh,
        cy: (b.y + b.h / 2.0) / fh,
        top: b.y / fh,
        w: b.w / fh,
        h: b.h / fh,
        aspect: b.h / b.w,
        score: b.score.clamp(0.0, 1.0),
        rest: b.rest,
    })
}

impl Posture {
    #[must_use]
    pub fn new(config: PostureConfig) -> Option<Self> {
        config.valid().then(|| Self {
            config,
            cameras: BTreeMap::new(),
        })
    }

    #[must_use]
    pub fn tracks(&self, camera: &str) -> usize {
        self.cameras.get(camera).map_or(0, |c| c.tracks.len())
    }

    pub fn observe(
        &mut self,
        camera: &str,
        t: f64,
        fw: f64,
        fh: f64,
        bodies: &[Body],
    ) -> Vec<PostureEvent> {
        let frame_ok = fw.is_finite()
            && fh.is_finite()
            && fw >= 16.0
            && fh >= 16.0
            && fw <= 16_384.0
            && fh <= 16_384.0;
        if !label_ok(camera) || !t.is_finite() || t < 0.0 || !frame_ok {
            return Vec::new();
        }
        if !self.cameras.contains_key(camera) && self.cameras.len() >= MAX_CAMERAS {
            return Vec::new();
        }
        let config = self.config;
        let cam = self.cameras.entry(camera.to_owned()).or_default();
        cam.tracks.retain(|tr| {
            tr.last()
                .is_some_and(|s| t - s.t <= config.max_gap_s && s.t <= t)
        });
        let samples: Vec<Sample> = bodies
            .iter()
            .take(MAX_BODIES)
            .filter_map(|b| sample_of(b, fw, fh, t))
            .collect();
        let mut taken = vec![false; cam.tracks.len()];
        let mut events = Vec::new();
        for s in samples {
            let best = cam
                .tracks
                .iter()
                .enumerate()
                .filter(|(i, _)| !taken.get(*i).copied().unwrap_or(true))
                .filter_map(|(i, tr)| tr.last().map(|l| (i, l.iou(&s))))
                .filter(|(_, iou)| *iou >= MATCH_IOU)
                .max_by(|a, b| a.1.total_cmp(&b.1));
            let index = match best {
                Some((i, _)) => i,
                None if cam.tracks.len() < MAX_TRACKS => {
                    cam.next = cam.next.wrapping_add(1);
                    cam.tracks.push(Track {
                        id: cam.next,
                        samples: VecDeque::new(),
                        candidate: None,
                        fell: false,
                        fall_sent: false,
                        anchor: None,
                        immobile_sent: false,
                    });
                    taken.push(false);
                    cam.tracks.len().saturating_sub(1)
                }
                None => continue,
            };
            if let Some(slot) = taken.get_mut(index) {
                *slot = true;
            }
            if let Some(track) = cam.tracks.get_mut(index) {
                step(track, s, &config, camera, &mut events);
            }
        }
        events
    }
}

fn push(track: &mut Track, s: Sample) {
    track.samples.push_back(s);
    while track.samples.len() > MAX_SAMPLES
        || track.samples.front().is_some_and(|f| s.t - f.t > HISTORY_S)
    {
        track.samples.pop_front();
    }
}

fn step(
    track: &mut Track,
    s: Sample,
    config: &PostureConfig,
    camera: &str,
    events: &mut Vec<PostureEvent>,
) {
    push(track, s);
    if s.aspect >= UPRIGHT {
        track.candidate = None;
        track.fell = false;
        track.fall_sent = false;
        track.anchor = None;
        track.immobile_sent = false;
        return;
    }
    let low = track.low(&s);
    if !low {
        track.candidate = None;
        track.anchor = None;
        return;
    }
    if track.candidate.is_none() && !track.fall_sent {
        if let Some(r) = track.upright_ref(s.t, config.fall_window_s) {
            let drop = (s.top - r.top) / r.h.max(1e-6);
            if drop >= MIN_DROP {
                let speed =
                    ((config.fall_window_s - (s.t - r.t)) / config.fall_window_s).clamp(0.0, 1.0);
                let size = ((drop - MIN_DROP) / 0.4).clamp(0.0, 1.0);
                let mut p = 0.55 + 0.25 * size + 0.15 * speed;
                if s.rest {
                    p *= 0.5;
                }
                track.candidate = Some((s.t, p.clamp(0.0, 0.95)));
            }
        }
    }
    if let Some((since, p)) = track.candidate {
        if !track.fall_sent && s.t - since >= config.confirm_s {
            track.fall_sent = true;
            track.fell = true;
            events.push(PostureEvent {
                camera: camera.to_owned(),
                track: track.id,
                kind: PostureKind::Fall,
                probability: p,
                confidence: track.confidence(),
                at: since,
            });
        }
    }
    if s.rest && !track.fell {
        track.anchor = None;
        return;
    }
    let moved = track
        .anchor
        .is_none_or(|a| ((s.cx - a.cx).powi(2) + (s.cy - a.cy).powi(2)).sqrt() > config.still_frac);
    if moved {
        track.anchor = Some(s);
        return;
    }
    if let Some(a) = track.anchor {
        if !track.immobile_sent && s.t - a.t >= config.immobile_s {
            track.immobile_sent = true;
            events.push(PostureEvent {
                camera: camera.to_owned(),
                track: track.id,
                kind: PostureKind::Immobility,
                probability: if track.fell { 0.9 } else { 0.7 },
                confidence: track.confidence(),
                at: s.t,
            });
        }
    }
}
