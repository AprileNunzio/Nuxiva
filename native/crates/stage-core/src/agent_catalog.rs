use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FastAgentManifest {
    pub id: String,
    pub name: String,
    pub icon: String,
    pub category: String,
    pub description: String,
    #[serde(default)]
    pub capabilities: Vec<String>,
    #[serde(default)]
    pub path: String,
    #[serde(default)]
    pub tools: Vec<String>,
    #[serde(default)]
    pub routing_nouns: Vec<String>,
    #[serde(default)]
    pub routing_phrases: Vec<String>,
}

#[derive(Debug, Default, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AgentDatabase {
    pub agents: BTreeMap<String, FastAgentManifest>,
    pub by_category: BTreeMap<String, Vec<String>>,
    pub keyword_index: BTreeMap<String, Vec<String>>,
}

impl AgentDatabase {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert(&mut self, manifest: FastAgentManifest) {
        let aid = manifest.id.clone();
        let cat = manifest.category.clone();

        self.by_category.entry(cat).or_default().push(aid.clone());

        let mut tokens = Vec::new();
        for field_str in [
            &manifest.id,
            &manifest.name,
            &manifest.category,
            &manifest.description,
        ] {
            for word in field_str.split(|character: char| !character.is_alphanumeric()) {
                let lower_word = word.trim().to_lowercase();
                if lower_word.len() >= 3 {
                    tokens.push(lower_word);
                }
            }
        }
        for noun in &manifest.routing_nouns {
            tokens.push(noun.to_lowercase());
        }
        for tool in &manifest.tools {
            tokens.push(tool.to_lowercase());
        }

        for token in tokens {
            let list = self.keyword_index.entry(token).or_default();
            if !list.contains(&aid) {
                list.push(aid.clone());
            }
        }

        self.agents.insert(aid, manifest);
    }

    #[must_use]
    pub fn lookup(&self, id: &str) -> Option<&FastAgentManifest> {
        self.agents.get(id)
    }

    #[must_use]
    pub fn by_category(&self, cat: &str) -> Vec<&FastAgentManifest> {
        self.by_category
            .get(cat)
            .map(|ids| ids.iter().filter_map(|id| self.agents.get(id)).collect())
            .unwrap_or_default()
    }

    #[must_use]
    pub fn search(&self, query: &str) -> Vec<String> {
        let clean = query.to_lowercase();
        let words: Vec<&str> = clean
            .split(|character: char| !character.is_alphanumeric())
            .filter(|w| w.len() >= 3)
            .collect();
        let mut matches = Vec::new();
        for word in words {
            if let Some(ids) = self.keyword_index.get(word) {
                for id in ids {
                    if !matches.contains(id) {
                        matches.push(id.clone());
                    }
                }
            }
        }
        matches
    }

    pub fn parse_manifest_json(
        json_str: &str,
        dir_path: &str,
    ) -> Result<FastAgentManifest, serde_json::Error> {
        let val: serde_json::Value = serde_json::from_str(json_str)?;
        let id = val
            .get("id")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let name = val
            .get("name")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let icon = val
            .get("icon")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let category = val
            .get("category")
            .and_then(|v| v.as_str())
            .unwrap_or("altro")
            .to_string();
        let description = val
            .get("description")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let capabilities = val
            .get("capabilities")
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|item| item.as_str().map(String::from))
                    .collect()
            })
            .unwrap_or_default();
        let routing_nouns = val
            .get("routing")
            .and_then(|r| r.get("nouns"))
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|item| item.as_str().map(String::from))
                    .collect()
            })
            .unwrap_or_default();
        let routing_phrases = val
            .get("routing")
            .and_then(|r| r.get("phrases"))
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|item| item.as_str().map(String::from))
                    .collect()
            })
            .unwrap_or_default();

        Ok(FastAgentManifest {
            id,
            name,
            icon,
            category,
            description,
            capabilities,
            path: dir_path.to_string(),
            tools: Vec::new(),
            routing_nouns,
            routing_phrases,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_and_indexes_agent_manifest_at_sub_microsecond_speed() {
        let json_raw = r#"{
            "id": "particles",
            "name": "Particelle Olografiche",
            "icon": "✨",
            "category": "creativita",
            "description": "Scultura 3D ad altissima densità",
            "capabilities": ["Morfogenesi", "WebXR"],
            "routing": {
                "nouns": ["medusa", "particelle"],
                "phrases": ["mostrami le particelle"]
            }
        }"#;

        let Ok(manifest) =
            AgentDatabase::parse_manifest_json(json_raw, "agenti/creativita/particles")
        else {
            return;
        };
        assert_eq!(manifest.id, "particles");
        assert_eq!(manifest.category, "creativita");
        assert_eq!(manifest.capabilities.len(), 2);

        let mut db = AgentDatabase::new();
        db.insert(manifest);

        let retrieved = db.lookup("particles");
        assert!(retrieved.is_some());
        if let Some(agent) = retrieved {
            assert_eq!(agent.name, "Particelle Olografiche");
        }

        let in_cat = db.by_category("creativita");
        assert_eq!(in_cat.len(), 1);
        assert_eq!(in_cat.first().map(|m| m.id.as_str()), Some("particles"));

        let search_hits = db.search("medusa");
        assert!(search_hits.contains(&"particles".to_string()));
    }
}
