#![allow(clippy::cast_precision_loss)]

use crate::image::{Gray, ramp};

pub const SIDE: usize = 112;
const MIN_BLOB: usize = 10;
const MAX_BLOB: usize = 700;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Traits {
    pub glasses: f32,
    pub beard: f32,
    pub fringe: f32,
    pub cigarette: f32,
}

#[derive(Debug, Clone, Copy)]
struct Rect {
    x0: usize,
    x1: usize,
    y0: usize,
    y1: usize,
}

const fn rect(x0: usize, x1: usize, y0: usize, y1: usize) -> Rect {
    Rect { x0, x1, y0, y1 }
}

#[derive(Debug, Clone, Copy, Default)]
struct Stats {
    lum: f32,
    gx: f32,
    gy: f32,
    std: f32,
}

impl Stats {
    fn grad(&self) -> f32 {
        f32::midpoint(self.gx, self.gy)
    }

    fn merge(a: Self, b: Self) -> Self {
        Self {
            lum: f32::midpoint(a.lum, b.lum),
            gx: f32::midpoint(a.gx, b.gx),
            gy: f32::midpoint(a.gy, b.gy),
            std: f32::midpoint(a.std, b.std),
        }
    }
}

struct Plane {
    v: Vec<f32>,
}

impl Plane {
    fn at(&self, x: usize, y: usize) -> f32 {
        self.v
            .get(y.saturating_mul(SIDE).saturating_add(x))
            .copied()
            .unwrap_or(0.0)
    }

    fn stats(&self, r: Rect) -> Stats {
        let (mut lum, mut sq, mut gx, mut gy, mut n) = (0.0f32, 0.0f32, 0.0f32, 0.0f32, 0.0f32);
        let last = SIDE.saturating_sub(1);
        for y in r.y0.max(1)..r.y1.min(last) {
            for x in r.x0.max(1)..r.x1.min(last) {
                let p = self.at(x, y);
                lum += p;
                sq += p * p;
                gx += (self.at(x.saturating_add(1), y) - self.at(x.saturating_sub(1), y)).abs();
                gy += (self.at(x, y.saturating_add(1)) - self.at(x, y.saturating_sub(1))).abs();
                n += 1.0;
            }
        }
        if n < 1.0 {
            return Stats::default();
        }
        let mean = lum / n;
        Stats {
            lum: mean,
            gx: gx / n,
            gy: gy / n,
            std: (sq / n - mean * mean).max(0.0).sqrt(),
        }
    }
}

fn ratio(a: f32, b: f32) -> f32 {
    a / b.max(1.0)
}

fn glasses(p: &Plane) -> f32 {
    let control = p.stats(rect(16, 96, 30, 100)).grad();
    let bridge = p.stats(rect(50, 62, 42, 58)).gy;
    let rims = f32::midpoint(
        p.stats(rect(24, 48, 60, 68)).gy,
        p.stats(rect(64, 88, 60, 68)).gy,
    );
    let temples = f32::midpoint(
        p.stats(rect(12, 22, 40, 64)).gx,
        p.stats(rect(90, 100, 40, 64)).gx,
    );
    let main = ramp(ratio(bridge, control), 0.8, 1.6);
    let side = ramp(ratio(rims, control), 1.0, 1.9).min(ramp(ratio(temples, control), 0.9, 1.7));
    main.max(side * 0.8)
}

fn hair_like(p: &Plane, zone: Stats) -> f32 {
    let cheeks = Stats::merge(p.stats(rect(24, 40, 60, 78)), p.stats(rect(72, 88, 60, 78)));
    let darker = 1.0 - ratio(zone.lum, cheeks.lum);
    let texture = ratio(zone.grad(), cheeks.grad());
    0.5 * ramp(darker, 0.08, 0.35) + 0.5 * ramp(texture, 1.15, 2.0)
}

fn beard(p: &Plane) -> f32 {
    let chin = p.stats(rect(36, 76, 100, 111));
    let jaw = Stats::merge(
        p.stats(rect(20, 34, 82, 104)),
        p.stats(rect(78, 92, 82, 104)),
    );
    hair_like(p, Stats::merge(chin, jaw))
}

fn fringe(p: &Plane) -> f32 {
    hair_like(p, p.stats(rect(30, 82, 4, 24)))
}

struct Blob {
    count: f32,
    sx: f32,
    sy: f32,
    sxx: f32,
    syy: f32,
    sxy: f32,
    min_x: usize,
    max_x: usize,
    min_y: usize,
    max_y: usize,
}

impl Blob {
    const fn new(x: usize, y: usize) -> Self {
        Self {
            count: 0.0,
            sx: 0.0,
            sy: 0.0,
            sxx: 0.0,
            syy: 0.0,
            sxy: 0.0,
            min_x: x,
            max_x: x,
            min_y: y,
            max_y: y,
        }
    }

    fn add(&mut self, x: usize, y: usize) {
        let (fx, fy) = (x as f32, y as f32);
        self.count += 1.0;
        self.sx += fx;
        self.sy += fy;
        self.sxx += fx * fx;
        self.syy += fy * fy;
        self.sxy += fx * fy;
        self.min_x = self.min_x.min(x);
        self.max_x = self.max_x.max(x);
        self.min_y = self.min_y.min(y);
        self.max_y = self.max_y.max(y);
    }

    fn shape(&self) -> (f32, f32, f32) {
        let n = self.count.max(1.0);
        let (mx, my) = (self.sx / n, self.sy / n);
        let a = self.sxx / n - mx * mx;
        let c = self.syy / n - my * my;
        let b = self.sxy / n - mx * my;
        let mid = f32::midpoint(a, c);
        let diff = (((a - c) * 0.5).powi(2) + b * b).sqrt();
        let (major, minor) = ((mid + diff).max(0.0), (mid - diff).max(0.04));
        let angle = (0.5 * (2.0 * b).atan2(a - c)).to_degrees().abs();
        (
            (major / minor).sqrt(),
            4.0 * major.sqrt(),
            angle.min(180.0 - angle),
        )
    }

    fn touches(&self, r: Rect) -> bool {
        self.max_x >= r.x0 && self.min_x < r.x1 && self.max_y >= r.y0 && self.min_y < r.y1
    }

    fn inside(&self, r: Rect) -> bool {
        self.min_x >= r.x0 && self.max_x < r.x1 && self.min_y >= r.y0 && self.max_y < r.y1
    }
}

fn cigarette(p: &Plane) -> f32 {
    let zone = rect(8, 104, 76, SIDE);
    let s = p.stats(zone);
    let limit = (s.lum + 2.0 * s.std).max(170.0);
    let width = zone.x1.saturating_sub(zone.x0);
    let height = zone.y1.saturating_sub(zone.y0);
    let mut seen = vec![false; width.saturating_mul(height)];
    let index = |x: usize, y: usize| {
        y.saturating_sub(zone.y0)
            .saturating_mul(width)
            .saturating_add(x.saturating_sub(zone.x0))
    };
    let mouth = rect(30, 82, 82, 102);
    let teeth = rect(38, 74, 84, 102);
    let mut best = 0.0f32;
    let mut stack = Vec::new();
    for y0 in zone.y0..zone.y1 {
        for x0 in zone.x0..zone.x1 {
            if seen.get(index(x0, y0)).copied().unwrap_or(true) || p.at(x0, y0) < limit {
                continue;
            }
            let mut blob = Blob::new(x0, y0);
            stack.clear();
            stack.push((x0, y0));
            if let Some(s) = seen.get_mut(index(x0, y0)) {
                *s = true;
            }
            while let Some((x, y)) = stack.pop() {
                blob.add(x, y);
                let near = [
                    (x.checked_sub(1), Some(y)),
                    (x.checked_add(1), Some(y)),
                    (Some(x), y.checked_sub(1)),
                    (Some(x), y.checked_add(1)),
                ];
                for (nx, ny) in near {
                    let (Some(nx), Some(ny)) = (nx, ny) else {
                        continue;
                    };
                    if nx < zone.x0 || nx >= zone.x1 || ny < zone.y0 || ny >= zone.y1 {
                        continue;
                    }
                    let Some(flag) = seen.get_mut(index(nx, ny)) else {
                        continue;
                    };
                    if *flag || p.at(nx, ny) < limit {
                        continue;
                    }
                    *flag = true;
                    stack.push((nx, ny));
                }
            }
            #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
            let size = blob.count as usize;
            if !(MIN_BLOB..=MAX_BLOB).contains(&size) || !blob.touches(mouth) {
                continue;
            }
            let (aspect, length, angle) = blob.shape();
            if blob.inside(teeth) && angle < 25.0 {
                continue;
            }
            best = best.max(ramp(aspect, 3.0, 6.0) * ramp(length, 8.0, 16.0));
        }
    }
    best
}

#[must_use]
pub fn traits(face: &Gray<'_>) -> Traits {
    let plane = Plane {
        v: face.resample(SIDE),
    };
    Traits {
        glasses: glasses(&plane),
        beard: beard(&plane),
        fringe: fringe(&plane),
        cigarette: cigarette(&plane),
    }
}
