use crate::cluster::ClusterEngine;
use crate::error::TernaryError;
use crate::graph::{EdgeType, MemoryGraph};
use crate::index::{TernaryIndex, TernaryRecord};
use crate::quantize::quantize_dense;
use crate::sleep::SleepConsolidator;
use crate::tier::{TierManager, TierState, TieredMemoryItem};
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
fn test_accumulator_and_moving_centroid() {
    let v1 = TernaryVector::from_trits(&[1, -1, 0, 1]).unwrap();
    let v2 = TernaryVector::from_trits(&[1, 0, 0, 1]).unwrap();
    let v3 = TernaryVector::from_trits(&[-1, 0, 0, 1]).unwrap();

    let mut accum = vec![0i32; 4];
    v1.accumulate_into(&mut accum).unwrap();
    v2.accumulate_into(&mut accum).unwrap();
    v3.accumulate_into(&mut accum).unwrap();

    assert_eq!(accum, vec![1, -1, 0, 3]);
    let centroid = TernaryVector::from_accum(&accum).unwrap();
    assert_eq!(centroid.to_trits(), vec![1, -1, 0, 1]);
}

#[test]
fn test_micro_cluster_and_engine() {
    let mut engine = ClusterEngine::new(4, 0.4, 10).unwrap();
    let v1 = TernaryVector::from_trits(&[1, 1, 1, 0]).unwrap();
    let v2 = TernaryVector::from_trits(&[1, 1, 0, 0]).unwrap();
    let v3 = TernaryVector::from_trits(&[-1, -1, -1, 0]).unwrap();

    let c1 = engine
        .ingest(
            "doc1".into(),
            v1.clone(),
            Some("proj1".into()),
            "arch".into(),
            1000,
        )
        .unwrap();
    let c2 = engine
        .ingest("doc2".into(), v2, Some("proj1".into()), "arch".into(), 1001)
        .unwrap();
    let c3 = engine
        .ingest("doc3".into(), v3, Some("proj1".into()), "arch".into(), 1002)
        .unwrap();

    assert_eq!(c1, c2);
    assert_ne!(c1, c3);
    assert_eq!(engine.clusters().len(), 2);

    let top = engine.search_centroids(&v1, 1).unwrap();
    assert_eq!(top.len(), 1);
    assert_eq!(top[0].0, c1);

    let synth = engine
        .synthesize(c1, "Architecture decision summary".into(), 2000)
        .unwrap();
    assert_eq!(synth.member_ids.len(), 2);
    assert_eq!(engine.synthesis_nodes().len(), 1);
}

#[test]
fn test_memory_graph_bfs_expansion() {
    let mut graph = MemoryGraph::new();
    graph.add_edge(
        "decision_2023".into(),
        "arch_2026".into(),
        EdgeType::Causal,
        0.9,
        100,
    );
    graph.add_edge(
        "arch_2026".into(),
        "impl_2026".into(),
        EdgeType::Dependency,
        0.8,
        110,
    );
    graph.add_edge(
        "impl_2026".into(),
        "bugfix_2026".into(),
        EdgeType::Precedes,
        0.5,
        120,
    );

    let expanded = graph.expand_context(&["decision_2023".into()], 2, 10);
    assert_eq!(
        expanded,
        vec![
            "decision_2023".to_string(),
            "arch_2026".to_string(),
            "impl_2026".to_string(),
        ]
    );
}

#[test]
fn test_tier_retention_and_ebbinghaus_decay() {
    let mut tier_mgr = TierManager::new(0.6, 0.2, 1.5).unwrap();
    let v = TernaryVector::from_trits(&[1, 0, -1, 0]).unwrap();

    tier_mgr.insert(TieredMemoryItem {
        id: "mem1".into(),
        tier: TierState::Hot,
        weight: 1.0,
        stability_base: 100.0,
        recall_count: 0,
        created_at_ms: 0,
        last_accessed_ms: 0,
        is_immune: false,
        project_id: Some("p1".into()),
        cluster_id: Some(1),
        payload: vec![1, 2, 3],
        vector: Some(v.clone()),
    });

    let r_init = tier_mgr.calculate_retention(tier_mgr.get("mem1").unwrap(), 0);
    assert!((r_init - 1.0).abs() < f32::EPSILON);

    let r_mid = tier_mgr.calculate_retention(tier_mgr.get("mem1").unwrap(), 70_000);
    assert!(r_mid < 0.6);

    let transitions = tier_mgr.evaluate_and_prune(70_000);
    assert_eq!(transitions.len(), 1);
    assert_eq!(transitions[0].2, TierState::Warm);

    let transitions_cold = tier_mgr.evaluate_and_prune(300_000);
    assert_eq!(transitions_cold.len(), 1);
    assert_eq!(transitions_cold[0].2, TierState::Cold);
    assert!(tier_mgr.get("mem1").unwrap().vector.is_none());

    tier_mgr.record_access("mem1", 310_000).unwrap();
    assert_eq!(tier_mgr.get("mem1").unwrap().tier, TierState::Warm);
    assert_eq!(tier_mgr.get("mem1").unwrap().recall_count, 1);

    tier_mgr.hydrate("mem1", v).unwrap();
    assert_eq!(tier_mgr.get("mem1").unwrap().tier, TierState::Hot);
    assert!(tier_mgr.get("mem1").unwrap().vector.is_some());
}

#[test]
fn test_sleep_consolidation_daemon() {
    let mut tier_mgr = TierManager::new(0.6, 0.2, 1.5).unwrap();
    let mut cluster_engine = ClusterEngine::new(4, 0.3, 10).unwrap();
    let mut graph = MemoryGraph::new();

    let v1 = TernaryVector::from_trits(&[1, 1, 0, 0]).unwrap();
    let v2 = TernaryVector::from_trits(&[1, 1, 0, 0]).unwrap();

    let c1 = cluster_engine
        .ingest("m1".into(), v1.clone(), Some("p".into()), "d".into(), 100)
        .unwrap();
    let _ = cluster_engine
        .ingest("m2".into(), v2.clone(), Some("p".into()), "d".into(), 101)
        .unwrap();

    tier_mgr.insert(TieredMemoryItem {
        id: "m1".into(),
        tier: TierState::Hot,
        weight: 1.0,
        stability_base: 50.0,
        recall_count: 0,
        created_at_ms: 100,
        last_accessed_ms: 100,
        is_immune: false,
        project_id: Some("p".into()),
        cluster_id: Some(c1),
        payload: vec![10],
        vector: Some(v1),
    });

    let daemon = SleepConsolidator::new(2);
    let report = daemon
        .consolidate(&mut tier_mgr, &mut cluster_engine, &mut graph, 60_000)
        .unwrap();

    assert_eq!(report.synthesized_count, 1);
    assert_eq!(report.demoted_to_warm, 1);
    assert_eq!(graph.edge_count(), 2);
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
