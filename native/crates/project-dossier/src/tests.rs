use std::collections::{BTreeMap, BTreeSet};

use capability_registry::Role;

use crate::{Dossier, DossierError, REQUIRED, SectionRef, parse, skeleton};

fn full() -> Dossier {
    let mut dossier = Dossier::new();
    for name in REQUIRED {
        dossier
            .set(name, &skeleton(name).expect("skeleton"), "initial")
            .expect("set");
    }
    dossier
}

fn reference(file: &str, section: &str) -> SectionRef {
    SectionRef {
        file: file.into(),
        section: section.into(),
    }
}

#[test]
fn every_standard_file_has_a_valid_skeleton() {
    for name in REQUIRED {
        let text = skeleton(name).expect("skeleton");
        assert!(parse(name, &text).is_ok(), "{name}");
    }
    assert!(skeleton("unknown").is_none());
}

#[test]
fn a_project_cannot_start_until_every_file_exists_and_is_approved() {
    let mut dossier = Dossier::new();
    assert!(matches!(dossier.ready(), Err(DossierError::Missing(_))));
    dossier
        .set("principio", &skeleton("principio").expect("s"), "x")
        .expect("set");
    assert!(matches!(
        dossier.approve(Role::Owner),
        Err(DossierError::Missing(_))
    ));
    let mut dossier = full();
    assert_eq!(dossier.ready(), Err(DossierError::NotApproved));
    assert_eq!(dossier.approve(Role::Guest), Err(DossierError::RoleDenied));
    dossier.approve(Role::Family).expect("approve");
    assert!(dossier.ready().is_ok());
}

#[test]
fn any_change_after_approval_requires_a_new_approval_and_is_logged() {
    let mut dossier = full();
    dossier.approve(Role::Owner).expect("approve");
    let revised = skeleton("grafica")
        .expect("s")
        .replace("To be written.", "Dark and calm.");
    let changed = dossier
        .set("grafica", &revised, "client asked for a dark theme")
        .expect("set");
    assert_eq!(changed.len(), 3);
    assert_eq!(dossier.ready(), Err(DossierError::NotApproved));
    assert_eq!(
        dossier.log(),
        ["revise grafica: client asked for a dark theme"]
    );
}

#[test]
fn only_changed_sections_invalidate_the_steps_that_cited_them() {
    let mut dossier = full();
    let revised = skeleton("sicurezza")
        .expect("s")
        .replacen("To be written.", "Tokens expire.", 1);
    let changed = dossier.set("sicurezza", &revised, "r").expect("set");
    assert_eq!(changed, vec![reference("sicurezza", "threats")]);
    let used = BTreeMap::from([
        ("a".to_owned(), vec![reference("sicurezza", "threats")]),
        ("b".to_owned(), vec![reference("grafica", "style")]),
    ]);
    assert_eq!(Dossier::invalidated(&changed, &used), vec!["a"]);
}

#[test]
fn selection_loads_only_relevant_sections_within_the_token_budget() {
    let dossier = full();
    let picked = dossier.select("which capabilities are forbidden", 1_500);
    assert_eq!(
        picked.first().map(|p| p.reference.cite()),
        Some("sicurezza#limits".to_owned())
    );
    assert!(picked.len() < 6);
    assert!(dossier.select("forbidden", 0).is_empty());
    let huge = dossier.select("data modules layout style", 1_000_000);
    let tokens: usize = huge
        .iter()
        .map(|p| (p.summary.len() + p.body.len()).div_ceil(4))
        .sum();
    assert!(tokens <= 1_500 + huge.len() * 2);
}

#[test]
fn the_security_file_can_only_restrict_never_extend() {
    let mut dossier = full();
    let text = "# sicurezza\n\n## limits - Forbidden capabilities\ndeny: files.delete\ndeny: admin.shell\nallow: payments.charge\n\n## threats - Risks\nx\n\n## data - Data\nx\n";
    dossier.set("sicurezza", text, "r").expect("set");
    let allowed: BTreeSet<String> = ["files.delete", "image.search", "admin.shell"]
        .map(String::from)
        .into();
    let result = dossier.restrict(&allowed);
    assert_eq!(result, BTreeSet::from(["image.search".to_owned()]));
    assert!(!result.contains("payments.charge"));
}

#[test]
fn malformed_files_are_rejected() {
    for text in [
        "no headings at all",
        "# t\n\n## BadId - summary\nbody",
        "# t\n\n## a - s\nx\n\n## a - again\ny",
        "# t\n\n## a\nbody",
        "stray text\n## a - s\nbody",
        "# t\n\n## a - s\nbad\u{7}char",
    ] {
        assert!(parse("principio", text).is_err(), "{text}");
    }
    assert!(parse("Bad Name", "# t\n## a - s\nb").is_err());
    assert!(parse("principio", &"x".repeat(200_000)).is_err());
}
