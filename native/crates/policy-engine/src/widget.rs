use std::collections::BTreeSet;

use capability_registry::Role;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Widget {
    pub id: String,
    pub min_role: Role,
    pub contexts: BTreeSet<String>,
}

#[must_use]
pub fn visible<'a>(role: Role, context: &str, widgets: &'a [Widget]) -> Vec<&'a str> {
    widgets
        .iter()
        .filter(|w| {
            role.permits(w.min_role) && (w.contexts.is_empty() || w.contexts.contains(context))
        })
        .map(|w| w.id.as_str())
        .collect()
}
