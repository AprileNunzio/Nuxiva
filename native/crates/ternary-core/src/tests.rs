use crate::error::TernaryError;
use crate::index::{TernaryIndex, TernaryRecord};
use crate::quantize::quantize_dense;
use crate::vector::TernaryVector;

#[test]
fn test_packing_and_dot_product() {
    let trits_a: [i8; 4] = [1, -1, 0, 1];
    let trits_b: [i8; 4] = [1, 1, 0, -1];
    let vec_a = TernaryVector::from_trits(&trits_a).unwrap();
    let vec_b = TernaryVector::from_trits(&trits_b).unwrap();

    let dot = vec_a.dot(&vec_b).unwrap();
    assert_eq!(dot, -1);
}

#[test]
fn test_identical_vectors_dot_product() {
    let trits: [i8; 6] = [1, -1, 0, 1, 0, -1];
    let vec = TernaryVector::from_trits(&trits).unwrap();
    assert_eq!(vec.active_dimensions(), 4);

    let dot = vec.dot(&vec).unwrap();
    assert_eq!(dot, 4);

    let cosine = vec.cosine_similarity(&vec).unwrap();
    assert!((cosine - 1.0).abs() < f32::EPSILON);
}

#[test]
fn test_disjoint_invariant_validation() {
    let invalid = TernaryVector::from_raw(64, vec![0b0011], vec![0b0010]);
    assert_eq!(invalid, Err(TernaryError::OverlappingMasks { index: 0 }));

    let valid = TernaryVector::from_raw(64, vec![0b0001], vec![0b0010]);
    assert!(valid.is_ok());
}

#[test]
fn test_quantize_dense_floats() {
    let dense = [10.0f32, -9.0, 0.05, -0.02, 8.5];
    let vec = quantize_dense(&dense, 0.5).unwrap();
    let trits = vec.to_trits();
    assert_eq!(trits, vec![1, -1, 0, 0, 1]);
}

#[test]
fn test_index_search_top_k() {
    let mut index = TernaryIndex::new(4).unwrap();
    let v1 = TernaryVector::from_trits(&[1, 1, 1, 1]).unwrap();
    let v2 = TernaryVector::from_trits(&[1, 1, 1, -1]).unwrap();
    let v3 = TernaryVector::from_trits(&[-1, -1, -1, -1]).unwrap();

    index
        .add(TernaryRecord {
            id: "rec_1".into(),
            vector: v1.clone(),
            project_id: Some("proj_alpha".into()),
            timestamp_ms: 100,
        })
        .unwrap();
    index
        .add(TernaryRecord {
            id: "rec_2".into(),
            vector: v2,
            project_id: Some("proj_alpha".into()),
            timestamp_ms: 101,
        })
        .unwrap();
    index
        .add(TernaryRecord {
            id: "rec_3".into(),
            vector: v3,
            project_id: Some("proj_beta".into()),
            timestamp_ms: 102,
        })
        .unwrap();

    let results = index.search_top_k(&v1, 2).unwrap();
    assert_eq!(results.len(), 2);
    assert_eq!(results[0].0, "rec_1");
    assert_eq!(results[0].1, 4);
    assert_eq!(results[1].0, "rec_2");
    assert_eq!(results[1].1, 2);

    let filtered = index.filter_by_project("proj_alpha");
    assert_eq!(filtered.len(), 2);
}

#[test]
fn test_high_dimension_benchmark() {
    let mut trits_q = vec![0i8; 1024];
    for (i, t) in trits_q.iter_mut().enumerate() {
        if i % 3 == 0 {
            *t = 1;
        } else if i % 3 == 1 {
            *t = -1;
        }
    }
    let query = TernaryVector::from_trits(&trits_q).unwrap();

    let mut index = TernaryIndex::new(1024).unwrap();
    for i in 0..1000 {
        let mut trits = vec![0i8; 1024];
        for (j, t) in trits.iter_mut().enumerate() {
            if (i + j) % 3 == 0 {
                *t = 1;
            } else if (i + j) % 3 == 1 {
                *t = -1;
            }
        }
        let vector = TernaryVector::from_trits(&trits).unwrap();
        index
            .add(TernaryRecord {
                id: format!("doc_{i}"),
                vector,
                project_id: None,
                timestamp_ms: 1000 + i as u64,
            })
            .unwrap();
    }

    let top = index.search_top_k(&query, 10).unwrap();
    assert_eq!(top.len(), 10);
    assert!(top[0].1 > 0);
}
