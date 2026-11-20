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

    #[must_use]
    pub fn len(&self) -> usize {
        self.facts.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.facts.is_empty()
    }

    pub fn insert_fact(&mut self, fact: MemoryFact) {
        self.facts.insert(fact.id.clone(), fact);
    }

    pub fn consolidate(&mut self) -> usize {
        let mut to_remove: Vec<String> = Vec::new();
        let mut ids: Vec<String> = self.facts.keys().cloned().collect();
        ids.sort();
        for (i, id_a) in ids.iter().enumerate() {
            if to_remove.contains(id_a) {
                continue;
            }
            for id_b in ids.iter().skip(i.saturating_add(1)) {
                if to_remove.contains(id_b) {
                    continue;
                }
                let (merge, keep_a) = {
                    let Some(fa) = self.facts.get(id_a) else {
                        continue;
                    };
                    let Some(fb) = self.facts.get(id_b) else {
                        continue;
                    };
                    if fa.key == fb.key {
                        let val_a = fa.value.trim().to_lowercase();
                        let val_b = fb.value.trim().to_lowercase();
                        if val_a == val_b {
                            (true, fa.created_at_ms >= fb.created_at_ms)
                        } else if val_a.contains(&val_b) && val_b.len() > 10 {
                            (true, true)
                        } else if val_b.contains(&val_a) && val_a.len() > 10 {
                            (true, false)
                        } else {
                            (false, true)
                        }
                    } else {
                        (false, true)
                    }
                };
                if merge {
                    if keep_a {
                        if let Some(fb) = self.facts.get(id_b).cloned() {
                            if let Some(fa) = self.facts.get_mut(id_a) {
                                fa.hit_count = fa.hit_count.saturating_add(fb.hit_count);
                                fa.confidence = fa.confidence.max(fb.confidence);
                                fa.created_at_ms = fa.created_at_ms.max(fb.created_at_ms);
                            }
                        }
                        to_remove.push(id_b.clone());
                    } else {
                        if let Some(fa) = self.facts.get(id_a).cloned() {
                            if let Some(fb) = self.facts.get_mut(id_b) {
                                fb.hit_count = fb.hit_count.saturating_add(fa.hit_count);
                                fb.confidence = fb.confidence.max(fa.confidence);
                                fb.created_at_ms = fb.created_at_ms.max(fa.created_at_ms);
                            }
                        }
                        to_remove.push(id_a.clone());
                        break;
                    }
                }
            }
        }
        let count = to_remove.len();
        for id in to_remove {
            self.facts.remove(&id);
        }
        count
    }

    #[allow(clippy::cast_precision_loss)]
    pub fn prune(&mut self, now_ms: u64, max_facts: usize, half_life_ms: u64) -> usize {
        let hl = half_life_ms.max(1) as f32;
        let mut scored: Vec<(String, f32, bool)> = Vec::new();
        for fact in self.facts.values() {
            let immune = matches!(
                fact.key.as_str(),
                "user_name" | "user_preference" | "explicit_memory" | "project_focus"
            ) && fact.confidence >= 0.85;
            let delta = now_ms.saturating_sub(fact.created_at_ms) as f32;
            let decay = 0.5f32.powf(delta / hl);
            let score = if immune {
                1000.0 + fact.confidence
            } else {
                (fact.hit_count as f32) * fact.confidence * decay
            };
            scored.push((fact.id.clone(), score, immune));
        }

        let mut evicted = 0usize;
        let mut to_remove: Vec<String> = Vec::new();
        for (id, score, immune) in &scored {
            if !immune && *score < 0.05 {
                to_remove.push(id.clone());
            }
        }
        for id in &to_remove {
            self.facts.remove(id);
            evicted = evicted.saturating_add(1);
        }

        if self.facts.len() > max_facts {
            let mut remaining: Vec<(String, f32)> = self
                .facts
                .values()
                .map(|f| {
                    let immune = matches!(
                        f.key.as_str(),
                        "user_name" | "user_preference" | "explicit_memory" | "project_focus"
                    ) && f.confidence >= 0.85;
                    let delta = now_ms.saturating_sub(f.created_at_ms) as f32;
                    let decay = 0.5f32.powf(delta / hl);
                    let score = if immune {
                        1000.0 + f.confidence
                    } else {
                        (f.hit_count as f32) * f.confidence * decay
                    };
                    (f.id.clone(), score)
                })
                .collect();
            remaining.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));
            let excess = self.facts.len().saturating_sub(max_facts);
            for (id, _) in remaining.into_iter().take(excess) {
                self.facts.remove(&id);
                evicted = evicted.saturating_add(1);
            }
        }
        evicted
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::panic, clippy::indexing_slicing)]
mod tests {
    use super::*;

    #[test]
    fn test_vault_consolidation_merges_duplicates() {
        let mut vault = CrossMemoryVault::new();
        vault.learn_statement(
            "Preferisco risposte molto concise e dirette",
            MemorySource::WrittenChat,
            100,
        );
        vault.learn_statement(
            "Preferisco risposte molto concise e dirette",
            MemorySource::VoiceSpeech,
            200,
        );
        assert_eq!(vault.len(), 2);
        let merged = vault.consolidate();
        assert_eq!(merged, 1);
        assert_eq!(vault.len(), 1);
        let facts = vault.all_facts();
        assert_eq!(facts[0].hit_count, 2);
        assert_eq!(facts[0].created_at_ms, 200);
    }

    #[test]
    fn test_vault_prune_removes_expired_preserves_immune() {
        let mut vault = CrossMemoryVault::new();
        vault.learn_statement("Il mio nome è Alessandro", MemorySource::WrittenChat, 100);
        vault.learn_statement(
            "Oggi a pranzo ho mangiato una mela",
            MemorySource::WrittenChat,
            100,
        );
        assert_eq!(vault.len(), 2);
        let evicted = vault.prune(10_000_000, 10, 1000);
        assert_eq!(evicted, 1);
        assert_eq!(vault.len(), 1);
        let facts = vault.all_facts();
        assert_eq!(facts[0].key, "user_name");
    }
}
