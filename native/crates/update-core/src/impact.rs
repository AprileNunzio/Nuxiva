use serde::Serialize;
use std::collections::BTreeMap;

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize)]
pub struct ComponentImpact {
    pub component: &'static str,
    pub added: usize,
    pub modified: usize,
    pub deleted: usize,
    pub renamed: usize,
}

impl ComponentImpact {
    #[must_use]
    pub fn total(&self) -> usize {
        self.added
            .saturating_add(self.modified)
            .saturating_add(self.deleted)
            .saturating_add(self.renamed)
    }
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize)]
pub struct ImpactReport {
    pub files: usize,
    pub components: Vec<ComponentImpact>,
    pub effects: Vec<&'static str>,
}

#[must_use]
pub fn component_of(path: &str) -> &'static str {
    let top = path.split('/').next().unwrap_or_default();
    match top {
        "server" | "sandbox_broker" => "server",
        "client_web" => "web",
        "native" => "native",
        "installer_wizard" => "supervisor",
        "client_satellite" => "satellite",
        "client_apk" => "android",
        ".github" => "ci",
        "scripts" | "install.sh" | "systemd" => "system",
        "docs" => "docs",
        _ if std::path::Path::new(path)
            .extension()
            .is_some_and(|e| e.eq_ignore_ascii_case("md")) =>
        {
            "docs"
        }
        _ => "other",
    }
}

fn effects_of(path: &str) -> &'static [&'static str] {
    let name = path.rsplit('/').next().unwrap_or_default();
    if name.starts_with("requirements")
        || matches!(
            name,
            "package.json" | "package-lock.json" | "Cargo.lock" | "Cargo.toml"
        )
    {
        return &["dependencies"];
    }
    match component_of(path) {
        "native" => &["rebuild_native", "restart_services"],
        "web" => &["rebuild_web"],
        "server" | "supervisor" => &["restart_services"],
        "system" => &["system"],
        _ => &[],
    }
}

#[must_use]
pub fn analyze(name_status_z: &str) -> ImpactReport {
    let mut tokens = name_status_z.split('\0').filter(|t| !t.is_empty());
    let mut map: BTreeMap<&'static str, ComponentImpact> = BTreeMap::new();
    let mut effects: Vec<&'static str> = Vec::new();
    let mut files: usize = 0;
    while let Some(status) = tokens.next() {
        let code = status.chars().next().unwrap_or('?');
        let path = if matches!(code, 'R' | 'C') {
            let _ = tokens.next();
            tokens.next()
        } else {
            tokens.next()
        };
        let Some(path) = path else { break };
        files = files.saturating_add(1);
        let component = component_of(path);
        let slot = map.entry(component).or_insert_with(|| ComponentImpact {
            component,
            ..ComponentImpact::default()
        });
        match code {
            'A' | 'C' => slot.added = slot.added.saturating_add(1),
            'D' => slot.deleted = slot.deleted.saturating_add(1),
            'R' => slot.renamed = slot.renamed.saturating_add(1),
            _ => slot.modified = slot.modified.saturating_add(1),
        }
        for effect in effects_of(path) {
            if !effects.contains(effect) {
                effects.push(effect);
            }
        }
    }
    let mut components: Vec<ComponentImpact> = map.into_values().collect();
    components.sort_by(|a, b| b.total().cmp(&a.total()).then(a.component.cmp(b.component)));
    effects.sort_unstable();
    ImpactReport {
        files,
        components,
        effects,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn groups_by_component_and_effects() {
        let raw = "M\0server/core/app.py\0A\0client_web/src/x.tsx\0R087\0native/a.rs\0native/b.rs\0D\0README.md\0M\0native/Cargo.lock\0";
        let report = analyze(raw);
        assert_eq!(report.files, 5);
        assert_eq!(
            report.components.first().map(|c| (c.component, c.total())),
            Some(("native", 2))
        );
        assert!(report.effects.contains(&"rebuild_native"));
        assert!(report.effects.contains(&"rebuild_web"));
        assert!(report.effects.contains(&"dependencies"));
        assert!(report.effects.contains(&"restart_services"));
    }

    #[test]
    fn tolerates_truncated_input() {
        assert_eq!(analyze("M\0").files, 0);
        assert_eq!(analyze("").components.len(), 0);
    }
}
