use std::collections::{BTreeMap, HashMap};

use serde_json::json;

use crate::{Policy, Risk, RiskTable, Strength, Verdict};

fn policy() -> Policy {
    let ceiling: BTreeMap<String, Risk> = [
        ("system", Risk::Critical),
        ("owner", Risk::Critical),
        ("family", Risk::Files),
        ("guest", Risk::Home),
        ("anonymous", Risk::Home),
    ]
    .into_iter()
    .map(|(k, v)| (k.to_owned(), v))
    .collect();
    let proof: BTreeMap<Risk, Strength> = [
        (Risk::Info, Strength::None),
        (Risk::Home, Strength::None),
        (Risk::Personal, Strength::Single),
        (Risk::Files, Strength::Single),
        (Risk::Critical, Strength::Strong),
    ]
    .into_iter()
    .collect();
    let subroles = [("nanny".to_owned(), Risk::Home)].into_iter().collect();
    Policy::new(ceiling, proof, subroles)
}

#[test]
fn ceilings_proof_subroles_overrides() {
    let p = policy();
    assert_eq!(
        p.check("owner", "", "", Strength::Strong, Risk::Critical)
            .verdict,
        Verdict::Ok
    );
    assert_eq!(
        p.check("owner", "", "", Strength::Single, Risk::Critical)
            .verdict,
        Verdict::Proof
    );
    assert_eq!(
        p.check("guest", "", "", Strength::Strong, Risk::Personal)
            .verdict,
        Verdict::Role
    );
    assert_eq!(
        p.check("family", "nanny", "", Strength::Strong, Risk::Files)
            .verdict,
        Verdict::Role
    );
    assert_eq!(
        p.check("unknown", "", "", Strength::None, Risk::Home)
            .verdict,
        Verdict::Ok
    );
    assert_eq!(p.limit("guest", "", " Files "), Risk::Files);
    assert_eq!(p.limit("system", "", "info"), Risk::Critical);
}

#[test]
fn apply_respects_floors_and_system() {
    let mut p = policy();
    p.apply(&json!({"ceiling": {"system": "info", "guest": "personal", "ghost": "critical", "family": "bogus"},
                    "proof": {"critical": "weak", "personal": "none", "home": "strong", "files": "STRONG"}}));
    assert_eq!(p.ceiling().get("system"), Some(&Risk::Critical));
    assert_eq!(p.ceiling().get("guest"), Some(&Risk::Personal));
    assert!(!p.ceiling().contains_key("ghost"));
    assert_eq!(p.ceiling().get("family"), Some(&Risk::Files));
    assert_eq!(p.proof().get(&Risk::Critical), Some(&Strength::Strong));
    assert_eq!(p.proof().get(&Risk::Personal), Some(&Strength::Weak));
    assert_eq!(p.proof().get(&Risk::Home), Some(&Strength::None));
    assert_eq!(p.proof().get(&Risk::Files), Some(&Strength::Strong));
    p.apply(&json!({}));
    assert_eq!(p.ceiling().get("guest"), Some(&Risk::Home));
}

#[test]
fn composed_tools_take_the_worst_step_and_cycles_are_critical() {
    let tools: HashMap<String, Risk> = [("now", Risk::Info), ("read_file", Risk::Personal)]
        .into_iter()
        .map(|(k, v)| (k.to_owned(), v))
        .collect();
    let mut table = RiskTable::new(tools);
    assert!(table.compose("morning", vec!["now".into(), "read_file".into()]));
    assert!(table.compose("loop_a", vec!["loop_b".into()]));
    assert!(table.compose("loop_b", vec!["loop_a".into()]));
    assert!(table.compose("empty", vec![]));
    assert_eq!(table.of_tool("morning"), Risk::Personal);
    assert_eq!(table.of_tool("loop_a"), Risk::Critical);
    assert_eq!(table.of_tool("empty"), Risk::Critical);
    assert_eq!(table.of_tool("unknown"), Risk::Critical);
    table.forget("morning");
    assert_eq!(table.of_tool("morning"), Risk::Critical);
    assert!(!table.compose("big", vec!["now".into(); 100]));
}
