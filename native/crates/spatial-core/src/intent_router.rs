use std::collections::HashMap;

#[derive(Debug, Default)]
pub struct IntentRouter {
    intent_registry: HashMap<&'static str, &'static str>,
}

impl IntentRouter {
    #[must_use]
    pub fn new() -> Self {
        let mut registry = HashMap::new();
        registry.insert("chess", "app.nuxiva.chess");
        registry.insert("scacchi", "app.nuxiva.chess");
        registry.insert("cad3d", "app.nuxiva.cad3d");
        registry.insert("3d", "app.nuxiva.cad3d");
        registry.insert("whisper", "app.nuxiva.whisper");
        registry.insert("silent", "app.nuxiva.whisper");
        registry.insert("idle", "app.nuxiva.idle");
        registry.insert("home", "app.nuxiva.idle");

        Self {
            intent_registry: registry,
        }
    }

    pub fn register(&mut self, trigger: &'static str, context_id: &'static str) {
        self.intent_registry.insert(trigger, context_id);
    }

    #[must_use]
    pub fn resolve_intent(&self, raw_utterance: &str) -> Option<&'static str> {
        let normalized = raw_utterance.trim().to_lowercase();
        for (pattern, context_id) in &self.intent_registry {
            if normalized.contains(pattern) {
                return Some(*context_id);
            }
        }
        None
    }
}
