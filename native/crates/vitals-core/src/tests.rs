use crate::pulse::{agreed, breath_rate, heart_rate};
use crate::watch::{
    ATTEMPT, REFRESH, SHOW, Seen, Source, Values, Watch, camera_allowed, valid_slug,
};

#[allow(clippy::cast_precision_loss)]
fn clock(count: usize, rate: f64) -> Vec<f64> {
    (0..count).map(|i| 100.0 + i as f64 / rate).collect()
}

fn seen(slug: &str, device: Option<f64>, camera: Option<f64>) -> Seen {
    Seen {
        slug: slug.to_owned(),
        device: Values::cleaned(device, None),
        camera: Values::cleaned(camera, camera.map(|_| 14.0)),
    }
}

#[test]
fn heart_rate_finds_a_synthetic_pulse() {
    let ts = clock(360, 30.0);
    let rgb: Vec<[f64; 3]> = ts
        .iter()
        .map(|t| {
            let wave = (2.0 * std::f64::consts::PI * 1.2 * t).sin();
            [120.0 + 0.3 * wave, 100.0 + 0.9 * wave, 80.0 + 0.2 * wave]
        })
        .collect();
    let estimate = heart_rate(&ts, &rgb);
    assert!((estimate.per_minute - 72.0).abs() < 2.0, "{estimate:?}");
    assert!(estimate.quality > 0.5);
}

#[test]
fn breath_rate_finds_a_synthetic_chest_motion() {
    let ts = clock(600, 20.0);
    let shift: Vec<f64> = ts
        .iter()
        .map(|t| 0.02 * (2.0 * std::f64::consts::PI * 0.25 * t).sin())
        .collect();
    let estimate = breath_rate(&ts, &shift);
    assert!((estimate.per_minute - 15.0).abs() < 1.0, "{estimate:?}");
}

#[test]
fn bad_input_gives_nothing() {
    assert_eq!(heart_rate(&[1.0, 2.0], &[[1.0; 3]; 2]).per_minute, 0.0);
    let ts = clock(100, 30.0);
    assert_eq!(heart_rate(&ts, &vec![[0.5; 3]; 100]).per_minute, 0.0);
    let mut shuffled = clock(400, 30.0);
    shuffled.swap(3, 9);
    assert_eq!(
        heart_rate(&shuffled, &vec![[100.0; 3]; 400]).per_minute,
        0.0
    );
    assert_eq!(breath_rate(&[f64::NAN; 40], &[0.0; 40]).per_minute, 0.0);
}

#[test]
fn agreement_needs_three_close_values() {
    assert_eq!(agreed(&[Some(70.0), Some(72.0)], 3, 6.0), None);
    assert_eq!(agreed(&[Some(70.0), None, Some(72.0)], 3, 6.0), None);
    assert_eq!(agreed(&[Some(70.0), Some(80.0), Some(72.0)], 3, 6.0), None);
    assert_eq!(
        agreed(&[Some(90.0), Some(70.0), Some(73.0), Some(72.0)], 3, 6.0),
        Some(72)
    );
}

#[test]
fn privacy_rules_per_person() {
    assert!(camera_allowed(None, None, "family", None));
    assert!(!camera_allowed(Some(false), None, "owner", Some(true)));
    assert!(!camera_allowed(Some(true), Some(false), "owner", None));
    assert!(!camera_allowed(Some(true), None, "guest", Some(false)));
    assert!(camera_allowed(Some(true), None, "guest", Some(true)));
    assert!(valid_slug("anna-2"));
    assert!(!valid_slug("Anna"));
    assert!(!valid_slug("../x"));
    assert!(!valid_slug(""));
}

#[test]
fn background_attempt_shows_only_a_reliable_value() {
    let mut watch = Watch::new();
    let out = watch.tick(&[seen("anna", None, None)], true, 100.0);
    assert!(out.shown.is_empty());
    assert_eq!(out.force, vec![("anna".to_owned(), ATTEMPT)]);
    assert!(
        watch
            .tick(&[seen("anna", None, None)], true, 130.0)
            .shown
            .is_empty()
    );
    let out = watch.tick(&[seen("anna", None, Some(71.4))], true, 131.0);
    assert_eq!(out.shown.len(), 1);
    let row = out
        .shown
        .first()
        .map(|r| (r.values.heart, r.values.breath, r.source));
    assert_eq!(row, Some((Some(71.0), Some(14.0), Source::Camera)));
    let out = watch.tick(&[seen("anna", None, None)], true, 131.0 + SHOW);
    assert!(out.shown.is_empty());
    assert_eq!(out.force, vec![("anna".to_owned(), 0.0)]);
    assert!(
        watch
            .tick(&[seen("anna", None, Some(70.0))], true, 500.0)
            .shown
            .is_empty()
    );
    let out = watch.tick(
        &[seen("anna", None, None)],
        true,
        131.0 + SHOW + REFRESH + 1.0,
    );
    assert!(out.shown.is_empty());
    assert!(
        watch
            .tick(
                &[seen("anna", None, None)],
                true,
                131.0 + SHOW + REFRESH + 2.0
            )
            .force
            .iter()
            .any(|f| f.1 > 0.0)
    );
}

#[test]
fn failed_attempts_retry_silently_with_growing_pauses() {
    let mut watch = Watch::new();
    watch.tick(&[seen("anna", None, None)], true, 0.0);
    let out = watch.tick(&[seen("anna", None, None)], true, ATTEMPT);
    assert!(out.shown.is_empty());
    assert_eq!(out.force, vec![("anna".to_owned(), 0.0)]);
    assert!(
        watch
            .tick(&[seen("anna", None, None)], true, ATTEMPT + 10.0)
            .force
            .is_empty()
    );
    let out = watch.tick(&[seen("anna", None, None)], true, ATTEMPT + 20.0);
    assert_eq!(out.force, vec![("anna".to_owned(), ATTEMPT)]);
    watch.tick(&[seen("anna", None, None)], true, 2.0 * ATTEMPT + 20.0);
    assert!(
        watch
            .tick(&[seen("anna", None, None)], true, 2.0 * ATTEMPT + 50.0)
            .force
            .is_empty()
    );
    assert_eq!(
        watch
            .tick(&[seen("anna", None, None)], true, 2.0 * ATTEMPT + 60.0)
            .force
            .len(),
        1
    );
}

#[test]
fn device_values_win_and_stop_the_camera() {
    let mut watch = Watch::new();
    watch.tick(&[seen("anna", None, None)], true, 0.0);
    let out = watch.tick(&[seen("anna", Some(64.0), None)], true, 5.0);
    assert_eq!(out.force, vec![("anna".to_owned(), 0.0)]);
    assert_eq!(out.shown.first().map(|r| r.source), Some(Source::Device));
}

#[test]
fn several_people_are_measured_independently() {
    let mut watch = Watch::new();
    let crowd: Vec<Seen> = ["anna", "bruno", "carla", "dario", "elena"]
        .iter()
        .map(|s| seen(s, None, None))
        .collect();
    let out = watch.tick(&crowd, true, 0.0);
    assert_eq!(out.force.len(), 4);
    assert_eq!(watch.tracked(), 4);
    let mixed = vec![
        seen("anna", None, Some(80.0)),
        seen("bruno", Some(60.0), None),
        seen("carla", None, None),
        seen("anna", None, Some(50.0)),
    ];
    let out = watch.tick(&mixed, true, 10.0);
    let rows: Vec<(&str, Option<f64>, Source)> = out
        .shown
        .iter()
        .map(|r| (r.slug.as_str(), r.values.heart, r.source))
        .collect();
    assert_eq!(
        rows,
        vec![
            ("anna", Some(80.0), Source::Camera),
            ("bruno", Some(60.0), Source::Device)
        ]
    );
    let out = watch.tick(&[seen("bruno", Some(61.0), None)], true, 30.0);
    assert!(out.force.iter().any(|(s, v)| s == "anna" && *v == 0.0));
    assert_eq!(out.shown.len(), 1);
    assert!(watch.forget("bruno"));
    assert!(!watch.forget("bruno"));
}

#[test]
fn camera_off_never_forces() {
    let mut watch = Watch::new();
    assert!(
        watch
            .tick(&[seen("anna", None, None)], false, 0.0)
            .force
            .is_empty()
    );
    assert!(
        watch
            .tick(&[seen("anna", None, None)], false, 1.0)
            .force
            .iter()
            .all(|f| f.1 == 0.0)
    );
}
