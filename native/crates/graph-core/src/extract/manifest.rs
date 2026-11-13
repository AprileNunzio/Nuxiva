use super::util::clip;
use crate::model::{Fact, Facts, SymKind};
use crate::settings::GraphSettings;

#[must_use]
pub fn extract(text: &str, settings: &GraphSettings) -> Facts {
    let mut facts = Facts::default();
    let Ok(value) = serde_json::from_str::<serde_json::Value>(text) else {
        return facts;
    };
    let Some(object) = value.as_object() else {
        return facts;
    };
    for key in ["id", "name"] {
        if let Some(name) = object.get(key).and_then(|v| v.as_str()) {
            let name = clip(name, settings.max_name_chars);
            if !name.is_empty() && !facts.symbols.iter().any(|f| f.name == name) {
                facts.symbols.push(Fact {
                    name,
                    kind: SymKind::Entity,
                    line: 1,
                });
            }
        }
    }
    facts
}
