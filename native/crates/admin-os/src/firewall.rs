use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FirewallMode {
    Off,
    Monitor,
    Protect,
    Lockdown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuleAction {
    Accept,
    Drop,
    Reject,
    Limit,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuleDirection {
    Input,
    Output,
    Forward,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuleProtocol {
    Any,
    Tcp,
    Udp,
    Icmp,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FirewallRule {
    pub id: String,
    pub enabled: bool,
    pub action: RuleAction,
    pub direction: RuleDirection,
    pub protocol: RuleProtocol,
    pub ports: Vec<String>,
    pub sources: Vec<String>,
    pub comment: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BlockedAddress {
    pub address: String,
    pub expires: Option<u64>,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[allow(clippy::struct_excessive_bools)]
pub struct FirewallEngine {
    pub mode: FirewallMode,
    pub rules: Vec<FirewallRule>,
    pub blocks: Vec<BlockedAddress>,
    pub allow_lan: bool,
    pub allow_ping: bool,
    pub auto_block: bool,
    pub ai_analysis: bool,
}

impl Default for FirewallEngine {
    fn default() -> Self {
        Self {
            mode: FirewallMode::Protect,
            rules: Vec::new(),
            blocks: Vec::new(),
            allow_lan: true,
            allow_ping: true,
            auto_block: true,
            ai_analysis: true,
        }
    }
}

impl FirewallEngine {
    #[must_use]
    pub fn new(mode: FirewallMode) -> Self {
        Self {
            mode,
            ..Default::default()
        }
    }

    pub fn add_rule(&mut self, rule: FirewallRule) {
        if let Some(existing) = self.rules.iter_mut().find(|r| r.id == rule.id) {
            *existing = rule;
        } else {
            self.rules.push(rule);
        }
    }

    pub fn remove_rule(&mut self, id: &str) -> bool {
        if let Some(pos) = self.rules.iter().position(|r| r.id == id) {
            self.rules.remove(pos);
            true
        } else {
            false
        }
    }

    pub fn toggle_rule(&mut self, id: &str, enabled: bool) -> bool {
        if let Some(rule) = self.rules.iter_mut().find(|r| r.id == id) {
            rule.enabled = enabled;
            true
        } else {
            false
        }
    }

    pub fn block_address(
        &mut self,
        address: &str,
        duration_secs: Option<u64>,
        reason: &str,
        now: u64,
    ) {
        let expires = duration_secs.and_then(|d| now.checked_add(d));
        if let Some(existing) = self.blocks.iter_mut().find(|b| b.address == address) {
            existing.expires = expires;
            existing.reason = reason.to_string();
        } else {
            self.blocks.push(BlockedAddress {
                address: address.to_string(),
                expires,
                reason: reason.to_string(),
            });
        }
    }

    pub fn unblock_address(&mut self, address: &str) -> bool {
        if let Some(pos) = self.blocks.iter().position(|b| b.address == address) {
            self.blocks.remove(pos);
            true
        } else {
            false
        }
    }

    #[must_use]
    pub fn is_blocked(&self, address: &str, now: u64) -> bool {
        self.blocks
            .iter()
            .any(|b| b.address == address && b.expires.is_none_or(|exp| exp > now))
    }

    pub fn cleanup_expired_blocks(&mut self, now: u64) {
        self.blocks
            .retain(|b| b.expires.is_none_or(|exp| exp > now));
    }

    #[must_use]
    pub fn evaluate(
        &self,
        direction: RuleDirection,
        protocol: RuleProtocol,
        src_ip: &str,
        dst_port: Option<u16>,
        now: u64,
    ) -> RuleAction {
        if self.mode == FirewallMode::Off {
            return RuleAction::Accept;
        }

        if self.is_blocked(src_ip, now) {
            return RuleAction::Drop;
        }

        if self.mode == FirewallMode::Lockdown {
            return RuleAction::Drop;
        }

        for rule in &self.rules {
            if !rule.enabled {
                continue;
            }
            if rule.direction != direction {
                continue;
            }
            if rule.protocol != RuleProtocol::Any && rule.protocol != protocol {
                continue;
            }
            if !rule.sources.is_empty() && !rule.sources.iter().any(|s| s == src_ip) {
                continue;
            }
            if let Some(port) = dst_port {
                if !rule.ports.is_empty() {
                    let port_str = port.to_string();
                    if !rule.ports.iter().any(|p| p == &port_str) {
                        continue;
                    }
                }
            }
            return rule.action;
        }

        match self.mode {
            FirewallMode::Monitor | FirewallMode::Protect => RuleAction::Accept,
            _ => RuleAction::Drop,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_firewall_blocks_and_expiry() {
        let mut engine = FirewallEngine::new(FirewallMode::Protect);
        let now = 1000u64;

        engine.block_address("1.2.3.4", Some(60), "malicious", now);
        assert!(engine.is_blocked("1.2.3.4", now));
        assert!(engine.is_blocked("1.2.3.4", now + 30));
        assert!(!engine.is_blocked("1.2.3.4", now + 61));

        engine.cleanup_expired_blocks(now + 61);
        assert_eq!(engine.blocks.len(), 0);

        engine.block_address("5.6.7.8", None, "permanent", now);
        assert!(engine.is_blocked("5.6.7.8", now + 999_999));
        assert!(engine.unblock_address("5.6.7.8"));
        assert!(!engine.is_blocked("5.6.7.8", now));
    }

    #[test]
    fn test_firewall_rule_evaluation() {
        let mut engine = FirewallEngine::new(FirewallMode::Protect);
        let rule = FirewallRule {
            id: "drop-ssh".to_string(),
            enabled: true,
            action: RuleAction::Drop,
            direction: RuleDirection::Input,
            protocol: RuleProtocol::Tcp,
            ports: vec!["22".to_string()],
            sources: vec![],
            comment: "Block SSH".to_string(),
        };

        engine.add_rule(rule);

        let action = engine.evaluate(
            RuleDirection::Input,
            RuleProtocol::Tcp,
            "10.0.0.1",
            Some(22),
            100,
        );
        assert_eq!(action, RuleAction::Drop);

        let action_other_port = engine.evaluate(
            RuleDirection::Input,
            RuleProtocol::Tcp,
            "10.0.0.1",
            Some(80),
            100,
        );
        assert_eq!(action_other_port, RuleAction::Accept);

        assert!(engine.toggle_rule("drop-ssh", false));
        let action_disabled = engine.evaluate(
            RuleDirection::Input,
            RuleProtocol::Tcp,
            "10.0.0.1",
            Some(22),
            100,
        );
        assert_eq!(action_disabled, RuleAction::Accept);

        assert!(engine.remove_rule("drop-ssh"));
        assert_eq!(engine.rules.len(), 0);
    }
}
