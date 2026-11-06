use crate::fusion::{PRIOR_LOGIT, assess, sigmoid};
use crate::policy::Policy;
use crate::signal::{Evidence, EvidenceError, Hazard, Kind};

pub fn ev(kind: Kind, p: f64, c: f64, source: &str, at: f64) -> Evidence {
    Evidence {
        kind,
        probability: p,
        confidence: c,
        source: source.to_owned(),
        room: Some("salotto".to_owned()),
        at,
    }
}

fn risk(list: &[Evidence], hazard: Hazard, now: f64) -> f64 {
    assess(list, &Policy::default(), now).risk(hazard)
}

#[test]
fn nothing_means_prior() {
    let a = assess(&[], &Policy::default(), 10.0);
    assert!(a.hazards.is_empty());
    assert!((a.risk(Hazard::Medical) - sigmoid(PRIOR_LOGIT)).abs() < 1e-12);
}

#[test]
fn single_fall_only_watches() {
    let p = Policy::default();
    let r = risk(
        &[ev(Kind::Fall, 0.9, 0.8, "cam1", 0.0)],
        Hazard::Medical,
        0.0,
    );
    assert!(r >= p.watch_at() && r < p.check_at(), "{r}");
}

#[test]
fn independent_modalities_add_up() {
    let p = Policy::default();
    let fall = ev(Kind::Fall, 0.9, 0.8, "cam1", 0.0);
    let still = ev(Kind::Immobility, 0.9, 0.8, "cam1", 0.0);
    let silent = ev(Kind::NoResponse, 0.9, 1.0, "voice", 0.0);
    let two = risk(&[fall.clone(), still.clone()], Hazard::Medical, 0.0);
    let three = risk(&[fall, still, silent], Hazard::Medical, 0.0);
    assert!(two >= p.check_at(), "{two}");
    assert!(three > two && three >= p.alert_at(), "{three}");
}

#[test]
fn repeated_source_does_not_inflate() {
    let one = risk(
        &[ev(Kind::Scream, 0.9, 0.9, "mic1", 0.0)],
        Hazard::Medical,
        0.0,
    );
    let many: Vec<_> = (0..20)
        .map(|_| ev(Kind::Scream, 0.9, 0.9, "mic1", 0.0))
        .collect();
    assert!((risk(&many, Hazard::Medical, 0.0) - one).abs() < 1e-12);
}

#[test]
fn correlated_sources_are_discounted() {
    let one = ev(Kind::Scream, 0.9, 0.9, "mic1", 0.0);
    let base = assess(std::slice::from_ref(&one), &Policy::default(), 0.0);
    let pair = assess(
        &[one, ev(Kind::Scream, 0.9, 0.9, "mic2", 0.0)],
        &Policy::default(),
        0.0,
    );
    let w1 = base
        .of(Hazard::Medical)
        .map_or(0.0, |h| h.drivers.first().map_or(0.0, |d| d.weight));
    let w2 = pair
        .of(Hazard::Medical)
        .map_or(0.0, |h| h.drivers.first().map_or(0.0, |d| d.weight));
    assert!(w2 > w1 && w2 < 2.0 * w1);
}

#[test]
fn evidence_decays_and_expires() {
    let e = ev(Kind::Scream, 0.95, 1.0, "mic1", 0.0);
    let fresh = risk(std::slice::from_ref(&e), Hazard::Medical, 0.0);
    let later = risk(std::slice::from_ref(&e), Hazard::Medical, 60.0);
    assert!(later < fresh);
    assert!(e.expired(241.0));
    assert!((risk(&[e], Hazard::Medical, 300.0) - sigmoid(PRIOR_LOGIT)).abs() < 1e-12);
}

#[test]
fn all_clear_lowers_medical_but_not_fire() {
    let list = vec![
        ev(Kind::Fall, 0.9, 0.9, "cam1", 0.0),
        ev(Kind::Smoke, 0.9, 1.0, "ha", 0.0),
    ];
    let mut cleared = list.clone();
    cleared.push(ev(Kind::AllClear, 0.95, 1.0, "person", 0.0));
    assert!(risk(&cleared, Hazard::Medical, 0.0) < risk(&list, Hazard::Medical, 0.0));
    assert!((risk(&cleared, Hazard::Fire, 0.0) - risk(&list, Hazard::Fire, 0.0)).abs() < 1e-12);
}

#[test]
fn risk_is_monotonic_in_probability() {
    let mut last = 0.0;
    for step in 0..=100 {
        let p = f64::from(step) / 100.0;
        let r = risk(
            &[ev(Kind::HelpWords, p, 0.9, "mic1", 0.0)],
            Hazard::Medical,
            0.0,
        );
        assert!(r + 1e-12 >= last);
        last = r;
    }
}

#[test]
fn zero_confidence_adds_nothing() {
    let r = risk(&[ev(Kind::Fire, 1.0, 0.0, "ha", 0.0)], Hazard::Fire, 0.0);
    assert!((r - sigmoid(PRIOR_LOGIT)).abs() < 1e-12);
}

#[test]
fn confidence_grows_with_independent_sources() {
    let p = Policy::default();
    let a = assess(&[ev(Kind::Fall, 0.9, 0.6, "cam1", 0.0)], &p, 0.0);
    let b = assess(
        &[
            ev(Kind::Fall, 0.9, 0.6, "cam1", 0.0),
            ev(Kind::Vitals, 0.9, 0.6, "watch", 0.0),
        ],
        &p,
        0.0,
    );
    let ca = a.of(Hazard::Medical).map_or(0.0, |h| h.confidence);
    let cb = b.of(Hazard::Medical).map_or(0.0, |h| h.confidence);
    assert!(cb > ca && cb <= 1.0);
    assert_eq!(b.of(Hazard::Medical).map_or(0, |h| h.modalities), 2);
}

#[test]
fn validation_rejects_bad_input() {
    let ok = ev(Kind::Fall, 0.5, 0.5, "cam1", 10.0);
    assert_eq!(ok.validate(10.0), Ok(()));
    assert_eq!(
        Evidence {
            probability: 1.2,
            ..ok.clone()
        }
        .validate(10.0),
        Err(EvidenceError::Probability)
    );
    assert_eq!(
        Evidence {
            confidence: f64::NAN,
            ..ok.clone()
        }
        .validate(10.0),
        Err(EvidenceError::Confidence)
    );
    assert_eq!(
        Evidence {
            source: "a b".into(),
            ..ok.clone()
        }
        .validate(10.0),
        Err(EvidenceError::Source)
    );
    assert_eq!(
        Evidence {
            source: String::new(),
            ..ok.clone()
        }
        .validate(10.0),
        Err(EvidenceError::Source)
    );
    assert_eq!(
        Evidence {
            room: Some("<x>".into()),
            ..ok.clone()
        }
        .validate(10.0),
        Err(EvidenceError::Room)
    );
    assert_eq!(
        Evidence { at: 100.0, ..ok }.validate(10.0),
        Err(EvidenceError::Time)
    );
}

#[test]
fn every_kind_maps_to_a_hazard() {
    for kind in Kind::ALL {
        assert!(!kind.hazards().is_empty());
        assert!(kind.reliability() > 0.0 && kind.reliability() <= 1.0);
        assert!(kind.half_life() > 0.0);
    }
}
