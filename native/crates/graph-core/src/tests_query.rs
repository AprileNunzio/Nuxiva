use crate::tests::fixture;
use crate::{
    EdgeKind, Graph, GraphError, GraphSettings, NodeKind, build, impact, locate, neighborhood,
    pack, path, resolve,
};

fn graph() -> Graph {
    build(&fixture(), &GraphSettings::default()).expect("build")
}

fn paths(items: &[crate::Reach]) -> Vec<&str> {
    items.iter().map(|r| r.hit.path.as_str()).collect()
}

#[test]
fn locate_ranks_exact_then_prefix_then_substring() {
    let g = graph();
    let hits = locate(&g, "util", &GraphSettings::default());
    let names: Vec<&str> = hits.iter().map(|h| h.name.as_str()).collect();
    assert_eq!(names.first().copied(), Some("util"));
    assert!(names.contains(&"crates/a/src/util.rs"));
    assert!(locate(&g, "", &GraphSettings::default()).is_empty());
    assert!(locate(&g, &"x".repeat(500), &GraphSettings::default()).is_empty());
    assert!(locate(&g, "zzzzzz", &GraphSettings::default()).is_empty());
    let capped = locate(
        &g,
        "e",
        &GraphSettings {
            max_results: 3,
            ..GraphSettings::default()
        },
    );
    assert_eq!(capped.len(), 3);
}

#[test]
fn locate_is_case_insensitive() {
    let g = graph();
    assert_eq!(
        locate(&g, "ENGINE", &GraphSettings::default())
            .first()
            .map(|h| h.name.as_str()),
        Some("Engine")
    );
}

#[test]
fn resolve_accepts_file_package_and_unique_symbol() {
    let g = graph();
    assert!(resolve(&g, "app/main.py").is_ok());
    assert!(resolve(&g, "nuxiva-a").is_ok());
    assert!(resolve(&g, "Engine").is_ok());
    assert_eq!(resolve(&g, "nope"), Err(GraphError::Unknown));
    assert_eq!(resolve(&g, "start"), resolve(&g, "start"));
}

#[test]
fn impact_lists_dependents_transitively() {
    let g = graph();
    let s = GraphSettings::default();
    let direct = impact(&g, "crates/a/src/deep/inner.rs", 1, &s).expect("impact");
    assert!(paths(&direct.items).contains(&"crates/a/src/util.rs"));
    assert!(!paths(&direct.items).contains(&"crates/a/src/lib.rs"));
    let deep = impact(&g, "crates/a/src/deep/inner.rs", 4, &s).expect("impact");
    assert!(paths(&deep.items).contains(&"crates/a/src/lib.rs"));
    assert!(deep.items.iter().all(|r| r.via != EdgeKind::Declares));
    assert_eq!(deep.graph_ref, g.reference());
}

#[test]
fn impact_of_a_symbol_uses_its_file() {
    let g = graph();
    let s = GraphSettings::default();
    let by_symbol = impact(&g, "Thing", 3, &s).expect("impact");
    let by_file = impact(&g, "crates/a/src/deep/inner.rs", 3, &s).expect("impact");
    assert_eq!(by_symbol.items, by_file.items);
}

#[test]
fn impact_of_a_package_reaches_dependent_packages() {
    let g = graph();
    let reached = impact(&g, "nuxiva-a", 2, &GraphSettings::default()).expect("impact");
    assert!(
        reached
            .items
            .iter()
            .any(|r| r.hit.kind == NodeKind::Package && r.hit.name == "nuxiva-b")
    );
}

#[test]
fn neighborhood_is_bounded_and_breadth_first() {
    let g = graph();
    let s = GraphSettings::default();
    let near = neighborhood(&g, "crates/a/src/util.rs", 1, &s).expect("near");
    assert!(near.items.iter().all(|r| r.depth == 1));
    let far = neighborhood(&g, "crates/a/src/util.rs", 3, &s).expect("far");
    assert!(far.items.len() > near.items.len());
    assert!(far.items.is_sorted_by_key(|r| r.depth));
    let tiny = neighborhood(
        &g,
        "crates/a/src/util.rs",
        3,
        &GraphSettings {
            max_results: 2,
            ..s
        },
    )
    .expect("tiny");
    assert!(tiny.truncated && tiny.items.len() == 2);
}

#[test]
fn depth_is_clamped() {
    let g = graph();
    let s = GraphSettings {
        max_depth: 1,
        ..GraphSettings::default()
    };
    let a = neighborhood(&g, "crates/a/src/util.rs", 99, &s).expect("a");
    let b = neighborhood(&g, "crates/a/src/util.rs", 1, &s).expect("b");
    assert_eq!(a.items, b.items);
    assert_eq!(
        neighborhood(&g, "crates/a/src/util.rs", 0, &s)
            .expect("zero")
            .items,
        b.items
    );
}

#[test]
fn path_finds_shortest_route_and_directions() {
    let g = graph();
    let s = GraphSettings::default();
    let route = path(&g, "crates/a/src/lib.rs", "crates/a/src/deep/inner.rs", &s).expect("path");
    assert_eq!(
        route.first().map(|x| x.hit.path.as_str()),
        Some("crates/a/src/lib.rs")
    );
    assert_eq!(
        route.last().map(|x| x.hit.path.as_str()),
        Some("crates/a/src/deep/inner.rs")
    );
    assert!(route.len() <= 3);
    assert!(route.first().is_some_and(|x| x.via.is_none()));
    assert_eq!(
        path(&g, "app/main.py", "app/main.py", &s)
            .expect("same")
            .len(),
        1
    );
    assert_eq!(
        path(&g, "app/main.py", "assets/logo.png", &s).err(),
        Some(GraphError::Unknown)
    );
    assert_eq!(
        path(&g, "app/main.py", "nope", &s).err(),
        Some(GraphError::Unknown)
    );
}

#[test]
fn pack_describes_focus_within_budget() {
    let g = graph();
    let s = GraphSettings::default();
    let pack_all = pack(
        &g,
        &["crates/a/src/util.rs".to_owned(), "app/main.py".to_owned()],
        10_000,
        &s,
    )
    .expect("pack");
    assert!(
        pack_all
            .text
            .starts_with(&format!("graph_ref={}", g.reference()))
    );
    assert!(pack_all.text.contains("## crates/a/src/util.rs (rust)"));
    assert!(pack_all.text.contains("symbols: LIMIT, helper"));
    assert!(pack_all.text.contains("used_by: "));
    assert!(!pack_all.truncated);
    let tight = pack(
        &g,
        &["crates/a/src/util.rs".to_owned(), "app/main.py".to_owned()],
        150,
        &s,
    )
    .expect("pack");
    assert!(tight.truncated && tight.text.chars().count() <= 150);
    assert_eq!(
        pack(&g, &["nope".to_owned()], 1_000, &s).err(),
        Some(GraphError::Unknown)
    );
}

#[test]
fn queries_on_empty_graph_are_safe() {
    let g = build(&crate::MemorySource::new(), &GraphSettings::default()).expect("build");
    let s = GraphSettings::default();
    assert!(locate(&g, "a", &s).is_empty());
    assert_eq!(impact(&g, "a", 2, &s).err(), Some(GraphError::Unknown));
    assert!(
        pack(&g, &[], 100, &s)
            .expect("pack")
            .text
            .contains("files=0")
    );
}
