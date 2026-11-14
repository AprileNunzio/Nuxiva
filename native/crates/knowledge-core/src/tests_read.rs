use crate::tests::{kn, me, node, pid, relate, remember};
use crate::{Direction, Extractor, Kind, Level, NeighborQuery, Query};

fn search(k: &crate::Knowledge, who: &str, text: &str, depth: usize) -> Vec<crate::Hit> {
    k.search(
        &pid(who),
        &Query {
            text: text.to_owned(),
            depth,
            ..Query::default()
        },
    )
    .unwrap_or_default()
}

#[test]
fn search_finds_by_meaning_of_similar_words() {
    let mut k = kn();
    remember(
        &mut k,
        "nunzio",
        Kind::Preference,
        "pasta alla carbonara",
        Level::Private,
    );
    remember(&mut k, "nunzio", Kind::Place, "Roma", Level::Private);
    let hits = search(&k, "nunzio", "carbonara", 0);
    assert_eq!(
        hits.first().map(|h| h.label.as_str()),
        Some("pasta alla carbonara")
    );
    let fuzzy = search(&k, "nunzio", "carbonaras", 0);
    assert_eq!(
        fuzzy.first().map(|h| h.label.as_str()),
        Some("pasta alla carbonara")
    );
}

#[test]
fn search_expands_through_relations() {
    let mut k = kn();
    relate(
        &mut k,
        "nunzio",
        "spouse",
        &node(Kind::Person, "Giulia"),
        900,
        Level::Private,
    );
    let giulia = node(Kind::Person, "Giulia");
    let ev = crate::tests::conv(900);
    let out = k.relate(
        &pid("nunzio"),
        &crate::Link {
            from: &giulia,
            relation: "likes",
            to: &node(Kind::Preference, "cioccolato"),
            level: Level::Private,
        },
        &ev,
        crate::tests::T0,
    );
    assert!(out.is_ok());
    let near = search(&k, "nunzio", "Giulia", 0);
    assert!(!near.iter().any(|h| h.label == "cioccolato"));
    let far = search(&k, "nunzio", "Giulia", 1);
    let found = far.iter().find(|h| h.label == "cioccolato");
    assert_eq!(found.and_then(|h| h.via.as_deref()), Some("likes"));
}

#[test]
fn neighbors_by_relation_and_path() {
    let mut k = kn();
    relate(
        &mut k,
        "nunzio",
        "spouse",
        &node(Kind::Person, "Giulia"),
        900,
        Level::Private,
    );
    relate(
        &mut k,
        "nunzio",
        "child",
        &node(Kind::Person, "Marco"),
        900,
        Level::Private,
    );
    let spouse = k
        .neighbors(
            &pid("nunzio"),
            &NeighborQuery {
                relation: Some("spouse".to_owned()),
                direction: Direction::Out,
                ..NeighborQuery::default()
            },
        )
        .unwrap_or_default();
    assert_eq!(spouse.len(), 1);
    assert_eq!(
        spouse.first().map(|r| r.node.label.as_str()),
        Some("Giulia")
    );
    let path = k
        .path(
            &pid("nunzio"),
            &node(Kind::Person, "Giulia"),
            &node(Kind::Person, "Marco"),
        )
        .unwrap_or(None);
    assert_eq!(path.map(|p| p.len()), Some(2));
    let none = k
        .path(&pid("nunzio"), &me(), &node(Kind::Person, "Marco"))
        .unwrap_or(None);
    assert_eq!(none.map(|p| p.len()), Some(1));
}

#[test]
fn extractor_reads_italian_and_english() {
    let e = Extractor::new().unwrap_or_else(|_| unreachable!("rules"));
    let facts = e
        .extract("Abito a Torino e lavoro come ingegnere. Non mi piace il pesce, mi piace il caffè. La mia moglie si chiama Giulia.")
        .unwrap_or_default();
    let has = |rel: &str, label: &str| {
        facts
            .iter()
            .any(|f| f.relation == rel && f.to.label == label)
    };
    assert!(has("lives_in", "Torino"));
    assert!(has("works_as", "ingegnere"));
    assert!(has("dislikes", "pesce"));
    assert!(has("likes", "caffè"));
    let en = e
        .extract("I live in Boston. I don't like olives. My dog is named Rex. Every morning I run in the park")
        .unwrap_or_default();
    assert!(
        en.iter()
            .any(|f| f.relation == "lives_in" && f.to.label == "Boston")
    );
    assert!(
        en.iter()
            .any(|f| f.relation == "dislikes" && f.to.label == "olives")
    );
    assert!(en.iter().any(|f| f.relation == "owns_pet"
        && f.to.label == "Rex"
        && f.detail.as_deref() == Some("dog")));
    assert!(en.iter().any(|f| f.relation == "has_habit"));
}

#[test]
fn extractor_rejects_control_and_oversize() {
    let e = Extractor::new().unwrap_or_else(|_| unreachable!("rules"));
    assert!(e.extract("abito a \u{0}Roma").is_err());
    assert!(e.extract(&"a".repeat(5_000)).is_err());
    assert!(
        e.extract("che bel tempo oggi")
            .unwrap_or_default()
            .is_empty()
    );
}
