use crate::types::{MemoryFact, MemorySource};
use std::collections::HashMap;

#[derive(Debug, Clone, Default)]
pub struct CrossMemoryVault {
    facts: HashMap<String, MemoryFact>,
}

impl CrossMemoryVault {
    #[must_use]
    pub fn new() -> Self {
        Self {
            facts: HashMap::new(),
        }
    }

    pub fn learn_statement(
        &mut self,
        text: &str,
        source: MemorySource,
        timestamp_ms: u64,
    ) -> Option<MemoryFact> {
        let trimmed = text.trim();
        if trimmed.len() < 5 {
            return None;
        }

        let lower = trimmed.to_lowercase();
        let key = if lower.contains("mi chiamo ") || lower.contains("il mio nome è ") {
            "user_name"
        } else if lower.contains("preferisco ") || lower.contains("mi piace ") {
            "user_preference"
        } else if lower.contains("lavoro su ") || lower.contains("il mio lavoro ") {
            "user_occupation"
        } else if lower.contains("progetto ") || lower.contains("obiettiv") {
            "project_focus"
        } else if lower.contains("ricorda che ") || lower.contains("ricordati che ") {
            "explicit_memory"
        } else if source == MemorySource::VoiceSpeech {
            "voice_interaction"
        } else {
            "general_context"
        };

        let fact_id = format!("mem_{key}_{timestamp_ms:x}");
        let fact = MemoryFact {
            id: fact_id.clone(),
            key: key.to_string(),
            value: trimmed.to_string(),
            confidence: match source {
                MemorySource::VoiceSpeech => 0.95,
                MemorySource::WrittenChat => 0.90,
                MemorySource::SmbDocument => 0.85,
            },
            source,
            created_at_ms: timestamp_ms,
            hit_count: 1,
        };

        self.facts.insert(fact_id, fact.clone());
        Some(fact)
    }

    #[must_use]
    pub fn recall_relevant(&mut self, query: &str, limit: usize) -> Vec<MemoryFact> {
        let terms: Vec<String> = query
            .split_whitespace()
            .map(str::to_lowercase)
            .filter(|w| w.len() > 3)
            .collect();

        if terms.is_empty() {
            let mut all: Vec<MemoryFact> = self.facts.values().cloned().collect();
            all.sort_by_key(|a| std::cmp::Reverse(a.created_at_ms));
            all.truncate(limit);
            return all;
        }

        let mut scored: Vec<(u32, MemoryFact)> = Vec::new();

        for fact in self.facts.values_mut() {
            let val_lower = fact.value.to_lowercase();
            let mut score: u32 = 0;

            for term in &terms {
                if val_lower.contains(term) {
                    score = score.saturating_add(10);
                }
            }

            if score > 0 {
                fact.hit_count = fact.hit_count.saturating_add(1);
                scored.push((score, fact.clone()));
            }
        }

        scored.sort_by_key(|a| std::cmp::Reverse(a.0));
        scored.into_iter().take(limit).map(|(_, f)| f).collect()
    }

    #[must_use]
    pub fn build_system_injection(&mut self, query: &str) -> Option<String> {
        let recalls = self.recall_relevant(query, 5);
        if recalls.is_empty() {
            return None;
        }

        let mut lines = Vec::new();
        lines.push("RECALLED_CROSS_SESSION_MEMORY:".to_string());
        for fact in recalls {
            let src_str = match fact.source {
                MemorySource::VoiceSpeech => "spoken_by_voice",
                MemorySource::WrittenChat => "written_in_chat",
                MemorySource::SmbDocument => "indexed_from_smb",
            };
            lines.push(format!("- [{src_str}] {}: {}", fact.key, fact.value));
        }

        Some(lines.join("\n"))
    }

    #[must_use]
    pub fn all_facts(&self) -> Vec<MemoryFact> {
        let mut list: Vec<MemoryFact> = self.facts.values().cloned().collect();
        list.sort_by_key(|a| std::cmp::Reverse(a.created_at_ms));
        list
    }
}
