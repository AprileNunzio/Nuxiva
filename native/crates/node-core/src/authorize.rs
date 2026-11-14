use crate::profile::Mode;
use crate::scope;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verdict {
    Allow,
    Deny(&'static str),
}

#[must_use]
pub fn effective(mode: Mode, announced: &[String], grants: &[String]) -> Vec<String> {
    let mut out: Vec<String> = announced
        .iter()
        .filter(|s| scope::valid(s) && !scope::forbidden(s))
        .filter(|s| {
            scope::base_allowed(mode, s)
                || (mode == Mode::SecondServer
                    && scope::elevated(s)
                    && grants.iter().any(|g| g == *s))
        })
        .cloned()
        .collect();
    out.sort();
    out.dedup();
    out
}

#[must_use]
pub fn authorize(effective: &[String], requested: &str) -> Verdict {
    if !scope::valid(requested) {
        return Verdict::Deny("node.error.scope_invalid");
    }
    if scope::forbidden(requested) {
        return Verdict::Deny("node.error.scope_forbidden");
    }
    if effective.iter().any(|s| s == requested) {
        Verdict::Allow
    } else {
        Verdict::Deny("node.error.scope_not_granted")
    }
}
