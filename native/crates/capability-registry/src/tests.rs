use std::collections::BTreeSet;
use std::path::Path;

use crate::{Contract, Effect, Origin, Param, Registry, RegistryError, Role, State, ValueType};

fn shipped() -> Registry {
    let path =
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../contracts/capabilities/tools.json");
    Registry::from_document(&std::fs::read(path).expect("read")).expect("load")
}

fn contract(id: &str, origin: Origin) -> Contract {
    Contract {
        id: id.into(),
        version: 1,
        origin,
        summary: "Search images on the web by subject.".into(),
        inputs: vec![Param {
            name: "subject".into(),
            ty: ValueType::Text,
            required: true,
        }],
        output: ValueType::Image,
        effects: BTreeSet::from([Effect::Read]),
        reversible: true,
        min_role: Role::Family,
        nodes: BTreeSet::from(["server".into()]),
        tags: BTreeSet::new(),
        state: State::Active,
    }
}

#[test]
fn every_shipped_tool_has_a_valid_contract() {
    let registry = shipped();
    assert_eq!(registry.len(), 132);
    for id in registry.ids() {
        registry.get(id).expect("get").validate().expect(id);
    }
}

#[test]
fn contracts_cover_every_python_tool() {
    let registry = shipped();
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../installer_wizard/agenti");
    let mut found = BTreeSet::new();
    let mut stack = vec![root];
    while let Some(dir) = stack.pop() {
        for entry in std::fs::read_dir(&dir).expect("dir").flatten() {
            let path = entry.path();
            if path.is_dir() {
                stack.push(path);
            } else if path.extension().is_some_and(|e| e == "py") {
                let text = std::fs::read_to_string(&path).unwrap_or_default();
                for line in text.lines() {
                    if let Some(rest) = line.trim_start().strip_prefix("@tool(\"") {
                        if let Some(end) = rest.find('"') {
                            found.insert(rest[..end].to_owned());
                        }
                    }
                }
            }
        }
    }
    let present: BTreeSet<String> = registry.ids().map(str::to_owned).collect();
    let missing: Vec<_> = found.difference(&present).collect();
    assert!(missing.is_empty(), "{missing:?}");
}

#[test]
fn retrieval_recall_at_eight_on_real_requests() {
    let registry = shipped();
    let cases = [
        ("send an email with an attachment", "send_email"),
        ("what time is it", "now"),
        ("show me the football table", "football_table"),
        ("look up recent facts on the internet", "web_research"),
        ("read a word document", "read_file"),
        ("copy this folder", "copy"),
        ("remove a file to the trash", "delete"),
        ("find files by name", "find_files"),
        ("schedule a task for tomorrow", "schedule_task"),
        ("list the scheduled tasks", "list_tasks"),
        ("create an automation with triggers", "create_automation"),
        ("block an ip address in the firewall", "firewall_block"),
        ("turn on a light in home assistant", "ha_call_service"),
        ("play a tv channel", "tv_play_channel"),
        ("transcribe an audio recording", "transcribe_audio"),
        ("create a powerpoint presentation", "create_document"),
        ("find the email address of a person", "find_contact"),
        ("show a 3d model", "show_model"),
        ("restart a systemd service", "service_control"),
        ("install a debian package", "apt_install"),
        ("kill a running process", "process_kill"),
        ("how much memory is the server using", "debian_status"),
        ("show the camera sensor state", "camsense_state"),
        ("download a web page", "http_get"),
        ("compress a folder into a zip", "zip"),
        ("what did nuxiva learn about my habits", "what_i_learned"),
        ("connect the vpn", "vpn_connect"),
        ("remember a fact about a household member", "person_learn"),
        ("ask an expert a question", "expert_ask"),
        ("open a widget on the display", "show_widget"),
    ];
    let hits = cases
        .iter()
        .filter(|(query, wanted)| {
            registry
                .retrieve(query, 8, Role::Owner)
                .iter()
                .any(|hit| hit.id == *wanted)
        })
        .count();
    assert!(hits * 100 >= cases.len() * 95, "{hits}/{}", cases.len());
}

#[test]
fn retrieval_never_returns_what_the_role_cannot_use() {
    let registry = shipped();
    let hits = registry.retrieve("run any bash command as administrator", 8, Role::Guest);
    for hit in &hits {
        let found = registry.get(&hit.id).expect("get");
        assert!(Role::Guest.permits(found.min_role), "{}", hit.id);
    }
    assert!(!hits.iter().any(|h| h.id == "debian_shell"));
    let owner = registry.retrieve("run any bash command as administrator", 3, Role::Owner);
    assert_eq!(owner.first().map(|h| h.id.as_str()), Some("debian_shell"));
}

#[test]
fn untrusted_origins_enter_degraded_with_maximum_effects() {
    let mut registry = Registry::new();
    let before = registry.generation();
    registry
        .insert(contract("image.search", Origin::Mcp))
        .expect("insert");
    assert!(registry.generation() > before);
    let stored = registry.get("image.search").expect("get");
    assert_eq!(stored.state, State::Degraded);
    assert_eq!(stored.effects, Effect::all());
    assert!(stored.requires_approval());
    assert!(
        registry
            .retrieve("search images", 8, Role::Owner)
            .is_empty()
    );
    registry
        .activate("image.search", BTreeSet::from([Effect::Read]))
        .expect("activate");
    assert_eq!(registry.retrieve("search images", 8, Role::Owner).len(), 1);
    assert_eq!(registry.untrusted(), vec!["image.search"]);
}

#[test]
fn revoked_capabilities_are_not_selectable_and_cannot_return() {
    let mut registry = Registry::new();
    registry
        .insert(contract("image.search", Origin::Local))
        .expect("insert");
    registry.revoke("image.search").expect("revoke");
    assert!(
        registry
            .retrieve("search images", 8, Role::Owner)
            .is_empty()
    );
    assert!(
        registry
            .activate("image.search", BTreeSet::from([Effect::Read]))
            .is_err()
    );
}

#[test]
fn duplicates_need_a_higher_version_from_the_same_origin() {
    let mut registry = Registry::new();
    registry
        .insert(contract("image.search", Origin::Local))
        .expect("insert");
    assert!(matches!(
        registry.insert(contract("image.search", Origin::Local)),
        Err(RegistryError::Duplicate(_))
    ));
    assert!(matches!(
        registry.insert(contract("image.search", Origin::Generated)),
        Err(RegistryError::Duplicate(_))
    ));
    let mut newer = contract("image.search", Origin::Local);
    newer.version = 2;
    registry.insert(newer).expect("upgrade");
}

#[test]
fn invalid_contracts_are_rejected() {
    let mut bad_id = contract("Image Search", Origin::Local);
    assert!(bad_id.validate().is_err());
    bad_id.id = "ok".into();
    assert!(bad_id.validate().is_ok());
    let mut no_effects = contract("a", Origin::Local);
    no_effects.effects.clear();
    assert!(no_effects.validate().is_err());
    let mut long = contract("a", Origin::Local);
    long.summary = "word ".repeat(80);
    assert!(long.validate().is_err());
    let mut twin = contract("a", Origin::Local);
    twin.inputs.push(twin.inputs[0].clone());
    assert!(twin.validate().is_err());
    let mut lying = contract("a", Origin::Local);
    lying.effects.insert(Effect::SendExternal);
    assert!(lying.validate().is_err());
}

#[test]
fn documents_reject_unknown_fields_and_wrong_schema() {
    assert!(Registry::from_document(br#"{"schema":2,"capabilities":[]}"#).is_err());
    assert!(Registry::from_document(br#"{"schema":1,"capabilities":[],"x":1}"#).is_err());
    assert!(Registry::from_document(b"not json").is_err());
}

#[test]
fn typed_lookup_links_producers_and_consumers() {
    let mut registry = Registry::new();
    registry
        .insert(contract("image.search", Origin::Local))
        .expect("insert");
    let mut sender = contract("telegram.send_photo", Origin::Local);
    sender.summary = "Send a photo on Telegram.".into();
    sender.inputs = vec![Param {
        name: "photo".into(),
        ty: ValueType::Image,
        required: true,
    }];
    sender.output = ValueType::Text;
    sender.effects = BTreeSet::from([Effect::SendExternal]);
    sender.reversible = false;
    registry.insert(sender).expect("insert");
    assert_eq!(
        registry.producers_of(ValueType::Image, Role::Owner),
        vec!["image.search"]
    );
    assert_eq!(
        registry.consumers_of(ValueType::Image, Role::Owner),
        vec!["telegram.send_photo"]
    );
}
