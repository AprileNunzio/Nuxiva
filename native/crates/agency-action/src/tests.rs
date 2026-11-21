use std::collections::BTreeMap;

use agency_domain::Proof;

use crate::{
    ActionError, ActionItem, ActionKind, ReplacementChunk, StagedEdit, WorkspaceCoordinator,
    apply_surgical_patches, evaluate_gate, plan_parallel_batch, view_line_range,
};

#[test]
fn view_line_range_returns_1_indexed_slice() {
    let text = "fn a() {}\nfn b() {}\nfn c() {}\nfn d() {}\n";
    let res = view_line_range(text, 2, 3);
    assert!(res.is_ok());
    if let Ok(view) = res {
        assert_eq!(view.start_line, 2);
        assert_eq!(view.end_line, 3);
        assert_eq!(view.total_lines, 4);
        assert_eq!(view.content, "2: fn b() {}\n3: fn c() {}");
    }
}

#[test]
fn surgical_patch_replaces_multiple_non_overlapping_chunks() {
    let original = "line 1\nlet price = 10;\nline 3\nlet tax = 2;\nline 5\n";
    let chunks = vec![
        ReplacementChunk {
            start_line: 2,
            end_line: 2,
            target_content: "let price = 10;".to_owned(),
            replacement_content: "let price_cents = 1000;".to_owned(),
            allow_multiple: false,
        },
        ReplacementChunk {
            start_line: 4,
            end_line: 4,
            target_content: "let tax = 2;".to_owned(),
            replacement_content: "let tax_cents = 220;\nlet total_cents = 1220;".to_owned(),
            allow_multiple: false,
        },
    ];

    let res = apply_surgical_patches(original, &chunks);
    assert!(res.is_ok());
    if let Ok(outcome) = res {
        assert_eq!(outcome.replacements_applied, 2);
        assert_eq!(outcome.previous_lines, 5);
        assert_eq!(outcome.new_lines, 6);
        assert_eq!(
            outcome.updated_content,
            "line 1\nlet price_cents = 1000;\nline 3\nlet tax_cents = 220;\nlet total_cents = 1220;\nline 5\n"
        );
    }
}

#[test]
fn surgical_patch_rejects_ambiguous_or_overlapping_chunks() {
    let original = "dup\ndup\nend\n";
    let ambig = vec![ReplacementChunk {
        start_line: 1,
        end_line: 2,
        target_content: "dup".to_owned(),
        replacement_content: "fixed".to_owned(),
        allow_multiple: false,
    }];
    assert_eq!(
        apply_surgical_patches(original, &ambig),
        Err(ActionError::AmbiguousTarget {
            start_line: 1,
            end_line: 2,
            matches: 2
        })
    );

    let overlap = vec![
        ReplacementChunk {
            start_line: 1,
            end_line: 2,
            target_content: "dup".to_owned(),
            replacement_content: "a".to_owned(),
            allow_multiple: true,
        },
        ReplacementChunk {
            start_line: 2,
            end_line: 3,
            target_content: "end".to_owned(),
            replacement_content: "b".to_owned(),
            allow_multiple: false,
        },
    ];
    assert_eq!(
        apply_surgical_patches(original, &overlap),
        Err(ActionError::OverlappingChunks {
            first_end: 2,
            second_start: 2
        })
    );
}

#[test]
fn workspace_coordinator_merges_disjoint_worker_edits_and_detects_conflicts() {
    let mut base = BTreeMap::new();
    base.insert(
        "src/store.rs".to_owned(),
        "mod catalog;\nmod cart;\nmod payment;\nmod shipping;\n".to_owned(),
    );
    let mut coord = WorkspaceCoordinator::new(base.clone());

    assert!(
        coord
            .stage_edit(StagedEdit {
                worker: "agent-catalog".to_owned(),
                path: "src/store.rs".to_owned(),
                chunks: vec![ReplacementChunk {
                    start_line: 1,
                    end_line: 1,
                    target_content: "mod catalog;".to_owned(),
                    replacement_content: "pub mod catalog;".to_owned(),
                    allow_multiple: false,
                }],
            })
            .is_ok()
    );
    assert!(
        coord
            .stage_edit(StagedEdit {
                worker: "agent-payment".to_owned(),
                path: "src/store.rs".to_owned(),
                chunks: vec![ReplacementChunk {
                    start_line: 3,
                    end_line: 3,
                    target_content: "mod payment;".to_owned(),
                    replacement_content: "pub mod payment;".to_owned(),
                    allow_multiple: false,
                }],
            })
            .is_ok()
    );

    let merged = coord.merge_all();
    assert!(merged.is_ok());
    if let Ok(report) = merged {
        assert_eq!(report.applied_edits, 2);
        assert_eq!(
            report.merged_files.get("src/store.rs").map(String::as_str),
            Some("pub mod catalog;\nmod cart;\npub mod payment;\nmod shipping;\n")
        );
    }

    let mut conflicting = WorkspaceCoordinator::new(base);
    let _ = conflicting.stage_edit(StagedEdit {
        worker: "w1".to_owned(),
        path: "src/store.rs".to_owned(),
        chunks: vec![ReplacementChunk {
            start_line: 1,
            end_line: 2,
            target_content: "mod catalog;".to_owned(),
            replacement_content: "pub mod catalog;".to_owned(),
            allow_multiple: false,
        }],
    });
    let _ = conflicting.stage_edit(StagedEdit {
        worker: "w2".to_owned(),
        path: "src/store.rs".to_owned(),
        chunks: vec![ReplacementChunk {
            start_line: 2,
            end_line: 3,
            target_content: "mod cart;".to_owned(),
            replacement_content: "pub mod cart;".to_owned(),
            allow_multiple: false,
        }],
    });
    assert!(matches!(
        conflicting.merge_all(),
        Err(ActionError::MergeConflict { .. })
    ));
}

#[test]
fn batch_planner_groups_reads_and_separates_colliding_writes() {
    let actions = vec![
        ActionItem {
            id: "r1".to_owned(),
            kind: ActionKind::ReadFile,
            target_path: Some("a.rs".to_owned()),
        },
        ActionItem {
            id: "r2".to_owned(),
            kind: ActionKind::ViewOutline,
            target_path: Some("b.rs".to_owned()),
        },
        ActionItem {
            id: "w1".to_owned(),
            kind: ActionKind::SurgicalPatch,
            target_path: Some("a.rs".to_owned()),
        },
        ActionItem {
            id: "w2".to_owned(),
            kind: ActionKind::SurgicalPatch,
            target_path: Some("b.rs".to_owned()),
        },
        ActionItem {
            id: "w3".to_owned(),
            kind: ActionKind::SurgicalPatch,
            target_path: Some("a.rs".to_owned()),
        },
        ActionItem {
            id: "c1".to_owned(),
            kind: ActionKind::RunCheck,
            target_path: None,
        },
    ];

    let plan = plan_parallel_batch(&actions);
    assert_eq!(plan.total_actions, 6);
    assert_eq!(plan.waves.len(), 4);
    assert_eq!(plan.waves.first().map(|w| w.parallel_ids.len()), Some(2));
}

#[test]
fn acceptance_gate_requires_verified_proofs_and_artifacts() {
    let p_res = Proof::new("Tests pass", "cargo test", "ok");
    assert!(p_res.is_ok());
    if let Ok(mut p) = p_res {
        let _ = p.record_result("ok", Some("sha256:123"), true);
        let verdict = evaluate_gate(
            &[p],
            &["src/lib.rs".to_owned()],
            &["src/lib.rs".to_owned(), "src/tests.rs".to_owned()],
        );
        assert!(verdict.passed);
        assert_eq!(verdict.verified_proofs, 1);
    }
}

#[test]
fn test_preflight_invariants_allow_and_deny() {
    use crate::preflight::{
        ActionCommandSpec, ActionInvariant, PreflightSimulator, PreflightVerdict,
    };

    let invariants = vec![
        ActionInvariant::FilesystemBoundary {
            allowed_root: "/home/antigravity/workspace".to_string(),
        },
        ActionInvariant::ForbiddenPatterns {
            blacklisted_tokens: vec!["rm -rf /".to_string(), "mkfs".to_string()],
        },
        ActionInvariant::ResourceQuota {
            max_payload_bytes: 1024,
            max_files: 5,
        },
    ];
    let sim = PreflightSimulator::new(invariants);

    let valid_spec = ActionCommandSpec {
        command: "cargo check".to_string(),
        working_dir: "/home/antigravity/workspace/proj".to_string(),
        modified_files: vec!["/home/antigravity/workspace/proj/src/lib.rs".to_string()],
        payload_bytes: 256,
    };
    assert_eq!(sim.evaluate(&valid_spec), PreflightVerdict::Allowed);

    let boundary_violation = ActionCommandSpec {
        command: "cargo check".to_string(),
        working_dir: "/etc".to_string(),
        modified_files: vec![],
        payload_bytes: 0,
    };
    assert!(matches!(
        sim.evaluate(&boundary_violation),
        PreflightVerdict::Denied { .. }
    ));

    let pattern_violation = ActionCommandSpec {
        command: "rm -rf / --no-preserve-root".to_string(),
        working_dir: "/home/antigravity/workspace".to_string(),
        modified_files: vec![],
        payload_bytes: 0,
    };
    assert!(matches!(
        sim.evaluate(&pattern_violation),
        PreflightVerdict::Denied { .. }
    ));

    let quota_violation = ActionCommandSpec {
        command: "cat big".to_string(),
        working_dir: "/home/antigravity/workspace".to_string(),
        modified_files: vec![],
        payload_bytes: 5000,
    };
    assert!(matches!(
        sim.evaluate(&quota_violation),
        PreflightVerdict::Denied { .. }
    ));
}

#[test]
fn jev_web_navigator_validates_urls_and_executes_booking_lifecycle() {
    use crate::jev_web::{
        build_google_search_jev_plan, build_restaurant_booking_jev_plan, sanitize_zero_trust_url,
        verify_and_advance_jev_step,
    };

    assert!(sanitize_zero_trust_url("https://www.google.com/search?q=nuxiva").is_ok());
    assert!(sanitize_zero_trust_url("http://127.0.0.1:8080/admin").is_err());
    assert!(sanitize_zero_trust_url("http://192.168.1.1/router").is_err());
    assert!(sanitize_zero_trust_url("javascript:alert(1)").is_err());

    let search = build_google_search_jev_plan("sess-01", "miglior ristorante giapponese milano");
    assert!(search.is_ok());
    if let Ok(mut plan) = search {
        assert_eq!(
            plan.entry_url,
            "https://www.google.com/search?q=miglior+ristorante+giapponese+milano"
        );
        assert_eq!(
            verify_and_advance_jev_step(&mut plan, "dom.input.typed", false),
            Ok(false)
        );
        assert_eq!(
            verify_and_advance_jev_step(&mut plan, "dom.results.loaded", false),
            Ok(true)
        );
        assert!(plan.completed);
    }

    let booking = build_restaurant_booking_jev_plan(
        "sess-02",
        "Osteria Francescana Modena",
        2,
        "2026-11-22T20:30",
    );
    assert!(booking.is_ok());
    if let Ok(mut b_plan) = booking {
        assert_eq!(
            verify_and_advance_jev_step(&mut b_plan, "slot.2030.selected", false),
            Ok(false)
        );
        assert_eq!(
            verify_and_advance_jev_step(&mut b_plan, "submit.ready", false),
            Ok(false)
        );
        assert_eq!(b_plan.current_step, 2);
        assert_eq!(
            verify_and_advance_jev_step(&mut b_plan, "submit.ready", true),
            Ok(false)
        );
        assert_eq!(
            verify_and_advance_jev_step(&mut b_plan, "booking.confirmed.id", true),
            Ok(true)
        );
        assert!(b_plan.completed);
    }
}
