use std::path::Path;

use serde_json::json;

use super::{Fixture, base, camera, microphone_and_speaker};
use crate::agent::service::{existing_groups, unit};
use crate::agent::{Command, Runner, next_interval, parse_commands};
use crate::backends::builtin;

fn at(value: &serde_json::Value, pointer: &str) -> serde_json::Value {
    value.pointer(pointer).cloned().unwrap_or_default()
}

#[test]
fn commands_are_bounded_and_unknown_ones_are_not_executed() {
    let reply = json!({"commands": ["adapt", "restart", "identify", "rm -rf /", 7, "a", "b"]});
    let commands = parse_commands(&reply);
    assert_eq!(commands.len(), 4);
    assert_eq!(commands.first(), Some(&Command::Adapt));
    assert_eq!(
        commands.get(3),
        Some(&Command::Unsupported("rm -rf /".into()))
    );
    assert!(parse_commands(&json!({"commands": "adapt"})).is_empty());
}

#[test]
fn heartbeat_interval_is_clamped() {
    assert_eq!(next_interval(&json!({"heartbeat": 1})), 10);
    assert_eq!(next_interval(&json!({"heartbeat": 99999})), 300);
    assert_eq!(next_interval(&json!({})), 30);
}

#[test]
fn heartbeat_report_matches_the_server_contract() -> Result<(), String> {
    let fx = Fixture::new("report")?;
    base(&fx, 8, 16 * 1024 * 1024)?;
    microphone_and_speaker(&fx)?;
    camera(&fx, "USB Camera")?;
    fx.file("/proc/device-tree/compatible", "rockchip,rk3588\0")?
        .file("/dev/rknpu", "")?
        .file("/usr/lib/librknnrt.so", "")?;
    let mut runner = Runner::new(fx.root(), builtin(), Vec::new());
    let report = runner.report();
    assert_eq!(at(&report, "/agent"), "rust");
    assert_eq!(at(&report, "/hostname"), "salotto");
    assert_eq!(at(&report, "/hardware/cores"), 8);
    assert_eq!(at(&report, "/hardware/ram_gb"), 16.0);
    assert_eq!(at(&report, "/hardware/soc/vendor"), "Rockchip");
    assert_eq!(at(&report, "/hardware/accelerators/0/id"), "rknn");
    assert_eq!(at(&report, "/hardware/audio_in/0"), "USB PnP Sound Device");
    assert_eq!(at(&report, "/offload/vision/backend"), "rknn");
    assert_eq!(at(&report, "/offload/llm/target"), "edge");
    let caps = at(&report, "/capabilities")
        .as_array()
        .map(Vec::len)
        .unwrap_or_default();
    assert!(caps <= 12 && caps > 0);
    assert!(
        at(&report, "/capabilities")
            .as_array()
            .is_some_and(|c| c.contains(&json!("npu")))
    );
    Ok(())
}

#[test]
fn systemd_unit_is_hardened_and_rejects_injection() -> Result<(), String> {
    let groups = existing_groups(
        "root:x:0:\naudio:x:29:\nvideo:x:44:\n",
        &["audio", "video", "render"],
    );
    assert_eq!(groups, vec!["audio".to_owned(), "video".to_owned()]);
    let text = unit(
        Path::new("/usr/local/bin/nuxiva-satellite"),
        "Salotto",
        "satellite",
        "",
        &groups,
    )?;
    for line in [
        "DynamicUser=yes",
        "NoNewPrivileges=yes",
        "ProtectSystem=strict",
        "CapabilityBoundingSet=",
        "SupplementaryGroups=audio video",
    ] {
        assert!(text.contains(line), "{line}");
    }
    assert!(
        unit(
            Path::new("/bin/x"),
            "Salotto\nExecStartPre=/bin/sh",
            "satellite",
            "",
            &[]
        )
        .is_err()
    );
    assert!(unit(Path::new("relative"), "Salotto", "satellite", "", &[]).is_err());
    assert!(unit(Path::new("/bin/x y"), "Salotto", "satellite", "", &[]).is_err());
    Ok(())
}
