use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum TriggerKind {
    Cron(String),
    Event(String),
    Threshold { metric: String, threshold: u64 },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ActionKind {
    Notify { message: String, level: String },
    ToggleService { service_id: String, enable: bool },
    ExecuteScript { script_name: String },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AutomationRule {
    pub id: String,
    pub name: String,
    pub description: String,
    pub trigger: TriggerKind,
    pub actions: Vec<ActionKind>,
    pub enabled: bool,
    pub run_count: u64,
    pub last_status: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum LawTier {
    Fixed,
    Custom,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LawRule {
    pub id: String,
    pub tier: LawTier,
    pub index: u32,
    pub title: String,
    pub body: String,
    pub active: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AutomationsSummary {
    pub total_automations: usize,
    pub enabled_automations: usize,
    pub fixed_laws: usize,
    pub custom_laws: usize,
    pub total_runs: u64,
}

#[derive(Debug, Clone, Default)]
pub struct AutomationEngine {
    rules: Vec<AutomationRule>,
    laws: Vec<LawRule>,
}

impl AutomationEngine {
    #[must_use]
    pub fn new() -> Self {
        Self {
            rules: Vec::new(),
            laws: Vec::new(),
        }
    }

    pub fn register_rule(&mut self, rule: AutomationRule) {
        if let Some(pos) = self.rules.iter().position(|r| r.id == rule.id) {
            if let Some(existing) = self.rules.get_mut(pos) {
                *existing = rule;
            }
        } else {
            self.rules.push(rule);
        }
    }

    pub fn remove_rule(&mut self, id: &str) -> bool {
        let initial_len = self.rules.len();
        self.rules.retain(|r| r.id != id);
        self.rules.len() < initial_len
    }

    pub fn toggle_rule(&mut self, id: &str, enabled: bool) -> bool {
        if let Some(rule) = self.rules.iter_mut().find(|r| r.id == id) {
            rule.enabled = enabled;
            true
        } else {
            false
        }
    }

    pub fn register_law(&mut self, law: LawRule) {
        if let Some(pos) = self.laws.iter().position(|l| l.id == law.id) {
            if let Some(existing) = self.laws.get_mut(pos) {
                *existing = law;
            }
        } else {
            self.laws.push(law);
        }
    }

    pub fn remove_custom_law(&mut self, id: &str) -> Result<(), &'static str> {
        if let Some(pos) = self.laws.iter().position(|l| l.id == id) {
            if let Some(law) = self.laws.get(pos) {
                if law.tier == LawTier::Fixed {
                    return Err("cannot_remove_fixed_law");
                }
            }
            self.laws.remove(pos);
            Ok(())
        } else {
            Err("law_not_found")
        }
    }

    #[must_use]
    pub fn match_event_trigger(&self, event_topic: &str) -> Vec<String> {
        self.rules
            .iter()
            .filter(|r| r.enabled)
            .filter_map(|r| match &r.trigger {
                TriggerKind::Event(t) if t == event_topic => Some(r.id.clone()),
                _ => None,
            })
            .collect()
    }

    pub fn record_execution(&mut self, id: &str, status: &str) -> bool {
        if let Some(rule) = self.rules.iter_mut().find(|r| r.id == id) {
            rule.run_count = rule.run_count.saturating_add(1);
            rule.last_status = Some(status.to_string());
            true
        } else {
            false
        }
    }

    #[must_use]
    pub fn get_rules(&self) -> &[AutomationRule] {
        &self.rules
    }

    #[must_use]
    pub fn get_laws(&self) -> &[LawRule] {
        &self.laws
    }

    #[must_use]
    pub fn summary(&self) -> AutomationsSummary {
        let enabled_automations = self.rules.iter().filter(|r| r.enabled).count();
        let fixed_laws = self
            .laws
            .iter()
            .filter(|l| l.tier == LawTier::Fixed)
            .count();
        let custom_laws = self
            .laws
            .iter()
            .filter(|l| l.tier == LawTier::Custom)
            .count();
        let total_runs = self.rules.iter().map(|r| r.run_count).sum();

        AutomationsSummary {
            total_automations: self.rules.len(),
            enabled_automations,
            fixed_laws,
            custom_laws,
            total_runs,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rules_registration_and_toggle() {
        let mut engine = AutomationEngine::new();
        let rule = AutomationRule {
            id: "auto-1".to_string(),
            name: "Nightly Sync".to_string(),
            description: "Syncs mesh at midnight".to_string(),
            trigger: TriggerKind::Cron("0 0 * * *".to_string()),
            actions: vec![ActionKind::ExecuteScript {
                script_name: "sync.sh".to_string(),
            }],
            enabled: true,
            run_count: 0,
            last_status: None,
        };

        engine.register_rule(rule);
        assert_eq!(engine.get_rules().len(), 1);

        assert!(engine.toggle_rule("auto-1", false));
        assert!(!engine.get_rules().first().is_none_or(|r| r.enabled));

        assert!(engine.record_execution("auto-1", "success"));
        assert_eq!(engine.get_rules().first().map_or(0, |r| r.run_count), 1);

        assert!(engine.remove_rule("auto-1"));
        assert_eq!(engine.get_rules().len(), 0);
    }

    #[test]
    fn test_event_matching() {
        let mut engine = AutomationEngine::new();
        let rule1 = AutomationRule {
            id: "net-down".to_string(),
            name: "Net Disconnected".to_string(),
            description: "Alert on disconnect".to_string(),
            trigger: TriggerKind::Event("network/disconnect".to_string()),
            actions: vec![],
            enabled: true,
            run_count: 0,
            last_status: None,
        };
        let rule2 = AutomationRule {
            id: "net-down-disabled".to_string(),
            name: "Net Disconnected Inactive".to_string(),
            description: "Ignored".to_string(),
            trigger: TriggerKind::Event("network/disconnect".to_string()),
            actions: vec![],
            enabled: false,
            run_count: 0,
            last_status: None,
        };

        engine.register_rule(rule1);
        engine.register_rule(rule2);

        let matches = engine.match_event_trigger("network/disconnect");
        assert_eq!(matches.len(), 1);
        assert_eq!(matches.first().map(String::as_str), Some("net-down"));
    }

    #[test]
    fn test_laws_and_fixed_protection() {
        let mut engine = AutomationEngine::new();
        let fixed = LawRule {
            id: "fixed-1".to_string(),
            tier: LawTier::Fixed,
            index: 1,
            title: "First Law of Robotics".to_string(),
            body: "Never harm a human".to_string(),
            active: true,
        };
        let custom = LawRule {
            id: "custom-1".to_string(),
            tier: LawTier::Custom,
            index: 10,
            title: "Energy Limit".to_string(),
            body: "Do not exceed 100W".to_string(),
            active: true,
        };

        engine.register_law(fixed);
        engine.register_law(custom);

        assert_eq!(engine.get_laws().len(), 2);
        assert!(engine.remove_custom_law("fixed-1").is_err());
        assert!(engine.remove_custom_law("custom-1").is_ok());
        assert_eq!(engine.get_laws().len(), 1);
    }

    #[test]
    fn test_summary() {
        let engine = AutomationEngine::new();
        let summary = engine.summary();
        assert_eq!(summary.total_automations, 0);
        assert_eq!(summary.total_runs, 0);
    }
}
