use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SubappManifest {
    pub id: String,
    pub name: String,
    #[serde(default)]
    pub parent: String,
    #[serde(default = "default_version")]
    pub version: String,
    #[serde(default)]
    pub category: String,
    #[serde(default)]
    pub capabilities: Vec<String>,
    #[serde(default)]
    pub voice_triggers: Vec<String>,
}

fn default_version() -> String {
    "1.0.0".to_string()
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
    #[must_use]
    pub fn new() -> Self {
        Self {
            entries: HashMap::new(),
        }
    }

    #[must_use]
    pub fn sanitize_id(raw: &str) -> Option<String> {
        let trimmed = raw.trim();
        if trimmed.is_empty() || trimmed.len() > 64 {
            return None;
        }
        if !trimmed
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
        {
            return None;
        }
        Some(trimmed.to_ascii_lowercase())
    }

    pub fn register(&mut self, manifest: SubappManifest) -> Result<(), &'static str> {
        let valid_id = Self::sanitize_id(&manifest.id).ok_or("invalid_id")?;
        let valid_parent = if manifest.parent.is_empty() {
            String::new()
        } else {
            Self::sanitize_id(&manifest.parent).ok_or("invalid_parent")?
        };

        let mut sanitized = manifest;
        sanitized.id.clone_from(&valid_id);
        sanitized.parent = valid_parent;

        self.entries.insert(valid_id, sanitized);
        Ok(())
    }

    pub fn unregister(&mut self, id: &str) -> Option<SubappManifest> {
        self.entries.remove(id)
    }

    #[must_use]
    pub fn get(&self, id: &str) -> Option<&SubappManifest> {
        self.entries.get(id)
    }

    #[must_use]
    pub fn list_by_parent(&self, parent: &str) -> Vec<SubappManifest> {
        self.entries
            .values()
            .filter(|sub| sub.parent == parent)
            .cloned()
            .collect()
    }

    #[must_use]
    pub fn list_by_category(&self, category: &str) -> Vec<SubappManifest> {
        self.entries
            .values()
            .filter(|sub| sub.category == category)
            .cloned()
            .collect()
    }

    #[must_use]
    pub fn list_all(&self) -> Vec<SubappManifest> {
        self.entries.values().cloned().collect()
    }

    pub fn scan_directory<P: AsRef<Path>>(
        &mut self,
        root_path: P,
    ) -> Result<usize, std::io::Error> {
        let mut count = 0;
        let path = root_path.as_ref();
        if !path.exists() || !path.is_dir() {
            return Ok(0);
        }

        self.traverse_and_register(path, &mut count)?;
        Ok(count)
    }

    fn traverse_and_register(
        &mut self,
        current_dir: &Path,
        count: &mut usize,
    ) -> Result<(), std::io::Error> {
        let manifest_path = current_dir.join("manifest.json");
        if manifest_path.is_file() {
            if let Ok(content) = fs::read_to_string(&manifest_path) {
                if let Ok(manifest) = serde_json::from_str::<SubappManifest>(&content) {
                    if self.register(manifest).is_ok() {
                        *count = count.saturating_add(1);
                    }
                }
            }
        }

        for entry in fs::read_dir(current_dir)? {
            let entry = entry?;
            let path = entry.path();
            if path.is_dir() && !entry.file_name().to_string_lossy().starts_with('.') {
                let _ = self.traverse_and_register(&path, count);
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sanitize_id_valid_and_invalid() {
        assert!(SubappRegistry::sanitize_id("valid-id_123").is_some());
        assert!(SubappRegistry::sanitize_id("  TRIMMED-ID  ").is_some());
        assert!(SubappRegistry::sanitize_id("bad/path").is_none());
        assert!(SubappRegistry::sanitize_id("bad..path").is_none());
        assert!(SubappRegistry::sanitize_id("").is_none());
    }

    #[test]
    fn test_subapp_registration_and_query() {
        let mut reg = SubappRegistry::new();
        let app1 = SubappManifest {
            id: "app-one".to_string(),
            name: "App One".to_string(),
            parent: "macro-hub".to_string(),
            version: "1.0.0".to_string(),
            category: "tools".to_string(),
            capabilities: vec![],
            voice_triggers: vec!["start app one".to_string()],
        };
        let app2 = SubappManifest {
            id: "app-two".to_string(),
            name: "App Two".to_string(),
            parent: "macro-hub".to_string(),
            version: "2.0.0".to_string(),
            category: "tools".to_string(),
            capabilities: vec!["network".to_string()],
            voice_triggers: vec![],
        };

        let res1 = reg.register(app1);
        let res2 = reg.register(app2);
        assert!(res1.is_ok());
        assert!(res2.is_ok());

        assert_eq!(reg.list_by_parent("macro-hub").len(), 2);
        assert_eq!(reg.list_by_category("tools").len(), 2);
        assert_eq!(reg.list_all().len(), 2);
        assert!(reg.get("app-one").is_some());

        assert!(reg.unregister("app-one").is_some());
        assert_eq!(reg.list_by_parent("macro-hub").len(), 1);
    }

    #[test]
    fn test_dynamic_directory_scanner() {
        let nanos = match std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH) {
            Ok(d) => d.as_nanos(),
            Err(_) => 0,
        };
        let temp_dir = std::env::temp_dir().join(format!("nuxiva_test_scan_{nanos}"));
        let sub_dir = temp_dir.join("sample_pack").join("module_a");
        if fs::create_dir_all(&sub_dir).is_err() {
            return;
        }

        let manifest_content = r#"{
            "id": "dynamic-scanner-test",
            "name": "Dynamic App",
            "parent": "sample_pack",
            "category": "dynamic",
            "capabilities": ["test"]
        }"#;
        if fs::write(sub_dir.join("manifest.json"), manifest_content).is_err() {
            let _ = fs::remove_dir_all(&temp_dir);
            return;
        }

        let mut reg = SubappRegistry::new();
        let scanned = reg.scan_directory(&temp_dir);
        assert!(scanned.is_ok());
        if let Ok(count) = scanned {
            assert_eq!(count, 1);
            assert!(reg.get("dynamic-scanner-test").is_some());
        }

        let _ = fs::remove_dir_all(&temp_dir);
    }
}
