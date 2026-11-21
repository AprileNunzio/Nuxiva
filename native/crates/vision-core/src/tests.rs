use crate::{FrameMeta, Policy, PushOutcome, Rejection, Source, VisualBuffer};

fn meta(app: &str, title: &str, at_ms: u64) -> FrameMeta {
    FrameMeta {
        source: Source::Screen,
        app: app.to_owned(),
        title: title.to_owned(),
        at_ms,
    }
}

fn vec_of(seed: usize) -> Vec<f32> {
    (0..32)
        .map(|i| if i % 7 == seed % 7 { 1.0 } else { 0.05 })
        .collect()
}

fn consenting() -> VisualBuffer {
    VisualBuffer::new(Policy {
        consent: true,
        ..Policy::default()
    })
}

#[test]
fn nothing_is_stored_without_consent() {
    let mut buf = VisualBuffer::new(Policy::default());
    assert_eq!(
        buf.push(&meta("code", "main.rs", 0), &vec_of(1)),
        PushOutcome::Rejected(Rejection::NoConsent)
    );
    assert!(buf.is_empty());
    assert!(!buf.indicator(0).active);
}

#[test]
fn sensitive_windows_are_never_buffered() {
    let mut buf = consenting();
    for (app, title) in [
        ("1Password", "Vault"),
        ("Firefox", "Home Banking - Banca Intesa"),
        ("Chrome", "PayPal: accesso"),
        ("Firefox", "Navigazione in incognito"),
    ] {
        assert_eq!(
            buf.push(&meta(app, title, 10_000), &vec_of(2)),
            PushOutcome::Rejected(Rejection::Sensitive),
            "{app} {title}"
        );
    }
    assert!(buf.is_empty());
}

#[test]
fn rate_limit_expiry_and_capacity() {
    let mut buf = consenting();
    assert_eq!(
        buf.push(&meta("code", "a", 0), &vec_of(1)),
        PushOutcome::Stored
    );
    assert_eq!(
        buf.push(&meta("code", "a", 500), &vec_of(1)),
        PushOutcome::Rejected(Rejection::TooSoon)
    );
    assert_eq!(
        buf.push(&meta("code", "a", 2_500), &vec_of(2)),
        PushOutcome::Stored
    );
    buf.expire(2_500 + 6 * 60_000);
    assert!(buf.is_empty());
    let mut small = VisualBuffer::new(Policy {
        consent: true,
        capacity: 8,
        interval_ms: 250,
        ..Policy::default()
    });
    for i in 0..20_u64 {
        let _ = small.push(
            &meta("code", "a", i * 300),
            &vec_of(usize::try_from(i).unwrap_or(0)),
        );
    }
    assert_eq!(small.len(), 8);
}

#[test]
fn invalid_embeddings_are_rejected() {
    let mut buf = consenting();
    assert_eq!(
        buf.push(&meta("code", "a", 0), &[f32::NAN; 8]),
        PushOutcome::Rejected(Rejection::Invalid)
    );
    assert_eq!(
        buf.push(&meta("code", "a", 0), &[0.0; 8]),
        PushOutcome::Rejected(Rejection::Invalid)
    );
    assert_eq!(
        buf.push(&meta("code", "a", 0), &vec_of(1)),
        PushOutcome::Stored
    );
    assert_eq!(
        buf.push(&meta("code", "a", 5_000), &[1.0; 8]),
        PushOutcome::Rejected(Rejection::Invalid)
    );
}

#[test]
fn query_context_and_revoke() {
    let mut buf = consenting();
    let _ = buf.push(&meta("editor", "a", 0), &vec_of(1));
    let _ = buf.push(&meta("browser", "b", 3_000), &vec_of(2));
    let hits = buf.query(&vec_of(1), 4_000, 2);
    assert_eq!(hits.first().map(|h| h.app.as_str()), Some("editor"));
    assert_eq!(buf.current_app(4_000), Some("browser"));
    assert!(buf.context(4_000).is_some());
    assert!(buf.indicator(4_000).active);
    buf.set_policy(Policy::default());
    assert!(buf.is_empty());
    assert!(buf.context(4_000).is_none());
}

#[test]
fn visual_recognition_identifies_colors_objects_and_people() {
    use crate::{
        BoundingBox, PersonVisualObservation, RgbSample, SemanticColor, VisualRecognitionEngine,
        extract_color_palette,
    };

    let red_samples = vec![
        RgbSample {
            r: 230,
            g: 25,
            b: 30,
        },
        RgbSample {
            r: 220,
            g: 20,
            b: 25,
        },
        RgbSample {
            r: 15,
            g: 15,
            b: 18,
        },
    ];
    let blue_samples = vec![
        RgbSample {
            r: 20,
            g: 75,
            b: 235,
        },
        RgbSample {
            r: 25,
            g: 85,
            b: 240,
        },
    ];

    let red_palette = extract_color_palette(&red_samples);
    assert_eq!(red_palette.dominant, SemanticColor::WarmRed);
    assert_eq!(red_palette.secondary, Some(SemanticColor::AchromaticBlack));

    let blue_palette = extract_color_palette(&blue_samples);
    assert_eq!(blue_palette.dominant, SemanticColor::CoolBlue);

    let mut engine = VisualRecognitionEngine::new();
    let obj_emb = vec_of(3);
    assert!(engine.learn_object_prototype("object.soldering_iron", &obj_emb, &red_samples));

    let bbox = BoundingBox {
        x_min_bps: 1_000,
        y_min_bps: 2_000,
        x_max_bps: 4_000,
        y_max_bps: 6_000,
    };
    let detected = engine.recognize_object(&obj_emb, &red_samples, bbox);
    assert!(detected.is_some());
    if let Some(obj) = detected {
        assert_eq!(obj.label_key, "object.soldering_iron");
        assert_eq!(obj.palette.dominant, SemanticColor::WarmRed);
        assert!(obj.confidence_bps >= 9_500);
    }

    let face_nunzio = vec_of(5);
    let enroll_obs = PersonVisualObservation {
        person_hint: Some("nunzio".to_owned()),
        face_embedding: Some(face_nunzio.clone()),
        face_quality_bps: 9_200,
        upper_garment_palette: blue_palette.clone(),
        lower_garment_palette: red_palette.clone(),
        bbox,
        at_ms: 10_000,
    };
    assert!(engine.enroll_or_update_person("nunzio", &enroll_obs));

    let direct_match = engine.identify_person(&enroll_obs);
    assert!(direct_match.is_some());
    if let Some(m) = direct_match {
        assert_eq!(m.person_id, "nunzio");
        assert_eq!(m.dominant_garment_color_key, "color.blue");
        assert!(m.combined_confidence_bps >= 9_000);
    }

    let occluded_obs = PersonVisualObservation {
        person_hint: None,
        face_embedding: Some(face_nunzio),
        face_quality_bps: 4_200,
        upper_garment_palette: blue_palette,
        lower_garment_palette: red_palette,
        bbox,
        at_ms: 12_500,
    };
    let reid_match = engine.identify_person(&occluded_obs);
    assert!(reid_match.is_some());
    if let Some(m2) = reid_match {
        assert_eq!(m2.person_id, "nunzio");
        assert!(m2.appearance_contribution_bps >= 9_000);
    }
}
