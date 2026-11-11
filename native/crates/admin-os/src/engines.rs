use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EngineFamily {
    Reasoning,
    SpeechRecognition,
    MusicRecognition,
    Vision,
}

impl EngineFamily {
    #[must_use]
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Reasoning => "reasoning",
            Self::SpeechRecognition => "speech_recognition",
            Self::MusicRecognition => "music_recognition",
            Self::Vision => "vision",
        }
    }

    #[must_use]
    pub fn parse_str(raw: &str) -> Option<Self> {
        match raw.trim().to_ascii_lowercase().as_str() {
            "reasoning" => Some(Self::Reasoning),
            "speech_recognition" | "speech" | "voice" => Some(Self::SpeechRecognition),
            "music_recognition" | "music" | "audio_fingerprint" => Some(Self::MusicRecognition),
            "vision" | "face_recognition" => Some(Self::Vision),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EngineOption {
    pub id: String,
    pub option_type: String,
    pub default_value: String,
    pub label_key: String,
    pub desc_key: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EngineManifest {
    pub id: String,
    pub name: String,
    pub version: String,
    pub family: EngineFamily,
    #[serde(default)]
    pub author: String,
    #[serde(default)]
    pub entrypoint: String,
    #[serde(default)]
    pub capabilities: Vec<String>,
    #[serde(default)]
    pub options: Vec<EngineOption>,
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct EngineRegistry {
    engines: HashMap<String, EngineManifest>,
    active_engines: HashMap<EngineFamily, String>,
}

impl EngineRegistry {
    #[must_use]
    pub fn new() -> Self {
        Self {
            engines: HashMap::new(),
            active_engines: HashMap::new(),
        }
    }

    #[must_use]
    pub fn sanitize_id(raw: &str) -> Option<String> {
        let trimmed = raw.trim();
        if trimmed.is_empty() || trimmed.len() > 64 {
            return None;
        }
        if trimmed.starts_with('.')
            || trimmed.contains("..")
            || trimmed.contains('/')
            || trimmed.contains('\\')
        {
            return None;
        }
        let valid = trimmed
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_');
        if valid {
            Some(trimmed.to_ascii_lowercase())
        } else {
            None
        }
    }

    pub fn register(&mut self, manifest: EngineManifest) -> Result<(), String> {
        let Some(safe_id) = Self::sanitize_id(&manifest.id) else {
            return Err(format!(
                "Invalid engine identifier: {raw_id}",
                raw_id = manifest.id
            ));
        };

        if self.engines.contains_key(&safe_id) {
            return Err(format!("Engine '{safe_id}' already registered"));
        }

        let family = manifest.family;
        let mut sanitized = manifest;
        sanitized.id.clone_from(&safe_id);

        self.active_engines
            .entry(family)
            .or_insert_with(|| safe_id.clone());

        self.engines.insert(safe_id, sanitized);
        Ok(())
    }

    pub fn set_active(&mut self, family: EngineFamily, engine_id: &str) -> Result<(), String> {
        let Some(safe_id) = Self::sanitize_id(engine_id) else {
            return Err(format!("Invalid engine identifier: {engine_id}"));
        };

        match self.engines.get(&safe_id) {
            Some(engine) => {
                if engine.family != family {
                    return Err(format!(
                        "Engine '{safe_id}' does not belong to family {family:?}"
                    ));
                }
                self.active_engines.insert(family, safe_id);
                Ok(())
            }
            None => Err(format!("Engine '{safe_id}' not found")),
        }
    }

    #[must_use]
    pub fn get_active(&self, family: &EngineFamily) -> Option<&EngineManifest> {
        let active_id = self.active_engines.get(family)?;
        self.engines.get(active_id)
    }

    #[must_use]
    pub fn get_engine(&self, id: &str) -> Option<&EngineManifest> {
        let safe_id = Self::sanitize_id(id)?;
        self.engines.get(&safe_id)
    }

    #[must_use]
    pub fn list_by_family(&self, family: &EngineFamily) -> Vec<&EngineManifest> {
        self.engines
            .values()
            .filter(|e| &e.family == family)
            .collect()
    }

    #[must_use]
    pub fn total_engines(&self) -> usize {
        self.engines.len()
    }

    pub fn scan_directory(&mut self, root: &Path) -> Result<usize, String> {
        if !root.is_dir() {
            return Ok(0);
        }

        let mut discovered = 0usize;
        let entries = match fs::read_dir(root) {
            Ok(iter) => iter,
            Err(e) => return Err(e.to_string()),
        };

        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                let manifest_path = path.join("manifest.json");
                if manifest_path.is_file() {
                    if let Ok(content) = fs::read_to_string(&manifest_path) {
                        if let Ok(manifest) = serde_json::from_str::<EngineManifest>(&content) {
                            if self.register(manifest).is_ok() {
                                discovered = discovered.saturating_add(1);
                            }
                        }
                    }
                }
                if let Ok(sub_count) = self.scan_directory(&path) {
                    discovered = discovered.saturating_add(sub_count);
                }
            }
        }

        Ok(discovered)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_family_parsing() {
        assert_eq!(
            EngineFamily::parse_str("reasoning"),
            Some(EngineFamily::Reasoning)
        );
        assert_eq!(
            EngineFamily::parse_str("speech"),
            Some(EngineFamily::SpeechRecognition)
        );
        assert_eq!(
            EngineFamily::parse_str("music"),
            Some(EngineFamily::MusicRecognition)
        );
        assert_eq!(
            EngineFamily::parse_str("vision"),
            Some(EngineFamily::Vision)
        );
        assert_eq!(EngineFamily::parse_str("invalid_family"), None);
    }

    #[test]
    fn test_register_and_set_active() {
        let mut registry = EngineRegistry::new();
        let m1 = EngineManifest {
            id: "tree_of_thought".to_string(),
            name: "Tree of Thought".to_string(),
            version: "1.0.0".to_string(),
            family: EngineFamily::Reasoning,
            author: "Nuxiva".to_string(),
            entrypoint: "engine.wasm".to_string(),
            capabilities: vec!["reasoning".to_string()],
            options: vec![],
        };
        let m2 = EngineManifest {
            id: "react_autonomous".to_string(),
            name: "ReAct Autonomous".to_string(),
            version: "1.0.0".to_string(),
            family: EngineFamily::Reasoning,
            author: "Nuxiva".to_string(),
            entrypoint: "engine.wasm".to_string(),
            capabilities: vec!["reasoning".to_string()],
            options: vec![],
        };

        assert!(registry.register(m1).is_ok());
        assert!(registry.register(m2).is_ok());
        assert_eq!(registry.total_engines(), 2);

        let active1 = registry.get_active(&EngineFamily::Reasoning);
        assert!(active1.is_some());
        if let Some(active) = active1 {
            assert_eq!(active.id, "tree_of_thought");
        }

        assert!(
            registry
                .set_active(EngineFamily::Reasoning, "react_autonomous")
                .is_ok()
        );
        let active2 = registry.get_active(&EngineFamily::Reasoning);
        assert!(active2.is_some());
        if let Some(active) = active2 {
            assert_eq!(active.id, "react_autonomous");
        }
    }
}
