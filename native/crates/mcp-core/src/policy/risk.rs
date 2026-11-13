use serde::{Deserialize, Serialize};

use super::config::{PolicyConfig, RuleField};
use crate::protocol::ToolSpec;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Risk {
    Info,
    Home,
    Personal,
    Files,
    Critical,
}

#[must_use]
pub fn classify(spec: &ToolSpec, honor_read_only: bool, config: &PolicyConfig) -> Risk {
    let mut risk = config.base;
    match &spec.annotations {
        None => risk = risk.max(config.unannotated),
        Some(annotations) => {
            let read_only = honor_read_only && annotations.read_only == Some(true);
            let destructive = annotations.destructive.unwrap_or(!read_only);
            let open_world = annotations.open_world.unwrap_or(true);
            if destructive {
                risk = risk.max(config.destructive);
            }
            if open_world {
                risk = risk.max(config.open_world);
            }
            if read_only && !destructive && !open_world {
                risk = config.read_only;
            }
        }
    }
    let name = spec.name.to_lowercase();
    let description = spec.description.as_deref().unwrap_or("").to_lowercase();
    for rule in &config.risk_rules {
        let hit = rule.words.iter().any(|word| {
            let word = word.to_lowercase();
            rule.fields.iter().any(|field| match field {
                RuleField::Name => name.contains(&word),
                RuleField::Description => description.contains(&word),
            })
        });
        if hit {
            risk = risk.max(rule.min_risk);
        }
    }
    risk
}
