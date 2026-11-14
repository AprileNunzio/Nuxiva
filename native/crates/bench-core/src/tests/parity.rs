use crate::*;

struct Lcg(u64);

impl Lcg {
    fn next(&mut self) -> u64 {
        self.0 = self
            .0
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
        self.0 >> 33
    }

    fn below(&mut self, n: u64) -> u64 {
        self.next() % n
    }
}

fn reference_distance(r: &[String], h: &[String]) -> usize {
    let mut d = vec![vec![0usize; h.len() + 1]; r.len() + 1];
    for i in 0..=r.len() {
        d[i][0] = i;
    }
    for j in 0..=h.len() {
        d[0][j] = j;
    }
    for i in 1..=r.len() {
        for j in 1..=h.len() {
            let sub = d[i - 1][j - 1] + usize::from(r[i - 1] != h[j - 1]);
            d[i][j] = sub.min(d[i - 1][j] + 1).min(d[i][j - 1] + 1);
        }
    }
    d[r.len()][h.len()]
}

fn words(rng: &mut Lcg, max: u64) -> Vec<String> {
    let n = rng.below(max + 1);
    (0..n).map(|_| format!("w{}", rng.below(5))).collect()
}

#[test]
fn edit_distance_matches_full_matrix_reference() {
    let mut rng = Lcg(42);
    for _ in 0..2_000 {
        let r = words(&mut rng, 12);
        let h = words(&mut rng, 12);
        let ops = align(&r, &h);
        assert_eq!(
            ops.errors() as usize,
            reference_distance(&r, &h),
            "{r:?} {h:?}"
        );
        assert!(ops.deletions as usize <= r.len());
        assert!(r.len() + ops.insertions as usize == h.len() + ops.deletions as usize);
    }
}

#[test]
fn wer_known_cases() {
    let t = |s: &str| tokens(s);
    let o = align(&t("il gatto dorme sul divano"), &t("il gatto dorme divano"));
    assert_eq!((o.substitutions, o.deletions, o.insertions), (0, 1, 0));
    let o = align(&t("accendi la luce"), &t("spegni la luce ora"));
    assert_eq!((o.substitutions, o.deletions, o.insertions), (1, 0, 1));
    let o = align(&t("a b c"), &t(""));
    assert_eq!(o.deletions, 3);
    assert_eq!(tokens("L'ora, È: Tardi!"), vec!["l", "ora", "è", "tardi"]);
}

#[test]
fn wer_report_golden() {
    let report = crate::wer::analyze([
        ("accendi la luce", "accendi la luce"),
        ("spegni la luce del salotto", "spegni la luce salotto"),
        ("che ore sono", "che ore sono adesso"),
        ("apri la porta", "chiudi la porta"),
    ])
    .expect("wer");
    assert_eq!(report.utterances, 4);
    assert_eq!(report.reference_words, 14);
    assert_eq!(
        (report.substitutions, report.deletions, report.insertions),
        (1, 1, 1)
    );
    assert!((report.wer - 3.0 / 14.0).abs() < 1e-6);
    assert!((report.utterance_error_rate - 0.75).abs() < 1e-9);
}

fn reference_percentile(sorted: &[f64], pct: f64) -> f64 {
    let rank = (pct / 100.0 * sorted.len() as f64).ceil().max(1.0) as usize;
    sorted[rank - 1]
}

#[test]
fn percentiles_match_float_reference() {
    let mut rng = Lcg(7);
    for len in 1..300u64 {
        let values: Vec<f64> = (0..len).map(|_| rng.below(10_000) as f64 / 10.0).collect();
        let mut sorted = values.clone();
        sorted.sort_by(f64::total_cmp);
        let s = summarize(&values).expect("summary");
        assert_eq!(s.p50, reference_percentile(&sorted, 50.0));
        assert_eq!(s.p95, reference_percentile(&sorted, 95.0));
        assert_eq!(s.p99, reference_percentile(&sorted, 99.0));
        assert_eq!(s.max, *sorted.last().expect("max"));
        assert_eq!(s.n, len);
    }
}

#[test]
fn percentile_boundaries_and_rejections() {
    let hundred: Vec<f64> = (1..=100).map(f64::from).collect();
    let s = summarize(&hundred).expect("summary");
    assert_eq!((s.p50, s.p95, s.p99, s.max), (50.0, 95.0, 99.0, 100.0));
    assert_eq!(summarize(&[]).expect("empty"), Summary::default());
    assert!(summarize(&[1.0, f64::NAN]).is_err());
    assert!(summarize(&[-1.0]).is_err());
    assert!(summarize(&[f64::INFINITY]).is_err());
}

#[test]
fn stage_breakdown_sums_to_end_to_end() {
    let obs = generate(9, Profile::Healthy, Scale::standard());
    let times: Vec<StageTimes> = obs.utterances.iter().map(|u| u.stages).collect();
    let report = crate::latency::analyze(&times).expect("latency");
    assert_eq!(report.stages.len(), STAGES.len());
    let total_mean: f64 = report.stages.values().map(|s| s.mean).sum();
    assert!((total_mean - report.end_to_end.mean).abs() < 0.01);
    for name in STAGES {
        assert!(report.stages.contains_key(name));
    }
}
