use crate::align::{ALIGN_WINDOW, Aligner, correlation};
use crate::array::{ArrayError, MicArray, pick_best};

const FRAME: usize = 480;

struct Lcg(u64);

impl Lcg {
    fn next(&mut self) -> f32 {
        self.0 = self
            .0
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
        #[allow(clippy::cast_precision_loss)]
        let unit = (self.0 >> 40) as f32 / (1_u64 << 24) as f32;
        unit * 2.0 - 1.0
    }
}

fn voice(n: usize, seed: u64) -> Vec<f32> {
    let mut rng = Lcg(seed);
    let mut state = 0.0_f32;
    (0..n)
        .map(|i| {
            #[allow(clippy::cast_precision_loss)]
            let t = i as f32 / 16_000.0;
            let envelope = (t * 3.0 * std::f32::consts::TAU).sin().max(0.0);
            state = state * 0.6 + rng.next() * 0.4;
            let tone = (t * 180.0 * std::f32::consts::TAU).sin()
                + 0.5 * (t * 360.0 * std::f32::consts::TAU).sin();
            0.2 * envelope * (tone * 0.6 + state)
        })
        .collect()
}

fn noise(n: usize, seed: u64, gain: f32) -> Vec<f32> {
    let mut rng = Lcg(seed);
    (0..n).map(|_| rng.next() * gain).collect()
}

fn delayed(signal: &[f32], lag: usize) -> Vec<f32> {
    std::iter::repeat_n(0.0, lag)
        .chain(signal.iter().copied())
        .take(signal.len())
        .collect()
}

fn add(a: &[f32], b: &[f32]) -> Vec<f32> {
    a.iter().zip(b).map(|(x, y)| x + y).collect()
}

fn snr(clean: &[f32], mixed: &[f32]) -> f32 {
    let signal: f32 = clean.iter().map(|v| v * v).sum();
    let err: f32 = clean
        .iter()
        .zip(mixed)
        .map(|(c, m)| (m - c) * (m - c))
        .sum();
    10.0 * (signal / err.max(1e-12)).log10()
}

fn run(array: &mut MicArray, inputs: &[Vec<f32>]) -> (Vec<f32>, Vec<usize>, Vec<usize>) {
    let mut out = Vec::new();
    let mut bests = Vec::new();
    let mut fused = Vec::new();
    let split: Vec<Vec<&[f32]>> = inputs
        .iter()
        .map(|c| c.chunks_exact(FRAME).collect())
        .collect();
    let count = split.first().map_or(0, Vec::len);
    for index in 0..count {
        let frames: Vec<&[f32]> = split
            .iter()
            .map(|c| c.get(index).copied().unwrap_or(&[]))
            .collect();
        if let Ok(frame) = array.mix(&frames) {
            out.extend(frame.samples);
            bests.push(frame.best);
            fused.push(frame.fused);
        }
    }
    (out, bests, fused)
}

#[test]
fn the_cleaner_microphone_wins() {
    let n = 16_000 * 4;
    let speech = voice(n, 1);
    let far = add(
        &speech.iter().map(|v| v * 0.3).collect::<Vec<_>>(),
        &noise(n, 2, 0.05),
    );
    let near = add(&speech, &noise(n, 3, 0.01));
    let Ok(mut array) = MicArray::new(2) else {
        unreachable!()
    };
    let (_, bests, _) = run(&mut array, &[far, near]);
    assert_eq!(bests.last().copied(), Some(1));
}

#[test]
fn a_dead_microphone_is_left_out() {
    let n = 16_000 * 3;
    let speech = add(&voice(n, 4), &noise(n, 5, 0.01));
    let Ok(mut array) = MicArray::new(2) else {
        unreachable!()
    };
    let (_, bests, _) = run(&mut array, &[vec![0.0; n], speech]);
    assert_eq!(bests.last().copied(), Some(1));
}

#[test]
fn the_aligner_finds_the_delay() {
    let speech = voice(ALIGN_WINDOW, 6);
    let late = delayed(&speech, 300);
    let mut aligner = Aligner::new();
    let found = aligner.estimate(&speech, &late);
    assert_eq!(found.map(|a| a.lag), Some(300));
    assert!(found.is_some_and(|a| a.coherence > 0.9));
    let early = aligner.estimate(&late, &speech);
    assert_eq!(early.map(|a| a.lag), Some(-300));
    assert!(correlation(&speech, &late, 300) > 0.9);
}

#[test]
fn two_microphones_hearing_the_same_voice_are_fused_for_a_cleaner_signal() {
    let n = 16_000 * 5;
    let speech = voice(n, 7);
    let a = add(&speech, &noise(n, 8, 0.04));
    let b = add(&delayed(&speech, 200), &noise(n, 9, 0.04));
    let Ok(mut array) = MicArray::new(2) else {
        unreachable!()
    };
    let (out, _, fused) = run(&mut array, &[a.clone(), b]);
    assert_eq!(fused.last().copied(), Some(2));
    let tail = 16_000 * 2;
    let lag = crate::align::MAX_LAG;
    let end = out.len() - lag;
    let reference: Vec<f32> = speech.get(end - tail..end).unwrap_or(&[]).to_vec();
    let single: Vec<f32> = a.get(end - tail..end).unwrap_or(&[]).to_vec();
    let mixed: Vec<f32> = out.get(out.len() - tail..).unwrap_or(&[]).to_vec();
    assert!(snr(&reference, &mixed) > snr(&reference, &single) + 1.5);
}

#[test]
fn switching_needs_a_clear_and_lasting_lead() {
    let mut streak = (0, 0);
    assert_eq!(pick_best(&[10.0, 11.0], 0, &mut streak), 0);
    for _ in 0..20 {
        assert_eq!(pick_best(&[10.0, 12.0], 0, &mut streak), 0);
    }
    let mut picked = 0;
    for _ in 0..10 {
        picked = pick_best(&[10.0, 14.0], 0, &mut streak);
    }
    assert_eq!(picked, 1);
}

#[test]
fn malformed_input_is_rejected() {
    assert_eq!(MicArray::new(0).err(), Some(ArrayError::ChannelCount));
    assert_eq!(MicArray::new(9).err(), Some(ArrayError::ChannelCount));
    let Ok(mut array) = MicArray::new(2) else {
        unreachable!()
    };
    let a = vec![0.0; FRAME];
    let b = vec![0.0; FRAME - 1];
    assert_eq!(array.mix(&[&a]).err(), Some(ArrayError::ChannelCount));
    assert_eq!(array.mix(&[&a, &b]).err(), Some(ArrayError::FrameLength));
}
