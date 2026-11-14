use std::sync::Arc;

use nuxiva_context_core::{PersonId, Role};

use crate::{
    Correction, Evidence, Kind, Knowledge, KnowledgeSettings, Level, Link, MasterKey, NodeRef,
    Origin, Spec,
};

pub(crate) const DAY: u64 = 86_400_000;
pub(crate) const T0: u64 = 1_800_000_000_000;

pub(crate) fn pid(text: &str) -> PersonId {
    PersonId::new(text).unwrap_or_else(|_| unreachable!("fixture id"))
}

pub(crate) fn kn() -> Knowledge {
    let mut kn = Knowledge::new(
        KnowledgeSettings::default(),
        Some(Arc::new(MasterKey::from_key([9; 32]))),
    )
    .unwrap_or_else(|_| unreachable!("settings"));
    for (id, name, role) in [
        ("nunzio", "Nunzio", Role::Family),
        ("anna", "Anna", Role::Family),
        ("ospite", "Ospite", Role::Guest),
    ] {
        assert!(kn.register(&pid(id), name, role, true).is_ok());
    }
    kn
}

pub(crate) fn conv(confidence: u32) -> Evidence {
    Evidence {
        origin: Origin::Conversation,
        reference: "chat".to_owned(),
        confidence,
    }
}

pub(crate) fn node(kind: Kind, label: &str) -> NodeRef {
    NodeRef {
        kind,
        label: label.to_owned(),
    }
}

pub(crate) fn me() -> NodeRef {
    node(Kind::Person, crate::SELF_KEY)
}

pub(crate) fn relate(
    kn: &mut Knowledge,
    who: &str,
    relation: &str,
    to: &NodeRef,
    confidence: u32,
    level: Level,
) -> crate::Change {
    kn.relate(
        &pid(who),
        &Link {
            from: &me(),
            relation,
            to,
            level,
        },
        &conv(confidence),
        T0,
    )
    .map_or_else(|e| unreachable!("relate failed: {e}"), |o| o.change)
}

pub(crate) fn get(value: &serde_json::Value, pointer: &str) -> serde_json::Value {
    value
        .pointer(pointer)
        .cloned()
        .unwrap_or(serde_json::Value::Null)
}

pub(crate) fn remember(kn: &mut Knowledge, who: &str, kind: Kind, label: &str, level: Level) {
    let spec = Spec {
        kind,
        label,
        detail: None,
        level,
    };
    assert!(kn.remember(&pid(who), &spec, &conv(800), T0).is_ok());
}

pub(crate) fn assert_user(kn: &mut Knowledge, who: &str, relation: &str, to: &NodeRef) {
    let c = Correction::Assert {
        from: me(),
        relation: relation.to_owned(),
        to: to.clone(),
        level: Level::Private,
    };
    assert!(kn.correct(&pid(who), &c, T0).is_ok());
}
