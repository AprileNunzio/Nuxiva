use crate::visibility::{Show, widget_visible};
use nuxiva_display_domain::{AudienceKind, Sensitivity};

const KINDS: [AudienceKind; 5] = [
    AudienceKind::Empty,
    AudienceKind::GuestOnly,
    AudienceKind::Mixed,
    AudienceKind::Authorized,
    AudienceKind::Uncertain,
];
const LEVELS: [Sensitivity; 4] = [
    Sensitivity::Public,
    Sensitivity::Household,
    Sensitivity::Personal,
    Sensitivity::Sensitive,
];

fn expected(kind: AudienceKind, level: Sensitivity, show: Show, guest_safe: bool) -> bool {
    match kind {
        AudienceKind::Authorized => true,
        AudienceKind::Mixed => match level {
            Sensitivity::Public => true,
            Sensitivity::Household => show.trust_guests,
            Sensitivity::Personal | Sensitivity::Sensitive => false,
        },
        AudienceKind::GuestOnly => show.guest_public && guest_safe && level == Sensitivity::Public,
        AudienceKind::Empty | AudienceKind::Uncertain => false,
    }
}

#[test]
fn the_full_truth_table_holds() {
    for kind in KINDS {
        for level in LEVELS {
            for (guest_public, trust_guests, guest_safe) in [
                (false, false, false),
                (true, false, true),
                (false, true, false),
                (true, true, true),
                (true, true, false),
            ] {
                let show = Show {
                    guest_public,
                    trust_guests,
                };
                assert_eq!(
                    widget_visible(kind, level, guest_safe, false, show),
                    expected(kind, level, show, guest_safe),
                    "{kind:?} {level:?} {show:?} {guest_safe}"
                );
            }
        }
    }
}

#[test]
fn public_safety_alerts_are_always_shown() {
    for kind in KINDS {
        assert!(widget_visible(
            kind,
            Sensitivity::Public,
            false,
            true,
            Show::default()
        ));
    }
}

#[test]
fn personal_alerts_follow_the_audience() {
    assert!(!widget_visible(
        AudienceKind::GuestOnly,
        Sensitivity::Personal,
        false,
        true,
        Show::default()
    ));
    assert!(!widget_visible(
        AudienceKind::Mixed,
        Sensitivity::Sensitive,
        false,
        true,
        Show::default()
    ));
}
