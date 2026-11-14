use crate::tests::{DAY, T0, kn, node, pid, relate, remember};
use crate::{Correction, Kind, Level, Query};

#[test]
fn consolidation_decays_and_forgets_only_weak_unpinned() {
    let mut k = kn();
    let who = pid("nunzio");
    remember(
        &mut k,
        "nunzio",
        Kind::Event,
        "riunione condominio",
        Level::Private,
    );
    remember(
        &mut k,
        "nunzio",
        Kind::Event,
        "cena importante",
        Level::Private,
    );
    let pin = Correction::SetDetail {
        node: node(Kind::Event, "cena importante"),
        detail: Some("da ricordare".to_owned()),
    };
    assert!(k.correct(&who, &pin, T0).is_ok());
    assert!(k.consolidate(&who, T0).is_ok());
    let later = T0 + 400 * DAY;
    let report = k.consolidate(&who, later).unwrap_or_default();
    assert!(report.forgotten_nodes >= 1);
    let left = k
        .search(
            &who,
            &Query {
                text: "cena importante".to_owned(),
                ..Query::default()
            },
        )
        .unwrap_or_default();
    assert_eq!(
        left.first().map(|h| h.label.as_str()),
        Some("cena importante")
    );
    let gone = k
        .search(
            &who,
            &Query {
                text: "riunione condominio".to_owned(),
                ..Query::default()
            },
        )
        .unwrap_or_default();
    assert!(gone.is_empty());
}

#[test]
fn use_reinforces_against_forgetting() {
    let mut k = kn();
    let who = pid("nunzio");
    remember(
        &mut k,
        "nunzio",
        Kind::Preference,
        "tè verde",
        Level::Private,
    );
    remember(
        &mut k,
        "nunzio",
        Kind::Preference,
        "tè nero",
        Level::Private,
    );
    assert!(k.consolidate(&who, T0).is_ok());
    let mut now = T0;
    for _ in 0..20 {
        now += 30 * DAY;
        let hits = k
            .search(
                &who,
                &Query {
                    text: "tè verde".to_owned(),
                    ..Query::default()
                },
            )
            .unwrap_or_default();
        let ids: Vec<_> = hits
            .iter()
            .filter(|h| h.label == "tè verde")
            .map(|h| h.id.clone())
            .collect();
        k.touch(&who, &ids, now);
        assert!(k.consolidate(&who, now).is_ok());
    }
    let alive = k
        .search(
            &who,
            &Query {
                text: "tè".to_owned(),
                limit: 10,
                ..Query::default()
            },
        )
        .unwrap_or_default();
    assert!(alive.iter().any(|h| h.label == "tè verde"));
    assert!(!alive.iter().any(|h| h.label == "tè nero"));
}

#[test]
fn near_duplicates_merge_and_keep_edges() {
    let mut k = kn();
    let who = pid("nunzio");
    relate(
        &mut k,
        "nunzio",
        "likes",
        &node(Kind::Preference, "cioccolato fondente"),
        700,
        Level::Private,
    );
    relate(
        &mut k,
        "nunzio",
        "likes",
        &node(Kind::Preference, "Cioccolato  fondente"),
        700,
        Level::Private,
    );
    remember(
        &mut k,
        "nunzio",
        Kind::Preference,
        "cioccolato fondente extra",
        Level::Private,
    );
    let report = k.consolidate(&who, T0).unwrap_or_default();
    let stats = k
        .partition(&who)
        .map_or((0, 0), |p| (p.nodes.len(), p.edges.len()));
    assert!(report.merged <= 1);
    assert_eq!(stats.1, 1);
}

#[test]
fn habit_emerges_from_repeated_observations() {
    let mut k = kn();
    let who = pid("nunzio");
    let hour = 7 * 3_600_000_u64;
    let base = (T0 / DAY) * DAY + hour;
    let mut last = None;
    for day in 0..4_u64 {
        last = k
            .observe(&who, "corsa mattutina", base + day * DAY)
            .unwrap_or(None);
    }
    assert!(last.is_some());
    let hits = k
        .search(
            &who,
            &Query {
                text: "corsa mattutina".to_owned(),
                kinds: vec![Kind::Habit],
                ..Query::default()
            },
        )
        .unwrap_or_default();
    assert!(hits.first().is_some_and(|h| h.kind == Kind::Habit));
    let few = k.observe(&who, "altro evento", base).unwrap_or(None);
    assert!(few.is_none());
}
