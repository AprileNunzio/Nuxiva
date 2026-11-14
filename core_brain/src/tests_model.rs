use std::path::PathBuf;

use crate::{
    BrainError, EMBEDDING_DIM, Embedder, Fbank, MELS, ModelSpec, OnnxEmbedder, SPEAKER_MODEL,
};

fn tone(freq: f32, seconds: f32, phase: f32) -> Vec<f32> {
    let n = (16_000.0 * seconds) as u32;
    (0..n)
        .map(|i| {
            let t = i as f32 / 16_000.0;
            0.3 * (std::f32::consts::TAU * freq * t + phase).sin()
                + 0.1 * (std::f32::consts::TAU * freq * 2.7 * t).sin()
        })
        .collect()
}

fn cosine(a: &[f32], b: &[f32]) -> f32 {
    let dot: f32 = a.iter().zip(b).map(|(x, y)| x * y).sum();
    let na: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let nb: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    dot / (na * nb)
}

#[test]
fn fbank_shape_and_validation() {
    let fb = Fbank::new();
    let feats = fb.compute(&tone(220.0, 1.0, 0.0)).expect("fbank");
    assert_eq!(feats.len() % MELS, 0);
    assert_eq!(feats.len() / MELS, (16_000 - 400) / 160 + 1);
    assert!(feats.iter().all(|v| v.is_finite()));
    assert_eq!(
        fb.compute(&tone(220.0, 0.1, 0.0)),
        Err(BrainError::Embedding("too_short"))
    );
    let mut bad = tone(220.0, 1.0, 0.0);
    bad[3] = f32::NAN;
    assert_eq!(fb.compute(&bad), Err(BrainError::Embedding("non_finite")));
}

#[test]
fn model_verification_rejects_tampering() {
    assert_eq!(
        SPEAKER_MODEL.verify(b"x"),
        Err(BrainError::Embedding("model_size"))
    );
    let spec = ModelSpec {
        file: "m.onnx",
        url: "https://example.invalid/m",
        sha256: SPEAKER_MODEL.sha256,
        bytes: 4,
    };
    assert_eq!(
        spec.verify(b"abcd"),
        Err(BrainError::Embedding("model_hash"))
    );
    let good = ModelSpec {
        sha256: "88d4266fd4e6338d13b845fcf289579d209c897823b9217da3e161936f031589",
        ..spec
    };
    assert_eq!(good.verify(b"abcd"), Ok(()));
}

#[tokio::test]
async fn model_missing_is_explicit_error() {
    let dir = std::env::temp_dir().join("core_brain_no_model_dir");
    assert_eq!(
        SPEAKER_MODEL.load(&dir).await,
        Err(BrainError::Embedding("model_missing"))
    );
    let plain = ModelSpec {
        url: "http://insecure.invalid/m",
        ..SPEAKER_MODEL
    };
    assert_eq!(
        plain.fetch(&dir).await,
        Err(BrainError::Embedding("model_url"))
    );
}

#[tokio::test]
async fn real_model_embeds_when_available() {
    let Some(dir) = std::env::var_os("NUXIVA_TEST_MODEL_DIR").map(PathBuf::from) else {
        return;
    };
    let data = SPEAKER_MODEL.load(&dir).await.expect("model");
    let embedder = OnnxEmbedder::from_verified(&SPEAKER_MODEL, &data).expect("load");
    let a = embedder.embed(&tone(180.0, 2.0, 0.0)).expect("a");
    let a2 = embedder.embed(&tone(180.0, 2.0, 0.0)).expect("a2");
    let a3 = embedder.embed(&tone(180.0, 2.0, 1.1)).expect("a3");
    let b = embedder.embed(&tone(950.0, 2.0, 0.0)).expect("b");
    assert_eq!(a.len(), EMBEDDING_DIM);
    assert_eq!(a, a2);
    assert!(cosine(&a, &a3) > cosine(&a, &b));
}
