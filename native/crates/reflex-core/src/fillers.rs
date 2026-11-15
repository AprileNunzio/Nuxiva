#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::RwLock;

use crate::acoustic::DeliveryStyle;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TaskDomain {
    ThinkingComplex,
    ActionDirect,
    SearchWeb,
    General,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ReflexUtterance {
    pub text: String,
    pub language: String,
    pub delivery_style: DeliveryStyle,
    pub volume_scale: f32,
    pub semantic_token: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LexiconCatalog {
    // Map: lang -> domain_key -> style_key -> Vec<template_string>
    entries: HashMap<String, HashMap<String, HashMap<String, Vec<String>>>>,
}

impl Default for LexiconCatalog {
    fn default() -> Self {
        Self::new()
    }
}

impl LexiconCatalog {
    #[must_use]
    pub fn new() -> Self {
        Self {
            entries: HashMap::new(),
        }
    }

    pub fn register(&mut self, lang: &str, domain: &str, style: &str, template: &str) {
        let lang_map = self.entries.entry(lang.to_owned()).or_default();
        let domain_map = lang_map.entry(domain.to_owned()).or_default();
        let style_list = domain_map.entry(style.to_owned()).or_default();
        if !style_list.contains(&template.to_owned()) {
            style_list.push(template.to_owned());
        }
    }

    #[must_use]
    pub fn resolve(&self, lang: &str, domain: &str, style: &str, seed: usize) -> Option<String> {
        // Try requested language first, fallback to English or generic
        let candidates = self
            .entries
            .get(lang)
            .and_then(|d| d.get(domain))
            .and_then(|s| s.get(style))
            .or_else(|| {
                self.entries
                    .get("en")
                    .and_then(|d| d.get(domain))
                    .and_then(|s| s.get(style))
            })?;

        if candidates.is_empty() {
            return None;
        }

        let idx = seed.checked_rem(candidates.len()).unwrap_or(0);
        candidates.get(idx).cloned()
    }
}

#[derive(Debug)]
pub struct FillerEngine {
    catalog: RwLock<LexiconCatalog>,
}

impl Default for FillerEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl FillerEngine {
    #[must_use]
    pub fn new() -> Self {
        Self {
            catalog: RwLock::new(LexiconCatalog::new()),
        }
    }

    pub fn load_catalog(&self, catalog: LexiconCatalog) {
        if let Ok(mut lock) = self.catalog.write() {
            *lock = catalog;
        }
    }

    pub fn register_template(&self, lang: &str, domain: &str, style: &str, template: &str) {
        if let Ok(mut lock) = self.catalog.write() {
            lock.register(lang, domain, style, template);
        }
    }

    fn domain_key(domain: TaskDomain) -> &'static str {
        match domain {
            TaskDomain::ThinkingComplex => "thinking",
            TaskDomain::ActionDirect => "action",
            TaskDomain::SearchWeb => "search",
            TaskDomain::General => "general",
        }
    }

    fn style_key(style: DeliveryStyle) -> &'static str {
        match style {
            DeliveryStyle::Normal => "normal",
            DeliveryStyle::Whisper => "whisper",
            DeliveryStyle::NightDiscreet => "night",
        }
    }

    fn hash_query(query: &str) -> usize {
        let mut h: u64 = 0xcbf2_9ce4_8422_2325;
        for b in query.as_bytes() {
            h = (h ^ u64::from(*b)).wrapping_mul(0x0100_0000_01b3);
        }
        usize::try_from(h % 997).unwrap_or(0)
    }

    #[must_use]
    pub fn select_utterance(
        &self,
        query: &str,
        lang: &str,
        style: DeliveryStyle,
        domain: TaskDomain,
    ) -> ReflexUtterance {
        let domain_str = Self::domain_key(domain);
        let style_str = Self::style_key(style);
        let seed = Self::hash_query(query);

        let volume_scale = match style {
            DeliveryStyle::Whisper => 0.35,
            DeliveryStyle::NightDiscreet => 0.55,
            DeliveryStyle::Normal => 1.0,
        };

        let resolved_text = self
            .catalog
            .read()
            .ok()
            .and_then(|c| c.resolve(lang, domain_str, style_str, seed))
            .unwrap_or_else(|| {
                // Algorithmic abstract token without hardcoded language assumptions
                format!("ref:{lang}:{domain_str}:{style_str}")
            });

        ReflexUtterance {
            text: resolved_text,
            language: lang.to_owned(),
            delivery_style: style,
            volume_scale,
            semantic_token: format!("{domain_str}_{style_str}"),
        }
    }
}
