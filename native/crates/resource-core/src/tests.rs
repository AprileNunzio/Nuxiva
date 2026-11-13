#![allow(
    clippy::unwrap_used,
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]

use super::*;

const GB: u64 = 1024 * 1024 * 1024;

fn comp(id: &str, kind: Kind, class: Class, rss: u64) -> Component {
    Component {
        id: id.into(),
        kind,
        class,
        rss,
        budget: None,
        idle_ms: 0,
        visible: true,
        reclaimable: true,
        cpu_percent: 0.0,
    }
}

fn input(avail_mb: u64, components: Vec<Component>, previous: Option<Level>) -> Input {
    Input {
        system: System {
            mem_total: 16 * GB,
            mem_available: avail_mb * 1024 * 1024,
            ..System::default()
        },
        components,
        previous,
    }
}

#[test]
fn calm_system_only_suspends_hidden_surfaces() {
    let mut hidden = comp("avatar3d", Kind::Surface, Class::Normal, GB);
    hidden.visible = false;
    let p = plan(&input(
        14336,
        vec![hidden, comp("llm", Kind::Model, Class::Normal, 4 * GB)],
        None,
    ));
    assert_eq!(p.level, Level::Calm);
    assert_eq!(p.actions.len(), 1);
    assert_eq!(p.actions[0].action, ActionKind::Suspend);
}

#[test]
fn protected_components_never_get_actions() {
    let mut voice = comp("voice", Kind::Process, Class::Protected, 8 * GB);
    voice.idle_ms = u64::MAX;
    voice.visible = false;
    let p = plan(&input(0, vec![voice], None));
    assert_eq!(p.level, Level::Critical);
    assert!(p.actions.is_empty());
    assert_eq!(p.protected, vec!["voice".to_string()]);
}

#[test]
fn idle_model_unloads_sooner_under_pressure() {
    let mut model = comp("llm", Kind::Model, Class::Normal, 4 * GB);
    model.idle_ms = 200_000;
    model.visible = false;
    let calm = plan(&input(14336, vec![model.clone()], None));
    let high = plan(&input(1024, vec![model], None));
    assert!(calm.actions.is_empty());
    assert_eq!(high.actions[0].action, ActionKind::Unload);
}

#[test]
fn over_budget_cache_is_dropped_when_elevated() {
    let p = plan(&input(
        3072,
        vec![comp("cache", Kind::Cache, Class::Low, 3 * GB)],
        None,
    ));
    assert!(p.level >= Level::Elevated);
    assert_eq!(p.actions[0].action, ActionKind::Drop);
}

#[test]
fn level_has_hysteresis() {
    let held = plan(&input(2560, vec![], Some(Level::High)));
    let fresh = plan(&input(2560, vec![], None));
    assert!(held.level > fresh.level);
}

#[test]
fn json_roundtrip_and_validation() {
    let raw = r#"{"system":{"mem_total":1000,"mem_available":100},"components":[{"id":"a","kind":"cache","class":"low","rss":10,"reclaimable":true}]}"#;
    let out = plan_json(raw).expect("plan");
    assert!(out.contains("\"level\""));
    assert_eq!(plan_json("{").unwrap_err(), ResourceError::Invalid);
    let bad = r#"{"system":{"mem_total":0,"mem_available":0}}"#;
    assert_eq!(plan_json(bad).unwrap_err(), ResourceError::Invalid);
    let id = r#"{"system":{"mem_total":10,"mem_available":5},"components":[{"id":"BAD ID","kind":"cache","class":"low"}]}"#;
    assert_eq!(plan_json(id).unwrap_err(), ResourceError::Invalid);
}
