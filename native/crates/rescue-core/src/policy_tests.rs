use crate::policy::{Policy, PolicyError, Sensitivity};
use crate::signal::Kind;

#[test]
fn defaults_are_valid() {
    assert_eq!(Policy::default().validate(), Ok(()));
    assert_eq!(Policy::from_json(""), Ok(Policy::default()));
}

#[test]
fn rejects_unordered_thresholds() {
    let p = Policy {
        check: 0.1,
        watch: 0.2,
        ..Policy::default()
    };
    assert_eq!(p.validate(), Err(PolicyError::Thresholds));
    let p = Policy {
        critical: f64::NAN,
        ..Policy::default()
    };
    assert_eq!(p.validate(), Err(PolicyError::Thresholds));
}

#[test]
fn rejects_bad_timing_and_tiers() {
    assert_eq!(
        Policy {
            check_in_s: 2.0,
            ..Policy::default()
        }
        .validate(),
        Err(PolicyError::Timing)
    );
    assert_eq!(
        Policy {
            alert_grace_s: 50.0,
            check_in_s: 20.0,
            ..Policy::default()
        }
        .validate(),
        Err(PolicyError::Timing)
    );
    assert_eq!(
        Policy {
            family_tiers: 0,
            ..Policy::default()
        }
        .validate(),
        Err(PolicyError::Tiers)
    );
    assert_eq!(
        Policy {
            emergency_rounds: 9,
            ..Policy::default()
        }
        .validate(),
        Err(PolicyError::Tiers)
    );
}

#[test]
fn rejects_unknown_fields_and_oversize() {
    assert_eq!(
        Policy::from_json(r#"{"unlock_doors": true}"#),
        Err(PolicyError::Format)
    );
    assert_eq!(
        Policy::from_json(&"x".repeat(20_000)),
        Err(PolicyError::Format)
    );
}

#[test]
fn reliability_override_is_bounded() {
    let p = Policy::from_json(r#"{"reliability": {"fall": 0.9}}"#).unwrap_or_default();
    assert!((p.reliability_of(Kind::Fall) - 0.9).abs() < 1e-9);
    assert_eq!(
        Policy::from_json(r#"{"reliability": {"fall": 1.5}}"#),
        Err(PolicyError::Reliability)
    );
}

#[test]
fn sensitivity_moves_thresholds() {
    let high = Policy {
        sensitivity: Sensitivity::High,
        ..Policy::default()
    };
    let low = Policy {
        sensitivity: Sensitivity::Low,
        ..Policy::default()
    };
    assert!(high.check_at() < Policy::default().check_at());
    assert!(low.check_at() > Policy::default().check_at());
    assert!(low.critical_at() <= 0.99);
}
