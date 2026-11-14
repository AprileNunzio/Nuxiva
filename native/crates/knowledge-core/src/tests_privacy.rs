use std::sync::Arc;

use crate::tests::{T0, conv, kn, me, node, pid, relate, remember};
use crate::{
    Correction, Kind, Knowledge, KnowledgeError, KnowledgeSettings, Level, MasterKey,
    NeighborQuery, Query, Spec,
};

fn household(text: &str) -> Query {
    Query {
        text: text.to_owned(),
        household: true,
        ..Query::default()
    }
}

#[test]
fn family_sees_only_family_level_of_others() {
    let mut k = kn();
    remember(
        &mut k,
        "anna",
        Kind::Preference,
        "vino rosso",
        Level::Family,
    );
    remember(
        &mut k,
        "anna",
        Kind::Preference,
        "vino segreto",
        Level::Private,
    );
    remember(
        &mut k,
        "anna",
        Kind::Preference,
        "vino cifrato",
        Level::Secret,
    );
    let hits = k
        .search(&pid("nunzio"), &household("vino"))
        .unwrap_or_default();
    let labels: Vec<_> = hits.iter().map(|h| h.label.as_str()).collect();
    assert!(labels.contains(&"vino rosso"));
    assert!(!labels.contains(&"vino segreto"));
    assert!(!labels.contains(&"vino cifrato"));
    let own_only = k
        .search(
            &pid("nunzio"),
            &Query {
                text: "vino".to_owned(),
                ..Query::default()
            },
        )
        .unwrap_or_default();
    assert!(own_only.is_empty());
}

#[test]
fn guests_are_isolated_both_ways() {
    let mut k = kn();
    remember(&mut k, "ospite", Kind::Preference, "tisana", Level::Public);
    remember(&mut k, "nunzio", Kind::Preference, "tisana", Level::Public);
    let guest = k
        .search(&pid("ospite"), &household("tisana"))
        .unwrap_or_default();
    assert_eq!(guest.len(), 1);
    assert!(guest.iter().all(|h| h.owner == pid("ospite")));
    let family = k
        .search(&pid("nunzio"), &household("tisana"))
        .unwrap_or_default();
    assert!(family.iter().all(|h| h.owner == pid("nunzio")));
}

#[test]
fn consent_withdrawn_blocks_read_and_write() {
    let mut k = kn();
    remember(&mut k, "anna", Kind::Place, "Napoli", Level::Family);
    assert!(
        k.register(
            &pid("anna"),
            "Anna",
            nuxiva_context_core::Role::Family,
            false
        )
        .is_ok()
    );
    assert_eq!(
        k.search(&pid("anna"), &Query::default()).map(|h| h.len()),
        Err(KnowledgeError::Forbidden)
    );
    let hidden = k
        .search(&pid("nunzio"), &household("Napoli"))
        .unwrap_or_default();
    assert!(hidden.is_empty());
    let spec = Spec {
        kind: Kind::Place,
        label: "Bari",
        detail: None,
        level: Level::Family,
    };
    assert_eq!(
        k.remember(&pid("anna"), &spec, &conv(800), T0),
        Err(KnowledgeError::Forbidden)
    );
}

#[test]
fn unknown_person_cannot_read_or_write() {
    let mut k = kn();
    let spec = Spec {
        kind: Kind::Place,
        label: "Bari",
        detail: None,
        level: Level::Public,
    };
    assert_eq!(
        k.remember(&pid("intruso"), &spec, &conv(800), T0),
        Err(KnowledgeError::NotFound)
    );
    assert_eq!(
        k.neighbors(&pid("intruso"), &NeighborQuery::default())
            .map(|v| v.len()),
        Err(KnowledgeError::NotFound)
    );
}

#[test]
fn secret_detail_is_encrypted_and_revealed_only_on_request() {
    let mut k = kn();
    let spec = Spec {
        kind: Kind::Concept,
        label: "codice cassaforte",
        detail: Some("4821"),
        level: Level::Secret,
    };
    assert!(k.remember(&pid("nunzio"), &spec, &conv(900), T0).is_ok());
    let dump = serde_json::to_string(
        &k.partition(&pid("nunzio"))
            .map(|p| p.nodes.clone())
            .unwrap_or_default(),
    )
    .unwrap_or_default();
    assert!(!dump.contains("4821"));
    let plain = k
        .search(
            &pid("nunzio"),
            &Query {
                text: "cassaforte".to_owned(),
                ..Query::default()
            },
        )
        .unwrap_or_default();
    assert_eq!(plain.first().and_then(|h| h.detail.clone()), None);
    let shown = k
        .search(
            &pid("nunzio"),
            &Query {
                text: "cassaforte".to_owned(),
                reveal: true,
                ..Query::default()
            },
        )
        .unwrap_or_default();
    assert_eq!(
        shown.first().and_then(|h| h.detail.clone()),
        Some("4821".to_owned())
    );
    let by_detail = k
        .search(
            &pid("nunzio"),
            &Query {
                text: "4821".to_owned(),
                ..Query::default()
            },
        )
        .unwrap_or_default();
    assert!(by_detail.is_empty());
}

#[test]
fn secret_without_key_fails_closed() {
    let mut k =
        Knowledge::new(KnowledgeSettings::default(), None).unwrap_or_else(|_| unreachable!());
    assert!(
        k.register(
            &pid("nunzio"),
            "Nunzio",
            nuxiva_context_core::Role::Family,
            true
        )
        .is_ok()
    );
    let spec = Spec {
        kind: Kind::Concept,
        label: "pin",
        detail: Some("1234"),
        level: Level::Secret,
    };
    assert_eq!(
        k.remember(&pid("nunzio"), &spec, &conv(900), T0),
        Err(KnowledgeError::Seal)
    );
}

#[test]
fn wrong_key_cannot_open_detail() {
    let mut k = kn();
    let spec = Spec {
        kind: Kind::Concept,
        label: "pin",
        detail: Some("1234"),
        level: Level::Secret,
    };
    assert!(k.remember(&pid("nunzio"), &spec, &conv(900), T0).is_ok());
    k.key = Some(Arc::new(MasterKey::from_key([1; 32])));
    let r = k.search(
        &pid("nunzio"),
        &Query {
            text: "pin".to_owned(),
            reveal: true,
            ..Query::default()
        },
    );
    assert_eq!(r.map(|h| h.len()), Err(KnowledgeError::Seal));
}

#[test]
fn restricting_a_node_raises_incident_edges() {
    let mut k = kn();
    relate(
        &mut k,
        "anna",
        "likes",
        &node(Kind::Preference, "yoga"),
        800,
        Level::Family,
    );
    let restrict = Correction::Restrict {
        node: node(Kind::Preference, "yoga"),
        level: Level::Private,
    };
    assert!(k.correct(&pid("anna"), &restrict, T0).is_ok());
    let hidden = k
        .search(&pid("nunzio"), &household("yoga"))
        .unwrap_or_default();
    assert!(hidden.is_empty());
    let _ = me();
}
