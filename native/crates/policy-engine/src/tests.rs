use std::collections::BTreeSet;

use capability_registry::{Contract, Effect, Origin, Param, Role, State, ValueType};

use crate::{Decision, Engine, Policy, PolicyError, Subject, Why, Widget, matches, visible};

const POLICY: &str = r#"{
"ceilings":{"guest":["read"],"child":["read"],"staff":["read","write"],"family":["read","write","send_external"],"owner":["read","write","send_external","spend","physical"]},
"contexts":{
"home":{},
"kids":{"deny":["files.delete","payments.*"],"max_effects":["read"]},
"work":{"approve":["files.write"]}
},
"users":{
"anna":{"deny":["door.unlock"]},
"leo":{"allow_only":["weather.*","image.search"]}
}}"#;

fn contract(id: &str, effects: &[Effect], role: Role) -> Contract {
    Contract {
        id: id.into(),
        version: 1,
        origin: Origin::Local,
        summary: format!("Capability {id}."),
        inputs: vec![Param {
            name: "x".into(),
            ty: ValueType::Text,
            required: false,
        }],
        output: ValueType::Text,
        effects: effects.iter().copied().collect(),
        reversible: !effects.iter().any(|e| e.irreversible_risk()),
        min_role: role,
        nodes: BTreeSet::from(["server".into()]),
        tags: BTreeSet::new(),
        state: State::Active,
    }
}

fn engine() -> Engine {
    Engine::new(Policy::parse(POLICY).expect("policy"))
}

fn subject(user: &str, role: Role) -> Subject<'_> {
    Subject { user, role }
}

#[test]
fn patterns_match_exactly_or_by_prefix() {
    assert!(matches("payments.*", "payments.send"));
    assert!(matches("files.delete", "files.delete"));
    assert!(!matches("files.delete", "files.delete_all"));
    assert!(!matches("payments.*", "pay.send"));
}

#[test]
fn reads_are_allowed_and_irreversible_sends_need_approval() {
    let e = engine();
    let read = contract("image.search", &[Effect::Read], Role::Guest);
    let send = contract("email.send", &[Effect::SendExternal], Role::Family);
    let s = subject("maria", Role::Owner);
    assert_eq!(e.decide(&s, "home", &read), Decision::Allow);
    assert_eq!(e.decide(&s, "home", &send), Decision::Approve);
}

#[test]
fn a_role_never_exceeds_its_effect_ceiling_or_minimum_role() {
    let e = engine();
    let send = contract("email.send", &[Effect::SendExternal], Role::Guest);
    assert_eq!(
        e.decide(&subject("kid", Role::Child), "home", &send),
        Decision::Deny(Why::EffectAboveCeiling)
    );
    let admin = contract("admin.shell", &[Effect::Read], Role::Owner);
    assert_eq!(
        e.decide(&subject("maria", Role::Family), "home", &admin),
        Decision::Deny(Why::RoleTooLow)
    );
    let spend = contract("pay", &[Effect::Spend], Role::Staff);
    assert_eq!(
        e.decide(&subject("bob", Role::Family), "home", &spend),
        Decision::Deny(Why::EffectAboveCeiling)
    );
}

#[test]
fn a_context_can_only_restrict_even_for_the_owner() {
    let e = engine();
    let owner = subject("maria", Role::Owner);
    let write = contract("files.write", &[Effect::Write], Role::Staff);
    assert_eq!(
        e.decide(&owner, "kids", &write),
        Decision::Deny(Why::ContextEffects)
    );
    assert_eq!(e.decide(&owner, "work", &write), Decision::Approve);
    let pay = contract("payments.send", &[Effect::Read], Role::Guest);
    assert_eq!(
        e.decide(&owner, "kids", &pay),
        Decision::Deny(Why::ContextDenied)
    );
    let read = contract("weather.now", &[Effect::Read], Role::Guest);
    assert_eq!(
        e.decide(&owner, "unknown", &read),
        Decision::Deny(Why::UnknownContext)
    );
}

#[test]
fn per_user_rules_narrow_but_never_widen() {
    let e = engine();
    let door = contract("door.unlock", &[Effect::Physical], Role::Family);
    assert_eq!(
        e.decide(&subject("anna", Role::Owner), "home", &door),
        Decision::Deny(Why::UserDenied)
    );
    let weather = contract("weather.now", &[Effect::Read], Role::Guest);
    let mail = contract("email.read", &[Effect::Read], Role::Guest);
    let leo = subject("leo", Role::Owner);
    assert_eq!(e.decide(&leo, "home", &weather), Decision::Allow);
    assert_eq!(
        e.decide(&leo, "home", &mail),
        Decision::Deny(Why::UserNotListed)
    );
    let admin = contract("admin.shell", &[Effect::Read], Role::Owner);
    assert_eq!(
        e.decide(&subject("leo", Role::Guest), "home", &admin),
        Decision::Deny(Why::RoleTooLow)
    );
}

#[test]
fn inactive_capabilities_are_never_allowed() {
    let e = engine();
    let mut c = contract("gen.x", &[Effect::Read], Role::Guest);
    c.state = State::Degraded;
    assert_eq!(
        e.decide(&subject("maria", Role::Owner), "home", &c),
        Decision::Deny(Why::Inactive)
    );
}

#[test]
fn the_allowed_set_matches_the_per_item_decisions() {
    let e = engine();
    let all = [
        contract("image.search", &[Effect::Read], Role::Guest),
        contract("files.delete", &[Effect::Write], Role::Staff),
        contract("email.send", &[Effect::SendExternal], Role::Family),
    ];
    let ids = e.allowed_ids(&subject("maria", Role::Owner), "kids", &all);
    assert_eq!(ids, BTreeSet::from(["image.search"]));
}

#[test]
fn replacing_the_policy_bumps_the_generation() {
    let mut e = engine();
    assert_eq!(e.generation(), 1);
    e.replace(Policy::parse(POLICY).expect("policy"));
    assert_eq!(e.generation(), 2);
}

#[test]
fn malformed_policies_are_rejected() {
    assert!(matches!(Policy::parse("{"), Err(PolicyError::Invalid(_))));
    assert!(Policy::parse(r#"{"ceilings":{"owner":["read"]}}"#).is_err());
    assert!(Policy::parse(r#"{"ceilings":{"guest":["read","spend"],"owner":["read"]}}"#).is_err());
    assert!(
        Policy::parse(r#"{"ceilings":{"guest":["read"]},"contexts":{"Bad Name":{}}}"#).is_err()
    );
    assert!(
        Policy::parse(r#"{"ceilings":{"guest":["read"]},"contexts":{"a":{"deny":["../x"]}}}"#)
            .is_err()
    );
    assert!(Policy::parse(r#"{"ceilings":{"guest":["read"]},"extra":1}"#).is_err());
}

#[test]
fn widgets_follow_role_and_context() {
    let widgets = [
        Widget {
            id: "weather".into(),
            min_role: Role::Guest,
            contexts: BTreeSet::new(),
        },
        Widget {
            id: "cameras".into(),
            min_role: Role::Family,
            contexts: BTreeSet::from(["home".into()]),
        },
        Widget {
            id: "payroll".into(),
            min_role: Role::Owner,
            contexts: BTreeSet::from(["work".into()]),
        },
    ];
    assert_eq!(visible(Role::Child, "home", &widgets), vec!["weather"]);
    assert_eq!(
        visible(Role::Family, "home", &widgets),
        vec!["weather", "cameras"]
    );
    assert_eq!(
        visible(Role::Owner, "work", &widgets),
        vec!["weather", "payroll"]
    );
}
