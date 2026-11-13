use crate::aec::{AecError, EchoCanceller, MAX_BLOCK};

fn noise(seed: u64, n: usize) -> Vec<f32> {
    let mut state = seed.wrapping_mul(6_364_136_223_846_793_005).wrapping_add(1);
    (0..n)
        .map(|_| {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            #[allow(clippy::cast_precision_loss)]
            let v = (state >> 40) as f32 / (1u64 << 24) as f32 - 0.5;
            v * 0.6
        })
        .collect()
}

fn echo_of(far: &[f32]) -> Vec<f32> {
    (0..far.len())
        .map(|i| {
            let a = i
                .checked_sub(120)
                .and_then(|k| far.get(k))
                .copied()
                .unwrap_or(0.0);
            let b = i
                .checked_sub(200)
                .and_then(|k| far.get(k))
                .copied()
                .unwrap_or(0.0);
            0.55 * a + 0.2 * b
        })
        .collect()
}

fn rms(v: &[f32]) -> f32 {
    #[allow(clippy::cast_precision_loss)]
    let n = v.len().max(1) as f32;
    (v.iter().map(|x| x * x).sum::<f32>() / n).sqrt()
}

fn run(aec: &mut EchoCanceller, near: &[f32], far: &[f32]) -> Vec<f32> {
    let mut out = Vec::new();
    for (n, f) in near.chunks(320).zip(far.chunks(320)) {
        out.extend(aec.process(n, f).unwrap_or_default());
    }
    out
}

#[test]
fn removes_playback_echo() {
    let far = noise(3, 16_000 * 6);
    let near = echo_of(&far);
    let mut aec = EchoCanceller::new();
    let out = run(&mut aec, &near, &far);
    let tail = 16_000 * 5;
    let before = rms(near.get(tail..).unwrap_or(&[]));
    let after = rms(out.get(tail..).unwrap_or(&[]));
    assert!(after < before * 0.1, "{after} vs {before}");
    assert!(aec.stats().converged);
}

#[test]
fn keeps_the_user_voice_during_playback() {
    let far = noise(5, 16_000 * 8);
    let mut near = echo_of(&far);
    let voice: Vec<f32> = (0..near.len())
        .map(|i| {
            #[allow(clippy::cast_precision_loss)]
            let t = i as f32 / 16_000.0;
            0.25 * (2.0 * std::f32::consts::PI * 220.0 * t).sin()
        })
        .collect();
    let warm = 16_000 * 3;
    for (n, v) in near.iter_mut().zip(voice.iter()).skip(warm) {
        *n += *v;
    }
    let mut aec = EchoCanceller::new();
    let out = run(&mut aec, &near, &far);
    let seg = 16_000 * 6..16_000 * 8;
    let kept = rms(out.get(seg.clone()).unwrap_or(&[]));
    let target = rms(voice.get(seg).unwrap_or(&[]));
    assert!(kept > target * 0.6, "{kept} vs {target}");
    assert!(kept < target * 1.5, "{kept} vs {target}");
}

#[test]
fn passes_through_without_playback() {
    let near = noise(9, 8000);
    let far = vec![0.0; 8000];
    let mut aec = EchoCanceller::new();
    let out = aec.process(&near, &far).unwrap_or_default();
    assert_eq!(out, near);
}

#[test]
fn rejects_bad_blocks() {
    let mut aec = EchoCanceller::new();
    assert_eq!(aec.process(&[0.0; 4], &[0.0; 5]), Err(AecError::Length));
    let big = vec![0.0; MAX_BLOCK + 1];
    assert_eq!(aec.process(&big, &big), Err(AecError::Block));
    let nan = [f32::NAN; 8];
    let out = aec.process(&nan, &nan).unwrap_or_default();
    assert!(out.iter().all(|v| v.is_finite()));
}
