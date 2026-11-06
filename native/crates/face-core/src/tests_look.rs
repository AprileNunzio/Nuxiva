#![allow(
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    clippy::float_cmp,
    clippy::struct_excessive_bools,
    clippy::many_single_char_names,
    clippy::manual_range_contains
)]

use crate::{Gray, LookMemory, LookSample, traits};

#[derive(Default, Clone, Copy)]
struct Wear {
    glasses: bool,
    beard: bool,
    fringe: bool,
    cigarette: bool,
}

struct Rng(u64);

impl Rng {
    fn next(&mut self) -> f32 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        (self.0 % 20_000) as f32 / 10_000.0 - 1.0
    }
}

fn near_segment(x: f32, y: f32, a: (f32, f32), b: (f32, f32)) -> f32 {
    let (dx, dy) = (b.0 - a.0, b.1 - a.1);
    let t = (((x - a.0) * dx + (y - a.1) * dy) / (dx * dx + dy * dy)).clamp(0.0, 1.0);
    ((x - a.0 - t * dx).powi(2) + (y - a.1 - t * dy).powi(2)).sqrt()
}

fn face(seed: u64, wear: Wear) -> Vec<u8> {
    let mut rng = Rng(seed.wrapping_mul(7919).wrapping_add(17));
    let mut img = vec![0_u8; 112 * 112];
    for y in 0..112_usize {
        for x in 0..112_usize {
            let (fx, fy) = (x as f32, y as f32);
            let mut v = 150.0 + rng.next() * 6.0;
            for ex in [38.0, 74.0] {
                if ((fx - ex) / 8.0).powi(2) + ((fy - 52.0) / 4.0).powi(2) < 1.0 {
                    v = 60.0;
                }
                if (fy - 38.0).abs() < 2.0 && (fx - ex).abs() < 10.0 {
                    v = 90.0;
                }
            }
            if (fy - 92.0).abs() < 2.0 && (42.0..70.0).contains(&fx) {
                v = 100.0;
            }
            if wear.fringe && fy < 24.0 {
                v = 70.0 + rng.next() * 40.0;
            }
            let lower = (fy >= 100.0 && (36.0..76.0).contains(&fx))
                || (fy >= 82.0 && (fx < 34.0 || fx >= 78.0));
            if wear.beard && lower {
                v = 75.0 + rng.next() * 40.0;
            }
            if wear.glasses {
                for ex in [38.0f32, 74.0] {
                    let r = ((fx - ex).powi(2) + ((fy - 54.0) * 1.3).powi(2)).sqrt();
                    if (r - 13.0).abs() < 1.5 {
                        v = 30.0;
                    }
                }
                if (47.0..50.0).contains(&fy) && (50.0..62.0).contains(&fx) {
                    v = 30.0;
                }
                if (46.0..50.0).contains(&fy) && (fx < 25.0 || fx > 87.0) {
                    v = 30.0;
                }
            }
            if wear.cigarette && near_segment(fx, fy, (68.0, 93.0), (98.0, 106.0)) < 1.6 {
                v = 248.0;
            }
            img[y * 112 + x] = v.clamp(0.0, 255.0) as u8;
        }
    }
    img
}

fn read(wear: Wear, seed: u64) -> crate::Traits {
    let img = face(seed, wear);
    traits(&Gray::new(&img, 112, 112).unwrap_or_else(|_| unreachable!()))
}

#[test]
fn glasses_beard_fringe_and_cigarette_are_seen() {
    let plain = read(Wear::default(), 1);
    assert!(plain.glasses < 0.4, "{plain:?}");
    assert!(plain.beard < 0.4, "{plain:?}");
    assert!(plain.fringe < 0.4, "{plain:?}");
    assert!(plain.cigarette < 0.3, "{plain:?}");
    let g = read(
        Wear {
            glasses: true,
            ..Wear::default()
        },
        2,
    );
    assert!(g.glasses > 0.7 && g.beard < 0.4, "{g:?}");
    let b = read(
        Wear {
            beard: true,
            ..Wear::default()
        },
        3,
    );
    assert!(b.beard > 0.6 && b.glasses < 0.4, "{b:?}");
    let f = read(
        Wear {
            fringe: true,
            ..Wear::default()
        },
        4,
    );
    assert!(f.fringe > 0.6 && f.beard < 0.4, "{f:?}");
    let c = read(
        Wear {
            cigarette: true,
            ..Wear::default()
        },
        5,
    );
    assert!(c.cigarette > 0.6, "{c:?}");
}

fn sample(glasses: f32, cigarette: f32, hair: &str) -> LookSample {
    LookSample {
        glasses,
        beard: 0.1,
        fringe: 0.1,
        cigarette,
        hair: Some(hair.to_owned()),
        samples: 8,
    }
}

#[test]
fn glasses_need_a_steady_streak_and_survive_a_roundtrip() {
    let mut m = LookMemory::new();
    let mut events = Vec::new();
    for i in 0..5 {
        events.extend(m.update(&sample(0.95, 0.0, "brown"), f64::from(i)));
    }
    assert!(events.iter().all(|e| e.kind != "glasses"));
    for i in 5..20 {
        events.extend(m.update(&sample(0.95, 0.0, "brown"), f64::from(i)));
    }
    let on: Vec<_> = events.iter().filter(|e| e.kind == "glasses").collect();
    assert_eq!(on.len(), 1);
    assert_eq!(on[0].value, "on");
    assert!(
        events
            .iter()
            .any(|e| e.kind == "hair_color" && e.value == "brown")
    );
    let text = m.to_json().unwrap_or_default();
    let mut back = LookMemory::from_json(&text).unwrap_or_default();
    assert_eq!(back, m);
    assert!(back.update(&sample(0.2, 0.0, "brown"), 21.0).is_empty());
    let mut off = Vec::new();
    for i in 22..40 {
        off.extend(back.update(&sample(0.0, 0.0, "brown"), f64::from(i)));
    }
    assert!(off.iter().any(|e| e.kind == "glasses" && e.value == "off"));
    assert!(back.summary().hair.as_deref() == Some("brown") && !back.summary().glasses);
}

#[test]
fn hair_change_and_smoking_episodes_are_learned() {
    let mut m = LookMemory::new();
    for i in 0..12 {
        m.update(&sample(0.0, 0.0, "brown"), f64::from(i));
    }
    let mut events = Vec::new();
    for i in 12..40 {
        events.extend(m.update(&sample(0.0, 0.0, "red"), f64::from(i)));
    }
    let change = events.iter().find(|e| e.kind == "hair_color");
    assert_eq!(
        change.map(|e| (e.value.as_str(), e.previous.as_deref())),
        Some(("red", Some("brown")))
    );
    let mut smoke = Vec::new();
    for t in [100.0, 110.0, 120.0, 900.0, 910.0] {
        smoke.extend(m.update(&sample(0.0, 0.8, "red"), t));
    }
    let kinds: Vec<&str> = smoke.iter().map(|e| e.kind).collect();
    assert_eq!(kinds, vec!["smoking", "smoking", "smoker"]);
    assert!(m.summary().smoker && m.summary().smoking_episodes == 2);
    assert!(m.forget("smoker").is_ok() && !m.summary().smoker);
    assert!(m.forget("tattoo").is_err());
}

#[test]
fn bad_state_and_samples_are_rejected() {
    assert!(LookMemory::from_json("{not json").is_err());
    assert!(LookMemory::from_json(&"x".repeat(70_000)).is_err());
    assert_eq!(
        LookMemory::from_json("").unwrap_or_default(),
        LookMemory::new()
    );
    let forged = r#"{"version":9,"glasses":{"ema":0.1,"on":false,"streak":0,"seen":1,"since":0.0},"beard":{"ema":0,"on":false,"streak":0,"seen":0,"since":0},"fringe":{"ema":0,"on":false,"streak":0,"seen":0,"since":0},"hair":{"recent":["<script>","brown"],"stable":"<b>","since":0},"smoke":{"episodes":0,"hits":0,"open":false,"last":0,"smoker":false}}"#;
    let m = LookMemory::from_json(forged).unwrap_or_default();
    assert_eq!(m.hair.recent.len(), 1);
    assert_eq!(m.hair.stable, None);
    let mut fresh = LookMemory::new();
    let few = LookSample {
        samples: 2,
        ..sample(1.0, 1.0, "brown")
    };
    assert!(fresh.update(&few, 1.0).is_empty());
    let nan = LookSample {
        glasses: f32::NAN,
        ..sample(0.0, 0.0, "plaid")
    };
    fresh.update(&nan, 2.0);
    assert_eq!(fresh.glasses.seen, 0);
    assert!(fresh.hair.recent.is_empty());
}
