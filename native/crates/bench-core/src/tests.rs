use std::path::PathBuf;

use nuxiva_collaudo_core::Verdict;

use crate::stats_api::{count_f, u64_f64};
use crate::*;

mod parity;

fn tmp(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "bench-{tag}-{}-{}",
        std::process::id(),
        blake3::hash(tag.as_bytes()).to_hex()
    ));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).expect("dir");
    dir
}

fn args(items: &[&str]) -> Vec<String> {
    items.iter().map(|s| (*s).to_owned()).collect()
}

fn healthy(seed: u64) -> Observations {
    generate(seed, Profile::Healthy, Scale::standard())
}

#[test]
fn healthy_profile_passes_default_thresholds() {
    for seed in 1..=8 {
        let report = run(&healthy(seed), &Thresholds::default()).expect("run");
        assert_eq!(
            report.verdict,
            Verdict::Pass,
            "seed {seed}: {:?} {:?}",
            report.violations,
            report.insufficient
        );
    }
}

#[test]
fn degraded_profile_fails_and_names_metrics() {
    let obs = generate(3, Profile::Degraded, Scale::standard());
    let report = run(&obs, &Thresholds::default()).expect("run");
    assert_eq!(report.verdict, Verdict::Fail);
    let failing: Vec<&str> = report
        .violations
        .iter()
        .filter(|v| v.severity == Severity::Fail)
        .map(|v| v.metric.as_str())
        .collect();
    for metric in [
        "e2e_p95_ms",
        "wer",
        "broadcast_as_known_rate",
        "wake_miss_rate",
    ] {
        assert!(failing.contains(&metric), "{metric} missing in {failing:?}");
    }
}

#[test]
fn generation_and_report_are_deterministic() {
    let a = run(&healthy(5), &Thresholds::default()).expect("a");
    let b = run(&healthy(5), &Thresholds::default()).expect("b");
    assert_eq!(a, b);
    assert_eq!(
        serde_json::to_string(&a).expect("a"),
        serde_json::to_string(&b).expect("b")
    );
    assert_ne!(
        healthy(5).fingerprint().expect("f"),
        healthy(6).fingerprint().expect("f")
    );
}

#[test]
fn report_contains_no_text_or_personal_data() {
    let obs = healthy(2);
    let report = run(&obs, &Thresholds::default()).expect("run");
    let text = serde_json::to_string(&report).expect("json");
    for sentence in SENTENCES {
        for word in sentence.split_whitespace().filter(|w| w.len() > 5) {
            assert!(!text.contains(word), "leaked {word}");
        }
    }
    assert!(!text.contains("\"reference\""));
    assert!(!text.contains("hypothesis"));
    assert_eq!(report.source, Source::Synthetic);
}

#[test]
fn missing_or_small_sections_are_insufficient_not_pass() {
    let mut obs = healthy(1);
    obs.barge.clear();
    let report = run(&obs, &Thresholds::default()).expect("run");
    assert_eq!(report.verdict, Verdict::Insufficient);
    assert_eq!(report.insufficient, vec!["barge".to_owned()]);
    let mut small = healthy(1);
    small.utterances.truncate(5);
    let report = run(&small, &Thresholds::default()).expect("run");
    assert!(report.insufficient.contains(&"wer".to_owned()));
    let relaxed = Thresholds {
        required: vec!["latency".to_owned()],
        ..Thresholds::default()
    };
    let mut only = healthy(1);
    only.barge.clear();
    only.wake.clear();
    only.speaker.clear();
    let report = run(&only, &relaxed).expect("run");
    assert_eq!(report.verdict, Verdict::Pass);
}

#[test]
fn regression_gate_trips_on_slowdown_even_under_hard_limits() {
    let th = Thresholds::default();
    let baseline = run(&healthy(4), &th).expect("base");
    let mut slow = healthy(4);
    for u in &mut slow.utterances {
        u.stages.transcribe_ms *= 1.5;
    }
    let mut current = run(&slow, &th).expect("slow");
    assert_ne!(current.verdict, Verdict::Fail);
    compare(&baseline, &mut current, &th);
    assert_eq!(current.verdict, Verdict::Fail);
    assert!(current.regressions.iter().any(|r| r.metric == "e2e_p50_ms"));
    let mut same = run(&healthy(4), &th).expect("same");
    compare(&baseline, &mut same, &th);
    assert!(same.regressions.is_empty());
    assert_eq!(same.verdict, Verdict::Pass);
}

#[test]
fn radio_leak_is_counted_per_background() {
    let mut obs = healthy(1);
    obs.speaker = (0..100)
        .map(|i| SpeakerTrial {
            truth: Class::Broadcast,
            predicted: if i < 10 {
                Class::Known
            } else {
                Class::Broadcast
            },
            truth_slot: None,
            predicted_slot: if i < 10 { Some(0) } else { None },
            background: Background::Radio,
        })
        .collect();
    let report = run(&obs, &Thresholds::default()).expect("run");
    let s = report.speaker.expect("speaker");
    assert!((s.broadcast_as_known_rate - 0.1).abs() < 1e-9);
    assert!((s.background_false_known_rate - 0.1).abs() < 1e-9);
    assert_eq!(s.confusion.get("broadcast>known"), Some(&10));
    assert!((s.false_known_rate - 1.0).abs() < 1e-9);
    assert!(
        report
            .violations
            .iter()
            .any(|v| v.metric == "broadcast_as_known_rate" && v.severity == Severity::Fail)
    );
}

#[test]
fn wrong_known_slot_counts_as_false_attribution() {
    let trials = [
        SpeakerTrial {
            truth: Class::Known,
            predicted: Class::Known,
            truth_slot: Some(1),
            predicted_slot: Some(2),
            background: Background::None,
        },
        SpeakerTrial {
            truth: Class::Known,
            predicted: Class::Known,
            truth_slot: Some(1),
            predicted_slot: Some(1),
            background: Background::Music,
        },
    ];
    let report = crate::speaker::analyze(&trials);
    assert!((report.known_miss_rate - 0.5).abs() < 1e-9);
    assert!((report.false_known_rate - 0.5).abs() < 1e-9);
    assert!((report.background_known_miss_rate - 0.0).abs() < 1e-9);
}

#[test]
fn wake_rates_use_audio_time() {
    let mut trials = vec![
        WakeTrial {
            expect_wake: false,
            fired: false,
            audio_ms: 1_800_000,
            background: Background::None,
        };
        2
    ];
    trials.push(WakeTrial {
        expect_wake: false,
        fired: true,
        audio_ms: 1_800_000,
        background: Background::Radio,
    });
    trials.push(WakeTrial {
        expect_wake: true,
        fired: false,
        audio_ms: 4_000,
        background: Background::None,
    });
    let r = crate::wake::analyze(&trials).expect("wake");
    assert!((r.negative_hours - 1.5).abs() < 1e-9);
    assert!((r.false_accepts_per_hour - 0.667).abs() < 1e-9);
    assert!((r.background_false_accepts_per_hour - 2.0).abs() < 1e-9);
    assert!((r.miss_rate - 1.0).abs() < 1e-9);
}

#[test]
fn barge_metrics_and_validation() {
    let trials = [
        BargeTrial {
            expect_barge: true,
            fired: true,
            reaction_ms: Some(200.0),
            background: Background::None,
        },
        BargeTrial {
            expect_barge: true,
            fired: false,
            reaction_ms: None,
            background: Background::None,
        },
        BargeTrial {
            expect_barge: false,
            fired: true,
            reaction_ms: Some(300.0),
            background: Background::Music,
        },
        BargeTrial {
            expect_barge: false,
            fired: false,
            reaction_ms: None,
            background: Background::Music,
        },
    ];
    let r = crate::barge::analyze(&trials).expect("barge");
    assert!((r.miss_rate - 0.5).abs() < 1e-9);
    assert!((r.false_rate - 0.5).abs() < 1e-9);
    assert!((r.background_false_rate - 0.5).abs() < 1e-9);
    assert!((r.reaction.p50 - 200.0).abs() < 1e-9);
    let bad = BargeTrial {
        expect_barge: true,
        fired: false,
        reaction_ms: Some(1.0),
        background: Background::None,
    };
    assert!(crate::barge::analyze(&[bad]).is_err());
}

#[test]
fn observations_reject_malformed_input() {
    let good = serde_json::to_vec(&healthy(1)).expect("json");
    assert!(Observations::parse(&good).is_ok());
    let mut value: serde_json::Value = serde_json::from_slice(&good).expect("value");
    value["extra"] = serde_json::json!(1);
    assert!(Observations::parse(&serde_json::to_vec(&value).expect("v")).is_err());
    let mut bad = healthy(1);
    bad.corpus = "../etc/passwd".to_owned();
    assert!(bad.validate().is_err());
    let mut bad = healthy(1);
    bad.utterances[0].stages.tts_ms = f64::from(u32::MAX);
    assert!(bad.validate().is_err());
    let mut bad = healthy(1);
    bad.utterances[0].reference = "ciao\u{0}".to_owned();
    assert!(bad.validate().is_err());
    let mut bad = healthy(1);
    bad.utterances[0].reference = String::new();
    assert!(run(&bad, &Thresholds::default()).is_err());
    let mut bad = healthy(1);
    bad.wake[0].audio_ms = 0;
    assert!(bad.validate().is_err());
    assert!(Observations::parse(b"{").is_err());
}

#[test]
fn thresholds_validation() {
    let defaults = Thresholds::default();
    let bytes = serde_json::to_vec(&defaults).expect("json");
    assert_eq!(Thresholds::parse(&bytes).expect("parse"), defaults);
    let mut bad = defaults.clone();
    bad.wer = Limit {
        warn: 0.5,
        fail: 0.1,
    };
    assert!(bad.validate().is_err());
    let mut bad = defaults.clone();
    bad.required.push("nope".to_owned());
    assert!(bad.validate().is_err());
    let mut bad = defaults;
    bad.e2e_p50_ms.fail = f64::NAN;
    assert!(bad.validate().is_err());
}

#[test]
fn ledger_a12_streaks_chain_and_idempotence() {
    let mut ledger = Ledger::default();
    let c = Criteria::default();
    for day in 0..14u32 {
        ledger
            .append(Kind::CiGreen, &format!("run{day}a"), day)
            .expect("a");
        ledger
            .append(Kind::CiGreen, &format!("run{day}b"), day)
            .expect("b");
    }
    assert!(!ledger.append(Kind::CiGreen, "run0a", 20).expect("dup"));
    for i in 0..3 {
        ledger
            .append(Kind::ShadowClean, &format!("sh{i}"), 13)
            .expect("s");
    }
    let s = ledger.status(&c, 14);
    assert!(s.ready, "{s:?}");
    assert_eq!(s.ci_green_streak, 28);
    let early = ledger.status(&c, 13);
    assert!(early.missing.contains(&"days".to_owned()));
    ledger.append(Kind::CiRed, "bad", 14).expect("red");
    let s = ledger.status(&c, 20);
    assert!(!s.ready && s.missing.contains(&"ci_green".to_owned()));
    ledger
        .append(Kind::ShadowDivergent, "div", 14)
        .expect("div");
    assert!(
        ledger
            .status(&c, 20)
            .missing
            .contains(&"shadow_clean".to_owned())
    );
    assert!(ledger.append(Kind::CiGreen, "late", 1).is_err());
    assert!(ledger.append(Kind::CiGreen, "bad id", 20).is_err());
    let bytes = serde_json::to_vec(&ledger).expect("json");
    assert_eq!(Ledger::parse(&bytes).expect("parse"), ledger);
    let tampered = String::from_utf8(bytes)
        .expect("utf8")
        .replace("run0a", "runXa");
    assert!(Ledger::parse(tampered.as_bytes()).is_err());
}

#[test]
fn cli_end_to_end_with_exit_codes_and_baseline() {
    let dir = tmp("cli");
    let p = |n: &str| dir.join(n).to_string_lossy().into_owned();
    let (obs, bad, rep, base) = (p("obs.json"), p("bad.json"), p("rep.json"), p("base.json"));
    let out = execute(&args(&["synth", "--seed", "2", "--out", &obs]), 0).expect("synth");
    assert_eq!(out.code, EXIT_PASS);
    execute(
        &args(&[
            "synth",
            "--seed",
            "2",
            "--profile",
            "degraded",
            "--out",
            &bad,
        ]),
        0,
    )
    .expect("synth bad");
    let ok = execute(&args(&["run", "--obs", &obs, "--out", &base]), 0).expect("run");
    assert_eq!(ok.code, EXIT_PASS);
    let fail = execute(&args(&["run", "--obs", &bad, "--out", &rep]), 0).expect("run bad");
    assert_eq!(fail.code, EXIT_FAIL);
    let regress = execute(&args(&["run", "--obs", &bad, "--baseline", &base]), 0).expect("reg");
    assert_eq!(regress.code, EXIT_FAIL);
    let parsed: BenchReport = serde_json::from_str(&regress.stdout).expect("report");
    assert!(!parsed.regressions.is_empty());
    let same = execute(&args(&["run", "--obs", &obs, "--baseline", &base]), 0).expect("same");
    assert_eq!(same.code, EXIT_PASS);
    assert!(execute(&args(&["run"]), 0).is_err());
    assert!(execute(&args(&["run", "--obs", &obs, "--bogus", "1"]), 0).is_err());
    assert!(execute(&args(&["run", "--obs", &obs, "--obs", &obs]), 0).is_err());
    assert!(execute(&args(&["frobnicate"]), 0).is_err());
    assert!(execute(&args(&["synth", "--profile", "x"]), 0).is_err());
    assert!(execute(&args(&["synth", "--seed", "-1"]), 0).is_err());
    let manifest = execute(&args(&["manifest"]), 0).expect("manifest");
    assert!(manifest.stdout.contains("corpus_sentences"));
    let defaults = execute(&args(&["thresholds"]), 0).expect("th");
    assert!(Thresholds::parse(defaults.stdout.as_bytes()).is_ok());
    let _ = std::fs::remove_dir_all(dir);
}

#[test]
fn cli_a12_flow_persists_and_reports() {
    let dir = tmp("a12");
    let ledger = dir.join("ledger.json").to_string_lossy().into_owned();
    let add = |kind: &str, id: &str, day: &str| {
        execute(
            &args(&[
                "a12", "add", "--ledger", &ledger, "--kind", kind, "--id", id, "--day", day,
            ]),
            0,
        )
        .expect("add")
    };
    assert!(add("ci_green", "r1", "100").stdout.contains("true"));
    assert!(add("ci_green", "r1", "100").stdout.contains("false"));
    let status = execute(
        &args(&["a12", "status", "--ledger", &ledger, "--day", "100"]),
        0,
    )
    .expect("st");
    assert_eq!(status.code, EXIT_INSUFFICIENT);
    assert!(execute(&args(&["a12", "status"]), 0).is_err());
    assert!(execute(&args(&["a12", "nope", "--ledger", &ledger]), 0).is_err());
    let _ = std::fs::remove_dir_all(dir);
}

#[test]
fn file_io_is_bounded_and_atomic() {
    let dir = tmp("io");
    let path = dir.join("f.json");
    write_atomic(&path, b"{}").expect("write");
    assert_eq!(read_limited(&path).expect("read"), b"{}");
    write_atomic(&path, b"[]").expect("rewrite");
    assert_eq!(read_limited(&path).expect("read"), b"[]");
    assert!(read_limited(&dir.join("missing")).is_err());
    let leftovers = std::fs::read_dir(&dir).expect("ls").count();
    assert_eq!(leftovers, 1);
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mode = std::fs::metadata(&path).expect("meta").permissions().mode();
        assert_eq!(mode & 0o077, 0);
    }
    let _ = std::fs::remove_dir_all(dir);
}

#[test]
fn numeric_helpers_are_exact() {
    assert!((u64_f64(10_000_000_000) - 1e10).abs() < 1e-3);
    assert!((count_f(7) - 7.0).abs() < 1e-12);
    assert_eq!(verdict_code(Verdict::Warn), EXIT_WARN);
    assert!(is_token("abc-1_2.x") && !is_token("") && !is_token("a b"));
}
