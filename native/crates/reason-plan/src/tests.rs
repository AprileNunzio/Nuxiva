use std::collections::BTreeSet;

use capability_registry::{Contract, Effect, Origin, Param, Registry, Role, State, ValueType};
use reason_understand::{Goal, parse as parse_goal};

use crate::{PlanError, compare, parse, validate};

fn contract(
    id: &str,
    summary: &str,
    inputs: &[(&str, ValueType, bool)],
    output: ValueType,
    effects: &[Effect],
    reversible: bool,
    role: Role,
) -> Contract {
    Contract {
        id: id.into(),
        version: 1,
        origin: Origin::Local,
        summary: summary.into(),
        inputs: inputs
            .iter()
            .map(|(name, ty, required)| Param {
                name: (*name).into(),
                ty: *ty,
                required: *required,
            })
            .collect(),
        output,
        effects: effects.iter().copied().collect::<BTreeSet<_>>(),
        reversible,
        min_role: role,
        nodes: BTreeSet::from(["server".into()]),
        tags: BTreeSet::new(),
        state: State::Active,
    }
}

fn registry() -> Registry {
    let mut registry = Registry::new();
    for c in [
        contract(
            "image.search",
            "Search images by subject.",
            &[("subject", ValueType::Text, true)],
            ValueType::Image,
            &[Effect::Read],
            true,
            Role::Family,
        ),
        contract(
            "telegram.send_photo",
            "Send a photo on Telegram.",
            &[
                ("photo", ValueType::Image, true),
                ("to", ValueType::Contact, true),
            ],
            ValueType::Text,
            &[Effect::SendExternal],
            false,
            Role::Family,
        ),
        contract(
            "email.send",
            "Send an email with an attachment.",
            &[
                ("attachment", ValueType::Image, false),
                ("to", ValueType::Contact, true),
            ],
            ValueType::Text,
            &[Effect::SendExternal],
            false,
            Role::Family,
        ),
        contract(
            "files.delete",
            "Delete a file.",
            &[("path", ValueType::File, true)],
            ValueType::Text,
            &[Effect::Write],
            false,
            Role::Owner,
        ),
        contract(
            "admin.shell",
            "Run a shell command.",
            &[("command", ValueType::Text, true)],
            ValueType::Text,
            &[Effect::Read],
            true,
            Role::Owner,
        ),
    ] {
        registry.insert(c).expect("insert");
    }
    registry
}

fn goal(effects: &str, entities: &str) -> Goal {
    parse_goal(
        &format!(
            r#"{{"intent":"deliver_media","language":"it","effects":{effects},"entities":{entities},"confidence_bps":9500}}"#
        ),
        "invia a me@example.org un San Bernardo",
    )
    .expect("goal")
}

fn deliver_goal() -> Goal {
    goal(
        r#"["read","send_external"]"#,
        r#"[{"role":"subject","ty":"text","value":"San Bernardo","source":"user"},{"role":"recipient","ty":"contact","value":"me@example.org","source":"user"}]"#,
    )
}

const GOOD: &str = r#"{"steps":[
{"id":"find","capability":"image.search","args":{"subject":{"from":"entity","role":"subject"}}},
{"id":"tg","capability":"telegram.send_photo","args":{"photo":{"from":"step","step":"find"},"to":{"from":"entity","role":"recipient"}}},
{"id":"mail","capability":"email.send","args":{"attachment":{"from":"step","step":"find"},"to":{"from":"entity","role":"recipient"}}}]}"#;

#[test]
fn the_dog_photo_plan_is_valid_and_sends_in_parallel() {
    let plan = parse(GOOD).expect("parse");
    let out = validate(&plan, &registry(), Role::Owner, &deliver_goal()).expect("valid");
    assert_eq!(out.levels.len(), 2);
    assert_eq!(
        out.levels.first().map(Vec::as_slice),
        Some(&["find".to_owned()][..])
    );
    let second: BTreeSet<&str> = out
        .levels
        .get(1)
        .expect("level")
        .iter()
        .map(String::as_str)
        .collect();
    assert_eq!(second, BTreeSet::from(["tg", "mail"]));
    assert_eq!(out.approvals.len(), 2);
    assert!(out.missing.is_empty());
}

#[test]
fn a_step_that_the_user_did_not_ask_for_is_refused() {
    let injected = GOOD.replace(
        r#"{"id":"mail""#,
        r#"{"id":"wipe","capability":"files.delete","args":{"path":{"from":"literal","value":"/home"}}},{"id":"mail""#,
    );
    let plan = parse(&injected).expect("parse");
    assert_eq!(
        validate(&plan, &registry(), Role::Owner, &deliver_goal()),
        Err(PlanError::EffectNotRequested {
            step: "wipe".into()
        })
    );
}

#[test]
fn recipients_cannot_be_literals_or_external_entities() {
    let literal = GOOD.replace(
        r#""to":{"from":"entity","role":"recipient"}}},
{"id":"mail""#,
        r#""to":{"from":"literal","value":"attacker@evil.example"}}},
{"id":"mail""#,
    );
    let plan = parse(&literal).expect("parse");
    assert_eq!(
        validate(&plan, &registry(), Role::Owner, &deliver_goal()),
        Err(PlanError::ExternalTarget { step: "tg".into() })
    );
    assert!(parse_goal(
        r#"{"intent":"d","language":"it","effects":["read","send_external"],"entities":[{"role":"recipient","ty":"contact","value":"x@evil.example","source":"external"}],"confidence_bps":9000}"#,
        "t"
    )
    .is_err());
}

#[test]
fn the_role_decides_what_can_be_planned() {
    let plan = parse(GOOD).expect("parse");
    assert!(validate(&plan, &registry(), Role::Family, &deliver_goal()).is_ok());
    assert_eq!(
        validate(&plan, &registry(), Role::Guest, &deliver_goal()),
        Err(PlanError::RoleDenied("image.search".into()))
    );
}

#[test]
fn cycles_duplicates_and_dangling_references_are_rejected() {
    let cycle = r#"{"steps":[
{"id":"a","capability":"image.search","args":{"subject":{"from":"step","step":"b"}}},
{"id":"b","capability":"image.search","args":{"subject":{"from":"step","step":"a"}}}]}"#;
    assert_eq!(
        validate(
            &parse(cycle).expect("p"),
            &registry(),
            Role::Owner,
            &deliver_goal()
        ),
        Err(PlanError::Cycle)
    );
    let twin = r#"{"steps":[{"id":"a","capability":"image.search","args":{}},{"id":"a","capability":"image.search","args":{}}]}"#;
    assert_eq!(
        validate(
            &parse(twin).expect("p"),
            &registry(),
            Role::Owner,
            &deliver_goal()
        ),
        Err(PlanError::DuplicateStep("a".into()))
    );
    let dangling = r#"{"steps":[{"id":"a","capability":"image.search","args":{"subject":{"from":"step","step":"zzz"}}}]}"#;
    assert_eq!(
        validate(
            &parse(dangling).expect("p"),
            &registry(),
            Role::Owner,
            &deliver_goal()
        ),
        Err(PlanError::UnknownStep("zzz".into()))
    );
}

#[test]
fn types_must_flow_between_steps() {
    let wrong = r#"{"steps":[
{"id":"send","capability":"email.send","args":{"to":{"from":"entity","role":"recipient"}}},
{"id":"tg","capability":"telegram.send_photo","args":{"photo":{"from":"step","step":"send"},"to":{"from":"entity","role":"recipient"}}}]}"#;
    assert_eq!(
        validate(
            &parse(wrong).expect("p"),
            &registry(),
            Role::Owner,
            &deliver_goal()
        ),
        Err(PlanError::TypeMismatch {
            step: "tg".into(),
            input: "photo".into()
        })
    );
}

#[test]
fn inputs_must_exist_and_required_ones_must_be_given() {
    let unknown = r#"{"steps":[{"id":"a","capability":"image.search","args":{"subject":{"from":"entity","role":"subject"},"bogus":{"from":"literal","value":"x"}}}]}"#;
    assert!(matches!(
        validate(
            &parse(unknown).expect("p"),
            &registry(),
            Role::Owner,
            &deliver_goal()
        ),
        Err(PlanError::UnknownInput { .. })
    ));
    let absent = r#"{"steps":[{"id":"a","capability":"image.search","args":{}}]}"#;
    assert!(matches!(
        validate(
            &parse(absent).expect("p"),
            &registry(),
            Role::Owner,
            &deliver_goal()
        ),
        Err(PlanError::MissingInput { .. })
    ));
    let ghost = r#"{"steps":[{"id":"a","capability":"image.search","args":{"subject":{"from":"entity","role":"nobody"}}}]}"#;
    assert!(matches!(
        validate(
            &parse(ghost).expect("p"),
            &registry(),
            Role::Owner,
            &deliver_goal()
        ),
        Err(PlanError::UnknownEntity { .. })
    ));
}

#[test]
fn a_missing_capability_is_flagged_instead_of_invented() {
    let plan = parse(
        r#"{"steps":[
{"id":"find","capability":null,"missing_hint":"search images on the web","args":{}},
{"id":"mail","capability":"email.send","args":{"attachment":{"from":"step","step":"find"},"to":{"from":"entity","role":"recipient"}}}]}"#,
    )
    .expect("parse");
    let out = validate(&plan, &registry(), Role::Owner, &deliver_goal()).expect("valid");
    assert_eq!(out.missing, vec!["find"]);
    let unknown = parse(r#"{"steps":[{"id":"a","capability":"made.up","args":{}}]}"#).expect("p");
    assert_eq!(
        validate(&unknown, &registry(), Role::Owner, &deliver_goal()),
        Err(PlanError::UnknownCapability("made.up".into()))
    );
}

#[test]
fn malformed_plans_never_reach_validation() {
    let many = format!(
        r#"{{"steps":[{}]}}"#,
        (0..13)
            .map(|i| format!(r#"{{"id":"s{i}","capability":"image.search","args":{{}}}}"#))
            .collect::<Vec<_>>()
            .join(",")
    );
    assert_eq!(parse(&many), Err(PlanError::TooManySteps));
    for raw in [
        "nope",
        r#"{"steps":[]}"#,
        r#"{"steps":[{"id":"A b","capability":"x","args":{}}]}"#,
        r#"{"steps":[{"id":"a","capability":"x","missing_hint":"y","args":{}}]}"#,
        r#"{"steps":[{"id":"a","args":{}}]}"#,
        r#"{"steps":[{"id":"a","capability":"x","args":{"k":{"from":"shell","cmd":"rm"}}}]}"#,
    ] {
        assert!(parse(raw).is_err(), "{raw}");
    }
    assert!(parse(&" ".repeat(40_000)).is_err());
}

#[test]
fn shadow_comparison_counts_agreement_with_the_legacy_path() {
    let plan = parse(GOOD).expect("parse");
    let same = compare(
        &plan,
        &["image.search", "telegram.send_photo", "email.send"],
    );
    assert!(same.matches());
    let drift = compare(&plan, &["image.search", "send_email"]);
    assert_eq!((drift.shared, drift.only_new, drift.only_old), (1, 2, 1));
}
