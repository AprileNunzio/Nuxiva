use serde::{Deserialize, Serialize};

use super::risk::Risk;
use crate::error::{McpError, McpResult};
use crate::guard::NetworkPolicy;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RuleField {
    Name,
    Description,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RiskRule {
    pub words: Vec<String>,
    pub fields: Vec<RuleField>,
    pub min_risk: Risk,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct RateConfig {
    pub per_principal_per_min: u32,
    pub per_server_per_min: u32,
    pub per_tool_per_min: u32,
    pub max_keys: usize,
}

impl Default for RateConfig {
    fn default() -> Self {
        Self {
            per_principal_per_min: 120,
            per_server_per_min: 600,
            per_tool_per_min: 60,
            max_keys: 4_096,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct PolicyConfig {
    pub base: Risk,
    pub unannotated: Risk,
    pub destructive: Risk,
    pub open_world: Risk,
    pub read_only: Risk,
    pub consent_from: Risk,
    pub taint_from: Risk,
    pub consent_ttl_ms: u64,
    pub max_result_chars: usize,
    pub allowed_image_mime: Vec<String>,
    pub risk_rules: Vec<RiskRule>,
    pub rate: RateConfig,
    pub network: NetworkPolicy,
}

impl Default for PolicyConfig {
    fn default() -> Self {
        let words = [
            "delete", "remove", "erase", "drop", "format", "kill", "exec", "shell", "sudo", "send",
            "email", "password", "secret", "token", "transfer", "payment",
        ];
        Self {
            base: Risk::Home,
            unannotated: Risk::Files,
            destructive: Risk::Files,
            open_world: Risk::Personal,
            read_only: Risk::Home,
            consent_from: Risk::Files,
            taint_from: Risk::Home,
            consent_ttl_ms: 120_000,
            max_result_chars: 6_000,
            allowed_image_mime: vec!["image/png".into(), "image/jpeg".into(), "image/webp".into()],
            risk_rules: vec![RiskRule {
                words: words.iter().map(|w| (*w).to_owned()).collect(),
                fields: vec![RuleField::Name, RuleField::Description],
                min_risk: Risk::Critical,
            }],
            rate: RateConfig::default(),
            network: NetworkPolicy::default(),
        }
    }
}

impl PolicyConfig {
    pub fn from_json(text: &str) -> McpResult<Self> {
        let config: Self = serde_json::from_str(text).map_err(|_| McpError::InvalidSettings)?;
        config.validate()?;
        Ok(config)
    }

    pub fn validate(&self) -> McpResult<()> {
        let rates = [
            self.rate.per_principal_per_min,
            self.rate.per_server_per_min,
            self.rate.per_tool_per_min,
        ];
        let rules_ok = self.risk_rules.len() <= 256
            && self
                .risk_rules
                .iter()
                .all(|r| !r.words.is_empty() && !r.fields.is_empty() && r.words.len() <= 1_024);
        let ok = (1..=1_000_000).contains(&self.max_result_chars)
            && (1..=3_600_000).contains(&self.consent_ttl_ms)
            && (1..=1_000_000).contains(&self.rate.max_keys)
            && rates.iter().all(|r| (1..=1_000_000).contains(r))
            && self.allowed_image_mime.len() <= 64
            && rules_ok;
        if ok {
            Ok(())
        } else {
            Err(McpError::InvalidSettings)
        }
    }
}
