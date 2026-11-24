use std::collections::{BTreeMap, BTreeSet};

use capability_registry::{Contract, Effect, Origin, Param, Registry, Role, State, ValueType};

use crate::{
    Artifact, Expect, Forge, ForgeError, Kind, Observation, Probe, SHADOW_STREAK, Sandbox,
    SandboxError, Stage,
};

fn contract(id: &str, effects: &[Effect], version: u32) -> Contract {
    Contract {
        id: id.into(),
        version,
        origin: Origin::Generated,
        summary: "Convert a temperature from Celsius to Fahrenheit.".into(),
        inputs: vec![Param {
            name: "value".into(),
            ty: ValueType::Text,
            required: true,
        }],
        output: ValueType::Text,
        effects: effects.iter().copied().collect(),
        reversible: !effects.iter().any(|e| e.irreversible_risk()),
        min_role: Role::Family,
        nodes: BTreeSet::from(["server".into()]),
        tags: BTreeSet::new(),
        state: State::Active,
    }
}

fn artifact(tag: &str) -> Artifact {
    Artifact {
        kind: Kind::Wasm,
        digest: tag.into(),
        size: 2_048,
    }
}

fn probes() -> Vec<Probe> {
    ["0", "100", "-40"]
        .iter()
        .zip(["32", "212", "-40"])
        .map(|(input, out)| Probe {
            input: BTreeMap::from([("value".to_owned(), (*input).to_owned())]),
            expect: Expect::Equals(out.into()),
        })
        .collect()
}

struct Box_ {
    effects: BTreeSet<Effect>,
    millis: u32,
    broken: bool,
}

impl Box_ {
    fn honest() -> Self {
        Self {
            effects: BTreeSet::new(),
            millis: 5,
            broken: false,
        }
    }
}

impl Sandbox for Box_ {
    fn run(
        &mut self,
        _artifact: &Artifact,
        input: &BTreeMap<String, String>,
    ) -> Result<Observation, SandboxError> {
        if self.broken {
            return Err(SandboxError::Crashed);
        }
        let celsius: i32 = input.get("value").and_then(|v| v.parse().ok()).unwrap_or(0);
        Ok(Observation {
            output: (celsius * 9 / 5 + 32).to_string(),
            effects: self.effects.clone(),
            millis: self.millis,
        })
    }
}

fn shadowed(forge: &mut Forge, registry: &mut Registry, id: &str) {
    forge
        .submit(
            registry,
            contract(id, &[Effect::Read], 1),
            artifact("a"),
            probes(),
        )
        .expect("submit");
    assert_eq!(
        forge
            .verify(registry, id, &mut Box_::honest())
            .expect("verify"),
        Stage::Verified
    );
    for _ in 0..SHADOW_STREAK {
        forge.shadow(id, true).expect("shadow");
    }
}

#[test]
fn a_generated_capability_walks_every_gate_before_it_becomes_usable() {
    let mut registry = Registry::new();
    let mut forge = Forge::new();
    forge
        .submit(
            &mut registry,
            contract("gen.temp", &[Effect::Read], 1),
            artifact("a"),
            probes(),
        )
        .expect("submit");
    let c = registry.get("gen.temp").expect("contract");
    assert_eq!(c.state, State::Degraded);
    assert!(registry.selectable(Role::Owner).is_empty());
    assert_eq!(
        forge.activate(&mut registry, "gen.temp", Role::Owner),
        Err(ForgeError::WrongStage("gen.temp".into()))
    );
    forge
        .verify(&mut registry, "gen.temp", &mut Box_::honest())
        .expect("verify");
    for _ in 0..SHADOW_STREAK {
        assert_ne!(forge.stage("gen.temp"), Some(Stage::Shadowed));
        forge.shadow("gen.temp", true).expect("shadow");
    }
    assert_eq!(forge.stage("gen.temp"), Some(Stage::Shadowed));
    forge
        .activate(&mut registry, "gen.temp", Role::Family)
        .expect("activate");
    assert!(registry.selectable(Role::Family).contains("gen.temp"));
}

#[test]
fn a_probe_that_fails_keeps_the_capability_unverified() {
    let mut registry = Registry::new();
    let mut forge = Forge::new();
    forge
        .submit(
            &mut registry,
            contract("gen.temp", &[Effect::Read], 1),
            artifact("a"),
            probes(),
        )
        .expect("submit");
    let mut crashing = Box_::honest();
    crashing.broken = true;
    assert_eq!(
        forge
            .verify(&mut registry, "gen.temp", &mut crashing)
            .expect("verify"),
        Stage::Drafted
    );
    let mut slow = Box_::honest();
    slow.millis = 9_000;
    assert_eq!(
        forge
            .verify(&mut registry, "gen.temp", &mut slow)
            .expect("verify"),
        Stage::Drafted
    );
}

#[test]
fn undeclared_side_effects_quarantine_and_revoke_for_good() {
    let mut registry = Registry::new();
    let mut forge = Forge::new();
    forge
        .submit(
            &mut registry,
            contract("gen.temp", &[Effect::Read], 1),
            artifact("a"),
            probes(),
        )
        .expect("submit");
    let mut sneaky = Box_::honest();
    sneaky.effects = BTreeSet::from([Effect::SendExternal]);
    assert_eq!(
        forge
            .verify(&mut registry, "gen.temp", &mut sneaky)
            .expect("verify"),
        Stage::Quarantined
    );
    assert_eq!(
        registry.get("gen.temp").map(|c| c.state),
        Some(State::Revoked)
    );
    let again = forge.submit(
        &mut registry,
        contract("gen.temp", &[Effect::Read], 2),
        artifact("b"),
        probes(),
    );
    assert_eq!(again, Err(ForgeError::Quarantined("gen.temp".into())));
    assert!(forge.shadow("gen.temp", true).is_err());
}

#[test]
fn one_disagreement_in_shadow_mode_restarts_the_streak() {
    let mut registry = Registry::new();
    let mut forge = Forge::new();
    forge
        .submit(
            &mut registry,
            contract("gen.temp", &[Effect::Read], 1),
            artifact("a"),
            probes(),
        )
        .expect("submit");
    forge
        .verify(&mut registry, "gen.temp", &mut Box_::honest())
        .expect("verify");
    for _ in 0..SHADOW_STREAK - 1 {
        forge.shadow("gen.temp", true).expect("shadow");
    }
    forge.shadow("gen.temp", false).expect("shadow");
    forge.shadow("gen.temp", true).expect("shadow");
    assert_ne!(forge.stage("gen.temp"), Some(Stage::Shadowed));
}

#[test]
fn irreversible_effects_need_the_owner_to_approve() {
    let mut registry = Registry::new();
    let mut forge = Forge::new();
    forge
        .submit(
            &mut registry,
            contract("gen.notify", &[Effect::SendExternal], 1),
            artifact("a"),
            probes(),
        )
        .expect("submit");
    forge
        .verify(&mut registry, "gen.notify", &mut Box_::honest())
        .expect("verify");
    for _ in 0..SHADOW_STREAK {
        forge.shadow("gen.notify", true).expect("shadow");
    }
    assert_eq!(
        forge.activate(&mut registry, "gen.notify", Role::Family),
        Err(ForgeError::ApprovalTooLow)
    );
    forge
        .activate(&mut registry, "gen.notify", Role::Owner)
        .expect("activate");
}

#[test]
fn a_generated_capability_cannot_replace_a_system_tool() {
    let mut registry = Registry::new();
    let mut system = contract("files.read", &[Effect::Read], 1);
    system.origin = Origin::Local;
    registry.insert(system).expect("insert");
    let mut forge = Forge::new();
    let hijack = forge.submit(
        &mut registry,
        contract("files.read", &[Effect::Read], 9),
        artifact("evil"),
        probes(),
    );
    assert!(hijack.is_err());
    assert_eq!(
        registry.get("files.read").map(|c| c.origin),
        Some(Origin::Local)
    );
}

#[test]
fn malformed_submissions_are_rejected_before_touching_the_registry() {
    let mut registry = Registry::new();
    let mut forge = Forge::new();
    let few = probes().into_iter().take(2).collect();
    assert!(
        forge
            .submit(
                &mut registry,
                contract("gen.a", &[Effect::Read], 1),
                artifact("a"),
                few
            )
            .is_err()
    );
    let mut huge = artifact("a");
    huge.size = 2 * 1024 * 1024;
    assert!(
        forge
            .submit(
                &mut registry,
                contract("gen.a", &[Effect::Read], 1),
                huge,
                probes()
            )
            .is_err()
    );
    assert!(registry.is_empty());
}

#[test]
fn retiring_removes_the_capability_from_selection() {
    let mut registry = Registry::new();
    let mut forge = Forge::new();
    shadowed(&mut forge, &mut registry, "gen.temp");
    forge
        .activate(&mut registry, "gen.temp", Role::Owner)
        .expect("activate");
    forge.retire(&mut registry, "gen.temp").expect("retire");
    assert!(registry.selectable(Role::Owner).is_empty());
    assert_eq!(forge.next_version("gen.temp"), 1);
}
