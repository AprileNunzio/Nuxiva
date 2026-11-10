#![allow(
    clippy::unwrap_used,
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::many_single_char_names,
    clippy::arithmetic_side_effects,
    clippy::cast_precision_loss,
    clippy::approx_constant
)]

use crate::{
    GAIT_DIM, GaitError, GaitMatch, GaitObservation, GaitSignature, ReferenceGait, evaluate_match,
    extract_signature, find_best_match,
};

fn generate_synthetic_walk(samples: usize, duration_ms: u64) -> Vec<GaitObservation> {
    let mut list = Vec::with_capacity(samples);
    let dt = duration_ms / (samples as u64);
    for i in 0..samples {
        let t = (i as u64) * dt;
        let progress = (i as f32) / (samples as f32);
        let x = 100.0 + progress * 200.0 + (progress * 12.56).sin() * 5.0;
        let y = 150.0 + (progress * 12.56).cos() * 8.0;
        let w = 45.0 + (progress * 6.28).sin() * 2.0;
        let h = 175.0;
        list.push(GaitObservation::new(t, x, y, w, h));
    }
    list
}

#[test]
fn test_extraction_success() {
    let obs = generate_synthetic_walk(20, 2000);
    let sig = extract_signature(&obs).unwrap();
    assert_eq!(sig.samples, 20);
    assert_eq!(sig.features.len(), GAIT_DIM);
    assert!(sig.confidence >= 0.4);
    assert!(sig.features[0] > 0.0);
}

#[test]
fn test_insufficient_samples() {
    let obs = generate_synthetic_walk(3, 1000);
    let res = extract_signature(&obs);
    assert_eq!(res, Err(GaitError::InsufficientSamples));
}

#[test]
fn test_insufficient_duration() {
    let obs = generate_synthetic_walk(10, 200);
    let res = extract_signature(&obs);
    assert_eq!(res, Err(GaitError::InsufficientDuration));
}

#[test]
fn test_invalid_bbox() {
    let mut obs = generate_synthetic_walk(10, 1000);
    obs[0].width = -5.0;
    let res = extract_signature(&obs);
    assert_eq!(res, Err(GaitError::InvalidBoundingBox));
}

#[test]
fn test_signature_validation() {
    let valid = vec![0.5_f32; 16];
    let sig = GaitSignature::from_slice(&valid, 10, 0.8).unwrap();
    assert_eq!(sig.to_vec(), valid);

    let invalid_len = vec![0.5_f32; 15];
    assert_eq!(
        GaitSignature::from_slice(&invalid_len, 10, 0.8),
        Err(GaitError::InvalidSignatureLength)
    );

    let nan_vec = vec![f32::NAN; 16];
    assert_eq!(
        GaitSignature::from_slice(&nan_vec, 10, 0.8),
        Err(GaitError::InvalidSignatureValue)
    );
}

#[test]
fn test_match_evaluation_high_similarity() {
    let obs_a = generate_synthetic_walk(20, 2000);
    let sig_a = extract_signature(&obs_a).unwrap();
    let obs_b = generate_synthetic_walk(20, 2000);
    let sig_b = extract_signature(&obs_b).unwrap();
    let res: GaitMatch = evaluate_match(&sig_a, &sig_b, Some("sight-1"), Some(1_700_000_000_000));
    assert!(res.similarity >= 0.90);
    assert!(res.probable_match);
    assert!(!res.is_biometric_conclusive);
    assert!(res.narrative_it.contains("probabilmente la stessa persona"));
    assert!(res.narrative_en.contains("likely the same person"));
}

#[test]
fn test_match_evaluation_low_similarity() {
    let sig_a = GaitSignature::from_slice(&[0.1; 16], 10, 0.8).unwrap();
    let sig_b = GaitSignature::from_slice(&[0.9; 16], 10, 0.8).unwrap();
    let res = evaluate_match(&sig_a, &sig_b, None, None);
    assert!(!res.probable_match);
    assert!(!res.is_biometric_conclusive);
    assert!(res.narrative_it.contains("non corrispondente"));
}

#[test]
fn test_find_best_match() {
    let sig = GaitSignature::from_slice(&[0.5; 16], 10, 0.8).unwrap();
    let refs = vec![
        ReferenceGait {
            id: "ref-1".to_owned(),
            timestamp_ms: 1000,
            signature: GaitSignature::from_slice(&[0.1; 16], 10, 0.8).unwrap(),
        },
        ReferenceGait {
            id: "ref-2".to_owned(),
            timestamp_ms: 2000,
            signature: GaitSignature::from_slice(&[0.49; 16], 10, 0.8).unwrap(),
        },
    ];
    let best = find_best_match(&sig, &refs).unwrap();
    assert_eq!(best.reference_id, Some("ref-2".to_owned()));
    assert!(best.probable_match);
}

#[test]
fn test_aggregation() {
    let s1 = GaitSignature::from_slice(&[0.2; 16], 5, 0.6).unwrap();
    let s2 = GaitSignature::from_slice(&[0.4; 16], 5, 0.8).unwrap();
    let agg = GaitSignature::aggregate(&[s1, s2]).unwrap();
    assert_eq!(agg.samples, 10);
    assert!((agg.features[0] - 0.3).abs() < 1e-5);
    assert!((agg.confidence - 0.7).abs() < 1e-5);
}
