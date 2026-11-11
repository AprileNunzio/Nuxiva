use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SubappManifest {
    pub id: String,
    pub name: String,
    pub parent: String,
    pub version: String,
    pub category: String,
    pub capabilities: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MacroAppManifest {
    pub id: String,
    pub name: String,
    pub category: String,
    pub icon: String,
    pub subapps: Vec<SubappManifest>,
}

#[derive(Debug, Default)]
pub struct SubappRegistry {
    entries: HashMap<String, SubappManifest>,
}

impl SubappRegistry {
    pub fn new() -> Self {
        Self {
            entries: HashMap::new(),
        }
    }

    pub fn sanitize_id(raw: &str) -> Option<String> {
        let trimmed = raw.trim();
        if trimmed.is_empty() || trimmed.len() > 64 {
            return None;
        }
        if !trimmed.chars().all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-') {
            return None;
        }
        Some(trimmed.to_ascii_lowercase())
    }

    pub fn register(&mut self, manifest: SubappManifest) -> Result<(), &'static str> {
        let valid_id = Self::sanitize_id(&manifest.id).ok_or("invalid_id")?;
        let valid_parent = Self::sanitize_id(&manifest.parent).ok_or("invalid_parent")?;

        let mut sanitized = manifest;
        sanitized.id = valid_id.clone();
        sanitized.parent = valid_parent;

        self.entries.insert(valid_id, sanitized);
        Ok(())
    }

    pub fn unregister(&mut self, id: &str) -> Option<SubappManifest> {
        self.entries.remove(id)
    }

    pub fn get(&self, id: &str) -> Option<&SubappManifest> {
        self.entries.get(id)
    }

    pub fn list_by_parent(&self, parent: &str) -> Vec<SubappManifest> {
        self.entries
            .values()
            .filter(|sub| sub.parent == parent)
            .cloned()
            .collect()
    }

    pub fn list_all(&self) -> Vec<SubappManifest> {
        self.entries.values().cloned().collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sanitize_id() {
        assert_eq!(SubappRegistry::sanitize_id("  Tris  "), Some("tris".to_string()));
        assert_eq!(SubappRegistry::sanitize_id("scacchi-3d"), Some("scacchi-3d".to_string()));
        assert_eq!(SubappRegistry::sanitize_id("bad/path"), None);
        assert_eq!(SubappRegistry::sanitize_id(""), None);
    }

    #[test]
    fn test_subapp_registration_and_query() {
        let mut reg = SubappRegistry::new();
        let tris = SubappManifest {
            id: "tris".to_string(),
            name: "Tris".to_string(),
            parent: "giochi".to_string(),
            version: "1.0.0".to_string(),
            category: "games".to_string(),
            capabilities: vec![],
        };
        let scacchi = SubappManifest {
            id: "scacchi".to_string(),
            name: "Scacchi".to_string(),
            parent: "giochi".to_string(),
            version: "1.0.0".to_string(),
            category: "games".to_string(),
            capabilities: vec![],
        };
        let cam = SubappManifest {
            id: "telecamere".to_string(),
            name: "Telecamere".to_string(),
            parent: "videosorveglianza".to_string(),
            version: "1.0.0".to_string(),
            category: "security".to_string(),
            capabilities: vec!["camera".to_string()],
        };

        assert!(reg.register(tris).is_ok());
        assert!(reg.register(scacchi).is_ok());
        assert!(reg.register(cam).is_ok());

        assert_eq!(reg.list_by_parent("giochi").len(), 2);
        assert_eq!(reg.list_by_parent("videosorveglianza").len(), 1);
        assert_eq!(reg.list_all().len(), 3);
        assert!(reg.get("tris").is_some());

        assert!(reg.unregister("tris").is_some());
        assert_eq!(reg.list_by_parent("giochi").len(), 1);
    }
}

