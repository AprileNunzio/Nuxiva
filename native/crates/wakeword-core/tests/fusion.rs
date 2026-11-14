use nuxiva_wakeword_core::{Decision, Policy, Speaker, decide};

#[test]
fn authorized_voice_with_a_real_wake_is_accepted() {
    let d = decide(0.8, Speaker::Authorized { score: 0.7 }, Policy::default());
    assert!(d.accepted());
    assert!(
        matches!(d, Decision::Accept { confidence, speaker: Some(_) } if (confidence - 0.7).abs() < 1e-6)
    );
}

#[test]
fn unknown_or_ambiguous_voices_are_refused() {
    assert_eq!(
        decide(0.9, Speaker::Unknown { score: 0.1 }, Policy::default()),
        Decision::RejectSpeaker
    );
    assert_eq!(
        decide(0.9, Speaker::Ambiguous, Policy::default()),
        Decision::RejectAmbiguous
    );
    assert_eq!(
        decide(
            0.9,
            Speaker::Authorized { score: f32::NAN },
            Policy::default()
        ),
        Decision::RejectSpeaker
    );
}

#[test]
fn weak_or_invalid_wake_confidence_is_refused_before_the_speaker() {
    assert_eq!(
        decide(0.1, Speaker::Authorized { score: 0.9 }, Policy::default()),
        Decision::RejectWake
    );
    assert_eq!(
        decide(
            f32::NAN,
            Speaker::Authorized { score: 0.9 },
            Policy::default()
        ),
        Decision::RejectWake
    );
}

#[test]
fn missing_voice_profiles_follow_the_policy() {
    assert_eq!(
        decide(0.9, Speaker::Unavailable, Policy::default()),
        Decision::NeedsEnrollment
    );
    let open = Policy {
        min_wake: 0.3,
        require_speaker: false,
    };
    assert!(decide(0.9, Speaker::Unavailable, open).accepted());
    assert_eq!(Decision::NeedsEnrollment.code(), "needs_enrollment");
}
