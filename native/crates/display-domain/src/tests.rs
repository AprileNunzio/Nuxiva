use crate::{AudienceKind, SectionKey, Sensitivity, Version};

#[test]
fn section_keys_are_strict() {
    assert!(SectionKey::parse("widget:weather-1").is_ok());
    assert!(SectionKey::parse("").is_err());
    assert!(SectionKey::parse("Widget").is_err());
    assert!(SectionKey::parse("a/b").is_err());
    assert!(SectionKey::parse(&"a".repeat(65)).is_err());
}

#[test]
fn versions_never_overflow() {
    assert_eq!(Version(u64::MAX).next(), Version(u64::MAX));
    assert_eq!(Version(1).next(), Version(2));
}

#[test]
fn only_authorized_audiences_see_personal_data() {
    for kind in [
        AudienceKind::Empty,
        AudienceKind::GuestOnly,
        AudienceKind::Mixed,
        AudienceKind::Uncertain,
    ] {
        assert!(!kind.may_see(Sensitivity::Personal, true));
        assert!(!kind.may_see(Sensitivity::Sensitive, true));
    }
    assert!(AudienceKind::Authorized.may_see(Sensitivity::Sensitive, false));
}

#[test]
fn mixed_audiences_see_household_only_when_guests_are_trusted() {
    assert!(AudienceKind::Mixed.may_see(Sensitivity::Public, false));
    assert!(!AudienceKind::Mixed.may_see(Sensitivity::Household, false));
    assert!(AudienceKind::Mixed.may_see(Sensitivity::Household, true));
}

#[test]
fn guests_and_empty_rooms_keep_only_the_nucleus() {
    assert!(AudienceKind::Empty.nucleus_only());
    assert!(AudienceKind::GuestOnly.nucleus_only());
    assert!(AudienceKind::Uncertain.nucleus_only());
    assert!(!AudienceKind::Mixed.nucleus_only());
    assert!(!AudienceKind::Authorized.nucleus_only());
}
