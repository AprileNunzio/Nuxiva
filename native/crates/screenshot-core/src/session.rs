use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use crate::proc::run_capture;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    Wayland,
    X11,
    Tty,
    Unknown,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Session {
    pub id: String,
    pub uid: u32,
    pub gid: u32,
    pub home: PathBuf,
    pub kind: Kind,
    pub locked: bool,
    pub display: Option<String>,
}

#[must_use]
pub fn parse_show(text: &str) -> std::collections::HashMap<String, String> {
    text.lines()
        .filter_map(|line| line.split_once('='))
        .map(|(k, v)| (k.trim().to_owned(), v.trim().to_owned()))
        .collect()
}

#[must_use]
pub fn passwd_entry(passwd: &str, uid: u32) -> Option<(u32, PathBuf)> {
    passwd.lines().find_map(|line| {
        let f: Vec<&str> = line.split(':').collect();
        let entry_uid: u32 = f.get(2)?.parse().ok()?;
        if entry_uid != uid {
            return None;
        }
        let gid: u32 = f.get(3)?.parse().ok()?;
        Some((gid, PathBuf::from(f.get(5)?)))
    })
}

#[must_use]
pub fn from_properties<S: std::hash::BuildHasher>(
    props: &std::collections::HashMap<String, String, S>,
    passwd: &str,
) -> Option<Session> {
    let get = |k: &str| props.get(k).map(String::as_str).unwrap_or_default();
    if get("Active") != "yes" || get("Remote") == "yes" || get("Class") != "user" {
        return None;
    }
    let uid: u32 = get("User").parse().ok()?;
    let (gid, home) = passwd_entry(passwd, uid)?;
    let kind = match get("Type") {
        "wayland" => Kind::Wayland,
        "x11" => Kind::X11,
        "tty" => Kind::Tty,
        _ => Kind::Unknown,
    };
    let display = Some(get("Display").to_owned()).filter(|d| !d.is_empty());
    Some(Session {
        id: get("Id").to_owned(),
        uid,
        gid,
        home,
        kind,
        locked: get("LockedHint") == "yes",
        display,
    })
}

#[must_use]
pub fn valid_session_id(id: &str) -> bool {
    !id.is_empty() && id.len() <= 16 && id.bytes().all(|b| b.is_ascii_alphanumeric())
}

#[must_use]
pub fn discover() -> Option<Session> {
    let list = run_capture(Command::new("loginctl").args(["list-sessions", "--no-legend"]))?;
    let passwd = fs::read_to_string("/etc/passwd").ok()?;
    list.lines()
        .filter_map(|line| line.split_whitespace().next())
        .filter(|id| valid_session_id(id))
        .filter_map(|id| {
            let out = run_capture(Command::new("loginctl").args([
                "show-session",
                id,
                "--property=Id,Type,User,Active,LockedHint,Display,Remote,Class",
            ]))?;
            from_properties(&parse_show(&out), &passwd)
        })
        .max_by_key(|s| u8::from(!matches!(s.kind, Kind::Tty)))
}

#[must_use]
pub fn wayland_socket(runtime: &Path) -> Option<String> {
    let mut names: Vec<String> = fs::read_dir(runtime)
        .ok()?
        .filter_map(Result::ok)
        .filter_map(|e| e.file_name().into_string().ok())
        .filter(|n| {
            n.strip_prefix("wayland-")
                .is_some_and(|rest| !rest.is_empty() && rest.bytes().all(|b| b.is_ascii_digit()))
        })
        .collect();
    names.sort();
    names.into_iter().next()
}

#[must_use]
pub fn xauthority(session: &Session) -> Option<PathBuf> {
    let runtime = PathBuf::from(format!("/run/user/{}", session.uid));
    let mut candidates = vec![
        runtime.join("gdm/Xauthority"),
        session.home.join(".Xauthority"),
    ];
    if let Ok(entries) = fs::read_dir(&runtime) {
        for entry in entries.filter_map(Result::ok) {
            let name = entry.file_name();
            if name.to_string_lossy().starts_with(".mutter-Xwaylandauth.") {
                candidates.push(entry.path());
            }
        }
    }
    candidates.into_iter().find(|p| p.is_file())
}

#[must_use]
pub fn valid_display(display: &str) -> bool {
    display.starts_with(':')
        && display.len() <= 12
        && display
            .bytes()
            .skip(1)
            .all(|b| b.is_ascii_digit() || b == b'.')
        && display.len() > 1
}
