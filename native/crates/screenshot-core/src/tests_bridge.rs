use std::collections::HashMap;
use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::PathBuf;
use std::time::Instant;

use crate::bridge::{Bridge, REQUEST, STATUS, Status};
use crate::capture::candidates;
use crate::config::{Config, Target, parse_env_text};
use crate::daemon::{Daemon, Format, folder};
use crate::session::{Kind, Session};
use crate::smblogin::{render, store, valid_password, valid_user};
use crate::tests::scratch;

fn session(kind: Kind, uid: u32) -> Session {
    Session {
        id: "2".into(),
        uid,
        gid: uid,
        home: PathBuf::from("/root"),
        kind,
        locked: false,
        display: None,
    }
}

#[test]
fn screenshots_are_on_unless_turned_off_or_shares_are_off() {
    let mut s = HashMap::new();
    s.insert(
        "NUXIVA_SCREENSHOT_TARGET".to_owned(),
        "/srv/nuxiva/condivisa".to_owned(),
    );
    assert!(Config::from_settings(&s).active());
    s.insert("NUXIVA_SHARES".to_owned(), "0".to_owned());
    assert!(!Config::from_settings(&s).enabled);
    s.insert("NUXIVA_SCREENSHOT".to_owned(), "1".to_owned());
    assert!(Config::from_settings(&s).enabled);
    s.insert("NUXIVA_SCREENSHOT".to_owned(), "0".to_owned());
    assert!(!Config::from_settings(&s).enabled);
    assert!(parse_env_text("NUXIVA_SHARES=0\n").contains_key("NUXIVA_SHARES"));
}

#[test]
fn kiosk_tty_session_is_captured_through_the_x_display() {
    let tty = session(Kind::Tty, 0);
    let list = candidates(Some(&tty));
    assert_eq!(list.len(), 1);
    assert_eq!(list[0].kind, Kind::X11);
    assert_eq!(list[0].display.as_deref(), Some(":0"));
    let wayland = session(Kind::Wayland, 1000);
    let list = candidates(Some(&wayland));
    assert_eq!(list[0], wayland);
    assert!(
        list.iter()
            .any(|s| s.uid == 0 && s.display.as_deref() == Some(":0"))
    );
    assert_eq!(candidates(None)[0].uid, 0);
}

#[test]
fn requests_are_consumed_once_and_status_is_published() {
    let dir = scratch("bridge");
    let mut bridge = Bridge::new(dir.clone());
    assert!(!bridge.take_request());
    fs::write(dir.join(REQUEST), b"").expect("request");
    assert!(bridge.take_request());
    assert!(!bridge.take_request());
    fs::create_dir(dir.join(REQUEST)).expect("dir");
    assert!(!bridge.take_request());
    let first = bridge
        .publish(Status::Saved, "nodo_1.png", "/srv/x\u{7}", 0)
        .expect("publish");
    let second = bridge
        .publish(Status::Queued, "", "/srv/x", 0)
        .expect("publish");
    assert!(second.id > first.id);
    assert_eq!(first.folder, "/srv/x");
    let text = fs::read_to_string(dir.join(STATUS)).expect("status");
    assert!(text.contains("\"status\":\"queued\""));
    let _ = fs::remove_dir_all(dir);
}

#[test]
fn daemon_reports_why_a_request_did_nothing() {
    let dir = scratch("daemon-bridge");
    let mut daemon = Daemon::new(dir.join("c.json"), Format::Json, None).with_bridge(dir.clone());
    let _ = daemon.capture_now(None, Instant::now());
    let text = fs::read_to_string(dir.join(STATUS)).expect("status");
    assert!(text.contains("\"status\":\"no_target\""), "{text}");
    let _ = fs::remove_dir_all(dir);
}

#[test]
fn folder_is_human_readable() {
    let mut c = Config {
        target: Target::Smb {
            host: "nas".into(),
            share: "condivisa".into(),
        },
        ..Config::default()
    };
    assert_eq!(folder(&c), "\\\\nas\\condivisa\\05 Scambio\\Screenshot");
    c.target = Target::Dir {
        path: PathBuf::from("/srv/nuxiva/condivisa"),
    };
    assert_eq!(folder(&c), "/srv/nuxiva/condivisa/05 Scambio/Screenshot");
}

#[test]
fn smb_login_from_settings_is_private_and_validated() {
    let mut s = HashMap::new();
    s.insert(
        "NUXIVA_SCREENSHOT_SMB_USER".to_owned(),
        "nuxiva-share".to_owned(),
    );
    s.insert(
        "NUXIVA_SCREENSHOT_SMB_PASSWORD".to_owned(),
        "Batteria-42".to_owned(),
    );
    let content = render(&s).expect("login");
    let dir = scratch("login");
    let path = store(&dir, &content).expect("store");
    assert_eq!(
        fs::metadata(&path).expect("meta").permissions().mode() & 0o777,
        0o600
    );
    assert_eq!(
        fs::read_to_string(&path).expect("read"),
        "username = nuxiva-share\npassword = Batteria-42\n"
    );
    s.insert(
        "NUXIVA_SCREENSHOT_SMB_PASSWORD".to_owned(),
        "a\nusername = x".to_owned(),
    );
    assert!(render(&s).is_none());
    assert!(!valid_user("-x") && !valid_user("a b") && valid_user("WORKGROUP\\mario"));
    assert!(!valid_password("") && !valid_password(&"x".repeat(300)));
    let _ = fs::remove_dir_all(dir);
}
