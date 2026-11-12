#![allow(
    clippy::many_single_char_names,
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    clippy::useless_vec
)]

use crate::danger_sound::{DangerKind, DangerSound};
use crate::distress::{Answer, Cue, analyze};

const RATE: f32 = 16_000.0;

struct Noise(u64);

impl Noise {
    fn next(&mut self) -> f32 {
        self.0 = self
            .0
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
        #[allow(clippy::cast_precision_loss)]
        let v = (self.0 >> 40) as f32 / (1u64 << 24) as f32;
        v * 2.0 - 1.0
    }
}

#[allow(clippy::cast_precision_loss)]
fn tone(
    seconds: f32,
    f0: f32,
    harmonics: &[f32],
    amp: f32,
    vibrato: f32,
    noise: &mut Noise,
) -> Vec<f32> {
    let n = (seconds * RATE) as usize;
    let mut phase = 0.0_f32;
    (0..n)
        .map(|i| {
            let t = i as f32 / RATE;
            let f = f0 * (1.0 + vibrato * (2.0 * std::f32::consts::PI * 6.0 * t).sin());
            phase += 2.0 * std::f32::consts::PI * f / RATE;
            let mut v = (phase).sin();
            for (h, a) in harmonics.iter().enumerate() {
                let m = h as f32 + 2.0;
                v += a * (phase * m).sin();
            }
            v * amp + noise.next() * 0.002
        })
        .collect()
}

#[allow(clippy::cast_precision_loss)]
fn quiet(seconds: f32, noise: &mut Noise) -> Vec<f32> {
    (0..(seconds * RATE) as usize)
        .map(|_| noise.next() * 0.002)
        .collect()
}

fn run(chunks: &[Vec<f32>], media: bool) -> Vec<DangerKind> {
    let mut d = DangerSound::new();
    let mut out = Vec::new();
    for c in chunks {
        out.extend(d.feed(c, media).into_iter().map(|e| e.kind));
    }
    out
}

#[test]
fn scream_is_heard() {
    let mut n = Noise(1);
    let chunks = vec![
        quiet(1.5, &mut n),
        tone(0.9, 1100.0, &[0.6, 0.4], 0.3, 0.03, &mut n),
        quiet(1.0, &mut n),
    ];
    assert!(run(&chunks, false).contains(&DangerKind::Scream));
}

#[test]
fn calm_speech_is_not_a_scream() {
    let mut n = Noise(2);
    let chunks = vec![
        quiet(1.5, &mut n),
        tone(2.0, 140.0, &[0.5, 0.33, 0.25, 0.2], 0.05, 0.02, &mut n),
        quiet(1.0, &mut n),
    ];
    assert!(!run(&chunks, false).contains(&DangerKind::Scream));
}

#[test]
fn short_shout_and_noise_are_ignored() {
    let mut n = Noise(3);
    let shout = vec![
        quiet(1.5, &mut n),
        tone(0.15, 1100.0, &[0.6], 0.3, 0.03, &mut n),
        quiet(1.0, &mut n),
    ];
    assert!(run(&shout, false).is_empty());
    let loud: Vec<f32> = (0..16_000).map(|_| n.next() * 0.4).collect();
    assert!(
        !run(&[quiet(1.5, &mut n), loud, quiet(1.0, &mut n)], false).contains(&DangerKind::Scream)
    );
}

fn t3(noise: &mut Noise, groups: usize, beeps: usize) -> Vec<Vec<f32>> {
    let mut chunks = vec![quiet(1.5, noise)];
    for _ in 0..groups {
        for _ in 0..beeps {
            chunks.push(tone(0.5, 3200.0, &[], 0.2, 0.0, noise));
            chunks.push(quiet(0.5, noise));
        }
        chunks.push(quiet(1.2, noise));
    }
    chunks
}

#[test]
fn smoke_alarm_pattern_is_recognised() {
    let mut n = Noise(4);
    let found = run(&t3(&mut n, 2, 3), false);
    assert_eq!(
        found
            .iter()
            .filter(|k| **k == DangerKind::SmokeAlarm)
            .count(),
        2
    );
    assert!(!found.contains(&DangerKind::Scream));
}

#[test]
fn co_alarm_pattern_is_recognised() {
    let mut n = Noise(5);
    assert!(run(&t3(&mut n, 1, 4), false).contains(&DangerKind::CoAlarm));
}

#[test]
fn a_single_beep_is_not_an_alarm() {
    let mut n = Noise(6);
    assert!(run(&t3(&mut n, 1, 1), false).is_empty());
}

#[test]
fn media_lowers_scream_probability() {
    let mut n = Noise(7);
    let chunks = vec![
        quiet(1.5, &mut n),
        tone(0.9, 1100.0, &[0.6, 0.4], 0.3, 0.03, &mut n),
        quiet(1.0, &mut n),
    ];
    let p = |media| {
        let mut d = DangerSound::new();
        chunks
            .iter()
            .flat_map(|c| d.feed(c, media))
            .map(|e| e.probability)
            .fold(0.0, f64::max)
    };
    assert!(p(true) < p(false));
}

#[test]
fn hostile_input_is_safe() {
    let mut d = DangerSound::new();
    assert!(
        d.feed(&[f32::NAN, f32::INFINITY, -9.0, 9.0], false)
            .is_empty()
    );
    assert!(d.feed(&vec![0.0; 16_000 * 40], false).is_empty());
}

#[test]
fn help_words_in_all_languages() {
    for text in [
        "Aiuto!",
        "help me",
        "Au secours",
        "¡Socorro!",
        "chiamate il 118",
        "Non riesco ad alzarmi",
        "I can't breathe",
    ] {
        let d = analyze(text, false, false, 0.9);
        assert!(d.help > 0.7, "{text}: {}", d.help);
        assert_eq!(d.answer, Some(Answer::NotOk), "{text}");
    }
}

#[test]
fn negation_and_tasks_lower_the_alarm() {
    assert!(analyze("non ho bisogno di aiuto", false, false, 0.9).help < 0.05);
    assert!(analyze("I don't need help", false, false, 0.9).help < 0.05);
    assert!(analyze("non chiamate l'ambulanza", false, false, 0.9).help < 0.05);
    assert!(analyze("aiutami a scrivere una mail", false, false, 0.9).help < 0.3);
    assert!(analyze("help me with the recipe", false, false, 0.9).help < 0.3);
}

#[test]
fn films_and_translations_count_less() {
    let real = analyze("aiuto", false, false, 0.9).help;
    assert!(analyze("nel film gridava aiuto", false, false, 0.9).help < real * 0.5);
    assert!(analyze("come si dice aiuto in inglese", false, false, 0.9).help < real * 0.5);
}

#[test]
fn answers_to_are_you_ok() {
    assert_eq!(
        analyze("sì sto bene", true, false, 0.9).answer,
        Some(Answer::Ok)
    );
    assert_eq!(
        analyze("no, sto bene", true, false, 0.9).answer,
        Some(Answer::Ok)
    );
    assert_eq!(
        analyze("non sto bene", true, false, 0.9).answer,
        Some(Answer::NotOk)
    );
    assert_eq!(
        analyze("I'm fine", true, false, 0.9).answer,
        Some(Answer::Ok)
    );
    assert_eq!(analyze("no", true, false, 0.9).answer, Some(Answer::NotOk));
    assert_eq!(analyze("sì", true, false, 0.9).answer, Some(Answer::Ok));
    assert_eq!(analyze("sì", false, false, 0.9).answer, None);
    assert_eq!(
        analyze("falso allarme", false, false, 0.9).answer,
        Some(Answer::Ok)
    );
}

#[test]
fn threats_and_fire_are_separate() {
    let d = analyze("lasciami, mi fai male!", false, false, 0.9);
    assert!(d.threat > 0.8 && d.help < 0.05);
    assert!(analyze("al fuoco! c'è fumo", false, false, 0.9).fire > 0.9);
    assert!(d.detections.iter().all(|x| x.cue == Cue::Threat));
}

#[test]
fn media_and_confidence_are_bounded() {
    assert!((analyze("aiuto", false, true, 0.9).confidence - 0.45).abs() < 1e-9);
    assert!(analyze("aiuto", false, false, f64::NAN).confidence.abs() < 1e-12);
    let long = "aiuto ".repeat(5000);
    assert!(analyze(&long, false, false, 0.9).detections.len() <= crate::distress::MAX_WORDS);
    assert!(analyze("", true, false, 0.9).answer.is_none());
}
