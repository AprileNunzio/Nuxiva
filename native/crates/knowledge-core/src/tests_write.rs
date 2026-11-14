use crate::tests::{T0, assert_user, conv, kn, me, node, pid, relate, remember};
use crate::{Change, Correction, Direction, Kind, KnowledgeError, Level, NeighborQuery, Query};

#[test]
fn relate_creates_then_reinforces_with_noisy_or() {
    let mut k = kn();
    let to = node(Kind::Place, "Roma");
    assert_eq!(
        relate(&mut k, "nunzio", "lives_in", &to, 600, Level::Private),
        Change::Created
    );
    assert_eq!(
        relate(&mut k, "nunzio", "lives_in", &to, 600, Level::Private),
        Change::Reinforced
    );
    let related = k
        .neighbors(&pid("nunzio"), &NeighborQuery::default())
        .unwrap_or_default();
    assert_eq!(related.len(), 1);
    assert_eq!(related.first().map(|r| r.confidence), Some(840));
}

#[test]
fn origin_caps_confidence() {
    let mut k = kn();
    let to = node(Kind::Place, "Milano");
    let ev = crate::Evidence {
        origin: crate::Origin::Inference,
        reference: String::new(),
        confidence: 1000,
    };
    let out = k.relate(
        &pid("nunzio"),
        &crate::Link {
            from: &me(),
            relation: "visited",
            to: &to,
            level: Level::Private,
        },
        &ev,
        T0,
    );
    assert!(out.is_ok());
    let related = k
        .neighbors(&pid("nunzio"), &NeighborQuery::default())
        .unwrap_or_default();
    assert_eq!(related.first().map(|r| r.confidence), Some(600));
}

#[test]
fn functional_relation_superseded_by_stronger_fact() {
    let mut k = kn();
    let rome = node(Kind::Place, "Roma");
    let turin = node(Kind::Place, "Torino");
    relate(&mut k, "nunzio", "lives_in", &rome, 500, Level::Private);
    assert_eq!(
        relate(&mut k, "nunzio", "lives_in", &turin, 800, Level::Private),
        Change::Superseded
    );
    assert_eq!(
        relate(&mut k, "nunzio", "lives_in", &rome, 300, Level::Private),
        Change::Contested
    );
}

#[test]
fn user_correction_prevails_over_later_extraction() {
    let mut k = kn();
    let rome = node(Kind::Place, "Roma");
    let turin = node(Kind::Place, "Torino");
    assert_user(&mut k, "nunzio", "lives_in", &rome);
    assert_eq!(
        relate(&mut k, "nunzio", "lives_in", &turin, 900, Level::Private),
        Change::Blocked
    );
    assert_user(&mut k, "nunzio", "lives_in", &turin);
    let active = k
        .neighbors(
            &pid("nunzio"),
            &NeighborQuery {
                relation: Some("lives_in".to_owned()),
                ..NeighborQuery::default()
            },
        )
        .unwrap_or_default();
    let live: Vec<_> = active
        .iter()
        .filter(|r| r.status == crate::Status::Active)
        .collect();
    assert_eq!(live.len(), 1);
    assert_eq!(live.first().map(|r| r.node.label.as_str()), Some("Torino"));
}

#[test]
fn refuted_fact_stays_refuted_for_automatic_sources() {
    let mut k = kn();
    let tea = node(Kind::Preference, "tè");
    relate(&mut k, "nunzio", "likes", &tea, 800, Level::Private);
    let refute = Correction::Refute {
        from: me(),
        relation: "likes".to_owned(),
        to: tea.clone(),
    };
    assert!(k.correct(&pid("nunzio"), &refute, T0).is_ok());
    assert_eq!(
        relate(&mut k, "nunzio", "likes", &tea, 900, Level::Private),
        Change::Blocked
    );
    assert_user(&mut k, "nunzio", "likes", &tea);
    assert_eq!(
        relate(&mut k, "nunzio", "likes", &tea, 900, Level::Private),
        Change::Reinforced
    );
}

#[test]
fn removed_node_is_not_recreated_by_extraction() {
    let mut k = kn();
    remember(&mut k, "nunzio", Kind::Object, "chitarra", Level::Private);
    let remove = Correction::Remove {
        node: node(Kind::Object, "chitarra"),
    };
    assert!(k.correct(&pid("nunzio"), &remove, T0).is_ok());
    let spec = crate::Spec {
        kind: Kind::Object,
        label: "chitarra",
        detail: None,
        level: Level::Private,
    };
    assert_eq!(
        k.remember(&pid("nunzio"), &spec, &conv(800), T0),
        Err(KnowledgeError::Forbidden)
    );
}

#[test]
fn rename_keeps_edges_and_updates_search() {
    let mut k = kn();
    relate(
        &mut k,
        "nunzio",
        "likes",
        &node(Kind::Preference, "caffe"),
        800,
        Level::Private,
    );
    let rename = Correction::Rename {
        node: node(Kind::Preference, "caffe"),
        label: "espresso".to_owned(),
    };
    assert!(k.correct(&pid("nunzio"), &rename, T0).is_ok());
    let hits = k
        .search(
            &pid("nunzio"),
            &Query {
                text: "espresso".to_owned(),
                ..Query::default()
            },
        )
        .unwrap_or_default();
    assert_eq!(hits.first().map(|h| h.label.as_str()), Some("espresso"));
    let out = k
        .neighbors(
            &pid("nunzio"),
            &NeighborQuery {
                direction: Direction::Out,
                ..NeighborQuery::default()
            },
        )
        .unwrap_or_default();
    assert_eq!(out.len(), 1);
}

#[test]
fn invalid_input_is_rejected() {
    let mut k = kn();
    let bad = node(Kind::Place, "Ro\u{0}ma");
    let ev = conv(800);
    let r = k.relate(
        &pid("nunzio"),
        &crate::Link {
            from: &me(),
            relation: "lives_in",
            to: &bad,
            level: Level::Private,
        },
        &ev,
        T0,
    );
    assert_eq!(r.map(|o| o.change), Err(KnowledgeError::Invalid));
    let rel = k.relate(
        &pid("nunzio"),
        &crate::Link {
            from: &me(),
            relation: "Bad Relation",
            to: &node(Kind::Place, "Roma"),
            level: Level::Private,
        },
        &ev,
        T0,
    );
    assert_eq!(rel.map(|o| o.change), Err(KnowledgeError::Invalid));
}
