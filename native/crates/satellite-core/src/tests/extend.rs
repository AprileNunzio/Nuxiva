use super::{Fixture, base};
use crate::backends::{builtin, load_extensions, merge, parse};
use crate::probe::profile;

const KENDRYTE: &str = r#"{
  "id": "kendryte-kpu",
  "vendor": "Canaan",
  "kind": "npu",
  "devices": ["/dev/kpu0"],
  "runtimes": ["libnncase.so"],
  "tasks": ["wake_word", "vad", "vision"],
  "priority": 90
}"#;

#[test]
fn any_chip_can_be_added_with_a_json_descriptor() -> Result<(), String> {
    let fx = Fixture::new("extend")?;
    base(&fx, 2, 1024 * 1024)?;
    fx.file("/dev/kpu0", "")?
        .file("/usr/local/lib/libnncase.so.2", "")?
        .file("/etc/nuxiva/accelerators.d/kendryte.json", KENDRYTE)?
        .file(
            "/etc/nuxiva/accelerators.d/broken.json",
            "{\"id\": \"../x\"}",
        )?
        .file("/etc/nuxiva/accelerators.d/ignored.txt", "x")?;
    let (extensions, rejected) = load_extensions(&fx.path().join("etc/nuxiva/accelerators.d"));
    assert_eq!(extensions.len(), 1);
    assert_eq!(rejected.len(), 1);
    let found = profile(&fx.root(), &merge(builtin(), extensions), &[]);
    assert!(
        found
            .accelerators
            .first()
            .is_some_and(|a| a.id == "kendryte-kpu" && a.ready)
    );
    Ok(())
}

#[test]
fn hostile_descriptors_are_rejected() {
    let cases = [
        (
            r#"{"id":"x","devices":["/dev/a"],"tasks":["vad"]}"#,
            "invalid_id",
        ),
        (
            r#"{"id":"cpu","devices":["/dev/a"],"tasks":["vad"]}"#,
            "invalid_id",
        ),
        (
            r#"{"id":"abc","kind":"cpu","devices":["/dev/a"],"tasks":["vad"]}"#,
            "invalid_kind",
        ),
        (
            r#"{"id":"abc","devices":["/etc/shadow"],"tasks":["vad"]}"#,
            "invalid_device",
        ),
        (
            r#"{"id":"abc","devices":["/dev/../etc/shadow"],"tasks":["vad"]}"#,
            "invalid_device",
        ),
        (
            r#"{"id":"abc","devices":["/dev/a"],"runtimes":["../../evil.so"],"tasks":["vad"]}"#,
            "invalid_runtime",
        ),
        (
            r#"{"id":"abc","modules":["Bad Name"],"tasks":["vad"]}"#,
            "invalid_driver",
        ),
        (
            r#"{"id":"abc","devices":["/dev/a"],"tasks":[]}"#,
            "no_tasks",
        ),
        (r#"{"id":"abc","tasks":["vad"]}"#, "no_evidence"),
        (
            r#"{"id":"abc","devices":["/dev/a"],"tasks":["vad"],"exec":"rm"}"#,
            "invalid_json",
        ),
    ];
    for (text, reason) in cases {
        assert_eq!(parse(text).err(), Some(reason), "{text}");
    }
}

#[test]
fn extension_overrides_builtin_with_the_same_id() -> Result<(), String> {
    let custom =
        parse(r#"{"id":"hailo","vendor":"Hailo","devices":["/dev/hailo9"],"tasks":["vision"]}"#)?;
    let merged = merge(builtin(), vec![custom]);
    let hailo: Vec<_> = merged.iter().filter(|d| d.id == "hailo").collect();
    assert_eq!(hailo.len(), 1);
    assert_eq!(
        hailo.first().map(|d| d.devices.clone()),
        Some(vec!["/dev/hailo9".to_owned()])
    );
    Ok(())
}

#[test]
fn builtin_catalog_is_itself_valid() {
    for descriptor in builtin().into_iter().filter(|d| d.id != "cpu") {
        let text = serde_json::to_string(&descriptor).unwrap_or_default();
        assert!(parse(&text).is_ok(), "{}", descriptor.id);
    }
}
