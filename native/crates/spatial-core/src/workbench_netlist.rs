use std::collections::HashMap;

use serde::{Deserialize, Serialize};

const GROUND_NAMES: [&str; 5] = ["gnd", "0", "vss", "agnd", "dgnd"];

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct PinReference {
    pub reference: String,
    pub pin: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct NetlistNet {
    pub name: String,
    pub pins: Vec<PinReference>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NetlistIssueKind {
    MissingGround,
    DanglingNet,
    PinOnMultipleNets,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct NetlistIssue {
    pub kind: NetlistIssueKind,
    pub net: String,
    pub detail: String,
}

#[must_use]
pub fn validate_netlist(nets: &[NetlistNet]) -> Vec<NetlistIssue> {
    let mut issues = Vec::new();
    if !nets.is_empty() && !nets.iter().any(|net| is_ground(&net.name)) {
        issues.push(NetlistIssue {
            kind: NetlistIssueKind::MissingGround,
            net: String::new(),
            detail: String::new(),
        });
    }
    let mut owners: HashMap<&PinReference, &str> = HashMap::new();
    for net in nets {
        if net.pins.len() < 2 {
            issues.push(NetlistIssue {
                kind: NetlistIssueKind::DanglingNet,
                net: net.name.clone(),
                detail: String::new(),
            });
        }
        for pin in &net.pins {
            match owners.get(pin) {
                Some(owner) if *owner != net.name.as_str() => {
                    issues.push(NetlistIssue {
                        kind: NetlistIssueKind::PinOnMultipleNets,
                        net: net.name.clone(),
                        detail: format!("{}:{}<->{}", pin.reference, pin.pin, owner),
                    });
                }
                Some(_) => {}
                None => {
                    owners.insert(pin, net.name.as_str());
                }
            }
        }
    }
    issues
}

fn is_ground(name: &str) -> bool {
    let lowered = name.trim().to_lowercase();
    GROUND_NAMES.contains(&lowered.as_str())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pin(reference: &str, pin: &str) -> PinReference {
        PinReference {
            reference: reference.to_owned(),
            pin: pin.to_owned(),
        }
    }

    fn net(name: &str, pins: Vec<PinReference>) -> NetlistNet {
        NetlistNet {
            name: name.to_owned(),
            pins,
        }
    }

    #[test]
    fn valid_netlist_has_no_issues() {
        let nets = vec![
            net("VCC", vec![pin("R1", "1"), pin("U1", "8")]),
            net("GND", vec![pin("R1", "2"), pin("U1", "4")]),
        ];
        assert!(validate_netlist(&nets).is_empty());
    }

    #[test]
    fn detects_missing_ground_and_dangling_net() {
        let nets = vec![net("VCC", vec![pin("R1", "1")])];
        let kinds: Vec<_> = validate_netlist(&nets).iter().map(|i| i.kind).collect();
        assert!(kinds.contains(&NetlistIssueKind::MissingGround));
        assert!(kinds.contains(&NetlistIssueKind::DanglingNet));
    }

    #[test]
    fn detects_pin_shared_by_two_nets() {
        let nets = vec![
            net("VCC", vec![pin("U1", "8"), pin("R1", "1")]),
            net("GND", vec![pin("U1", "8"), pin("R1", "2")]),
        ];
        let kinds: Vec<_> = validate_netlist(&nets).iter().map(|i| i.kind).collect();
        assert!(kinds.contains(&NetlistIssueKind::PinOnMultipleNets));
    }
}
