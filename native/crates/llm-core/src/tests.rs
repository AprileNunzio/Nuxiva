use crate::{
    Candidate, CriticWeights, Group, RankError, best_index, cosine, group_models, retrieve, round3,
    score, valid_text,
};

type Check = Result<(), RankError>;

fn pair(name: &str, cloud: bool) -> (String, bool) {
    (name.to_owned(), cloud)
}

#[test]
fn text_validity() {
    assert!(valid_text("ciao"));
    assert!(!valid_text("   "));
    assert!(!valid_text("Errore di rete"));
    assert!(!valid_text("  ERRORE"));
}

#[test]
fn scoring_and_selection() {
    let weights = CriticWeights::default();
    assert!((score(0.88, None, weights) - 0.88).abs() < f64::EPSILON);
    assert!((round3(score(0.88, Some(0.5), weights)) - 0.709).abs() < f64::EPSILON);
    let candidates = [
        Candidate {
            has_text: true,
            score: 0.5,
        },
        Candidate {
            has_text: true,
            score: 0.9,
        },
        Candidate {
            has_text: true,
            score: 0.9,
        },
    ];
    assert_eq!(best_index(&candidates), Some(1));
    assert_eq!(best_index(&[]), None);
}

#[test]
fn rounding_matches_half_even_on_binary_value() {
    assert!((round3(0.0005) - 0.001).abs() < f64::EPSILON);
    assert!((round3(2.675) - 2.675).abs() < f64::EPSILON);
    assert!((round3(0.709_499_9) - 0.709).abs() < f64::EPSILON);
}

#[test]
fn groups_consecutive_runs() {
    let models = [
        pair("a", false),
        pair("b", false),
        pair("c", true),
        pair("d", true),
        pair("e", false),
    ];
    assert_eq!(
        group_models(&models),
        vec![
            Group::Local(vec!["a".into(), "b".into()]),
            Group::Cloud("c".into()),
            Group::Cloud("d".into()),
            Group::Local(vec!["e".into()]),
        ]
    );
    assert!(group_models(&[]).is_empty());
}

#[test]
fn cosine_edge_cases() -> Check {
    assert!(cosine(&[], &[1.0])?.abs() < f64::EPSILON);
    assert!(cosine(&[0.0, 0.0], &[1.0, 2.0])?.abs() < f64::EPSILON);
    assert!((cosine(&[1.0, 0.0], &[1.0, 0.0])? - 1.0).abs() < 1e-12);
    assert_eq!(cosine(&[f64::NAN], &[1.0]), Err(RankError::NotFinite));
    Ok(())
}

#[test]
fn retrieval_keeps_core_agents_and_top_k() -> Check {
    let indexed = vec![
        ("near".to_owned(), vec![1.0, 0.0]),
        ("mid".to_owned(), vec![1.0, 1.0]),
        ("far".to_owned(), vec![0.0, 1.0]),
    ];
    let chosen = retrieve(&[1.0, 0.0], &indexed, 2, &["laws"])?;
    let names: Vec<&str> = chosen.iter().map(String::as_str).collect();
    assert_eq!(names, ["laws", "mid", "near"]);
    Ok(())
}

#[test]
fn privacy_levels() -> Check {
    use crate::{Level, PrivacyDetector, Verdict};
    let detector = PrivacyDetector::new()?;
    let level = |text: &str, names: &[&str]| {
        let owned = [text.to_owned()];
        let people: Vec<String> = names.iter().map(|name| (*name).to_owned()).collect();
        detector.classify_all(&owned, &people)
    };
    assert_eq!(level("ciao a tutti", &[])?, Verdict::Level(Level::Public));
    assert_eq!(
        level("la mia password è questa", &[])?,
        Verdict::Level(Level::Sensitive)
    );
    assert_eq!(
        level("carta 4111 1111 1111 1111", &[])?,
        Verdict::Level(Level::Sensitive)
    );
    assert_eq!(
        level("carta 4111 1111 1111 1112", &[])?,
        Verdict::Level(Level::Public)
    );
    assert_eq!(
        level("scrivi a mario.rossi@example.com", &[])?,
        Verdict::Level(Level::Personal)
    );
    assert_eq!(
        level("chiama il 333 1234567", &[])?,
        Verdict::Level(Level::Personal)
    );
    assert_eq!(
        level("ha chiamato giulia", &["giulia"])?,
        Verdict::Level(Level::Personal)
    );
    assert_eq!(level("日本語", &[])?, Verdict::Defer);
    Ok(())
}

#[test]
fn rate_observation_and_availability() -> Check {
    use crate::{ModelRate, Observed, RateRules, available};
    let rules = RateRules::new().map_err(|_| RankError::NotFinite)?;
    let blank = ModelRate {
        remaining_requests: None,
        request_limit: None,
        remaining_tokens: None,
        reset_at: 0.0,
        cooldown_until: 0.0,
        disabled: false,
    };
    let headers = vec![
        ("Retry-After".to_owned(), "30".to_owned()),
        ("X-RateLimit-Remaining".to_owned(), "1".to_owned()),
    ];
    let Observed::Rate(limited) = rules.observe(blank, &headers, 429, 1000.0) else {
        return Err(RankError::NotFinite);
    };
    assert!((limited.cooldown_until - 1030.0).abs() < f64::EPSILON);
    assert!(!available(&limited, 0, 1010.0));
    assert!(available(&limited, 0, 1031.0) || limited.remaining_requests == Some(1));
    let dated = vec![(
        "retry-after".to_owned(),
        "Wed, 21 Oct 2026 07:28:00 GMT".to_owned(),
    )];
    assert_eq!(rules.observe(blank, &dated, 200, 1.0), Observed::Defer);
    let Observed::Rate(banned) = rules.observe(blank, &[], 401, 1.0) else {
        return Err(RankError::NotFinite);
    };
    assert!(banned.disabled);
    Ok(())
}
