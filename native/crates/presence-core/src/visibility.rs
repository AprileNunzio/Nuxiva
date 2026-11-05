use nuxiva_display_domain::{AudienceKind, Sensitivity};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Show {
    pub guest_public: bool,
    pub trust_guests: bool,
}

#[must_use]
pub const fn widget_visible(
    kind: AudienceKind,
    level: Sensitivity,
    guest_safe: bool,
    alert: bool,
    show: Show,
) -> bool {
    let public = matches!(level, Sensitivity::Public);
    if alert && public {
        return true;
    }
    match kind {
        AudienceKind::GuestOnly => show.guest_public && guest_safe && public,
        _ => kind.may_see(level, show.trust_guests),
    }
}
