use std::fs;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use crate::capture::tools_for;
use crate::capture::{Tool, locate};
use crate::config::{Config, Retention, Target, parse_env_text};
use crate::daemon::{Daemon, Format, Outcome, load_config};
use crate::error::Error;
use crate::naming::stamp_secs;
use crate::notice::{Notice, text};
use crate::policy::Deny;
use crate::raster::Raster;
use crate::retention::plan;
use crate::session::{Kind, from_properties, parse_show, passwd_entry, valid_display};
use crate::sink::{DirSink, Entry, Sink, atomic_write, parse_smb_ls};
use crate::spool::{Backoff, SPOOL_MAX_FILES, Spool, flush};
use crate::tests::{name, scratch};

#[test]
fn dir_sink_blocks_traversal_and_symlinks() {
    let root = scratch("sink");
    let roots = vec![root.to_string_lossy().into_owned()];
    let sink = DirSink::with_roots(root.clone(), "05 Scambio/Screenshot".into(), roots.clone());
    let n = name(1_794_600_000, 1);
    sink.put(&n, b"png-bytes").expect("put");
    let stored = root.join("05 Scambio/Screenshot").join(&n);
    assert_eq!(fs::read(&stored).expect("read"), b"png-bytes");
    assert!(matches!(sink.put(&n, b"x"), Err(Error::Sink(m)) if m == "exists"));
    assert!(sink.put("../evil.png", b"x").is_err());
    assert!(sink.put("evil.sh", b"x").is_err());
    assert_eq!(sink.list().expect("list").len(), 1);
    sink.remove(&n).expect("remove");
    assert!(sink.remove("../../x.png").is_err());
    let bad = DirSink::with_roots(root.clone(), "../up".into(), roots.clone());
    assert!(bad.put(&n, b"x").is_err());
    let outside = scratch("outside");
    std::os::unix::fs::symlink(&outside, root.join("link")).expect("symlink");
    let linked = DirSink::with_roots(root.clone(), "link".into(), roots);
    assert!(linked.put(&n, b"x").is_err());
    assert!(fs::read_dir(&outside).expect("rd").next().is_none());
    let denied = DirSink::with_roots(root.clone(), String::new(), vec!["/nonexistent".into()]);
    assert!(denied.put(&n, b"x").is_err());
    let _ = fs::remove_dir_all(root);
    let _ = fs::remove_dir_all(outside);
}

#[test]
fn atomic_write_leaves_no_temp_files() {
    let dir = scratch("atomic");
    let n = name(1_794_600_000, 2);
    atomic_write(&dir, &n, b"abc", 0o600).expect("write");
    let names: Vec<String> = fs::read_dir(&dir)
        .expect("rd")
        .map(|e| e.expect("e").file_name().into_string().expect("s"))
        .collect();
    assert_eq!(names, vec![n]);
    let _ = fs::remove_dir_all(dir);
}

struct Flaky {
    fail: std::cell::Cell<bool>,
    calls: std::cell::Cell<u32>,
}

impl Sink for Flaky {
    fn put(&self, _: &str, _: &[u8]) -> crate::error::Result<()> {
        self.calls.set(self.calls.get() + 1);
        if self.fail.get() {
            Err(Error::Sink("down".into()))
        } else {
            Ok(())
        }
    }
    fn list(&self) -> crate::error::Result<Vec<Entry>> {
        Ok(Vec::new())
    }
    fn remove(&self, _: &str) -> crate::error::Result<()> {
        Ok(())
    }
}

#[test]
fn spool_retries_with_backoff_and_survives() {
    let dir = scratch("spool");
    let spool = Spool::open(dir.join("q")).expect("open");
    spool.enqueue(&name(1_794_600_000, 1), b"a").expect("e1");
    spool.enqueue(&name(1_794_600_001, 2), b"b").expect("e2");
    let sink = Flaky {
        fail: true.into(),
        calls: 0.into(),
    };
    let mut backoff = Backoff::new();
    let t0 = Instant::now();
    let report = flush(&spool, &sink, &mut backoff, t0);
    assert!(report.failed && report.delivered == 0);
    assert_eq!(sink.calls.get(), 1);
    assert_eq!(spool.pending().len(), 2);
    let again = flush(&spool, &sink, &mut backoff, t0);
    assert_eq!(again.delivered, 0);
    assert_eq!(sink.calls.get(), 1);
    sink.fail.set(false);
    let later = t0 + Duration::from_secs(10);
    let ok = flush(&spool, &sink, &mut backoff, later);
    assert_eq!(ok.delivered, 2);
    assert!(spool.pending().is_empty());
    assert_eq!(backoff.failures(), 0);
    assert_eq!(Backoff::delay(0), Duration::from_secs(5));
    assert_eq!(Backoff::delay(3), Duration::from_secs(40));
    assert_eq!(Backoff::delay(30), Duration::from_mins(15));
    let _ = fs::remove_dir_all(dir);
}

#[test]
fn spool_is_bounded() {
    let dir = scratch("bound");
    let spool = Spool::open(dir.join("q")).expect("open");
    for i in 0..(u32::try_from(SPOOL_MAX_FILES).expect("cap") + 5) {
        spool
            .enqueue(&name(1_794_600_000 + u64::from(i), i), b"x")
            .expect("enqueue");
    }
    assert_eq!(spool.pending().len(), SPOOL_MAX_FILES);
    let first = spool.pending().first().map(|p| p.0.clone()).expect("first");
    assert_eq!(stamp_secs(&first), Some(1_794_600_005));
    let link = dir.join("evil");
    std::os::unix::fs::symlink(Path::new("/tmp"), &link).expect("symlink");
    assert!(Spool::open(link).is_err());
    let _ = fs::remove_dir_all(dir);
}

#[test]
fn retention_by_age_count_and_size() {
    let day = 86_400;
    let now = 1_794_600_000;
    let entry = |age_days: u64, size: u64, seq: u32| {
        let stamp = now - age_days * day;
        Entry {
            name: name(stamp, seq),
            size,
            stamp,
        }
    };
    let entries = vec![
        entry(40, 10, 1),
        entry(5, 10, 2),
        entry(4, 10, 3),
        entry(1, 10, 4),
    ];
    let by_age = plan(
        &entries,
        &Retention {
            days: 30,
            max_files: 100,
            max_bytes: u64::MAX,
        },
        now,
    );
    assert_eq!(by_age, vec![entries[0].name.clone()]);
    let by_count = plan(
        &entries,
        &Retention {
            days: 0,
            max_files: 2,
            max_bytes: u64::MAX,
        },
        now,
    );
    assert_eq!(
        by_count,
        vec![entries[0].name.clone(), entries[1].name.clone()]
    );
    let by_size = plan(
        &entries,
        &Retention {
            days: 0,
            max_files: 100,
            max_bytes: 20,
        },
        now,
    );
    assert_eq!(by_size.len(), 2);
    assert!(
        plan(
            &entries,
            &Retention {
                days: 0,
                max_files: 100,
                max_bytes: u64::MAX
            },
            now
        )
        .is_empty()
    );
}

#[test]
fn smb_listing_parses_only_managed_files() {
    let n = name(1_794_600_000, 3);
    let text = format!(
        "  .                                   D        0  Sat Nov 14 20:00:00 2026\n  {n}      N   1234  Sat Nov 14 20:00:00 2026\n  other.png      N   5  x\n"
    );
    let parsed = parse_smb_ls(&text);
    assert_eq!(parsed.len(), 1);
    assert_eq!(parsed[0].size, 1234);
}

#[test]
fn session_parsing() {
    let passwd = "root:x:0:0:root:/root:/bin/bash\nmario:x:1000:1000:M:/home/mario:/bin/bash\n";
    assert_eq!(
        passwd_entry(passwd, 1000),
        Some((1000, PathBuf::from("/home/mario")))
    );
    assert_eq!(passwd_entry(passwd, 5), None);
    let show = "Id=2\nType=wayland\nUser=1000\nActive=yes\nLockedHint=yes\nDisplay=\nRemote=no\nClass=user\n";
    let s = from_properties(&parse_show(show), passwd).expect("session");
    assert_eq!((s.kind, s.locked, s.uid), (Kind::Wayland, true, 1000));
    let remote = show.replace("Remote=no", "Remote=yes");
    assert!(from_properties(&parse_show(&remote), passwd).is_none());
    let greeter = show.replace("Class=user", "Class=greeter");
    assert!(from_properties(&parse_show(&greeter), passwd).is_none());
    assert!(valid_display(":0"));
    assert!(valid_display(":1.0"));
    assert!(!valid_display("0"));
    assert!(!valid_display(":0;rm"));
    assert!(!valid_display(":"));
}

#[test]
fn capture_backends_by_session_kind() {
    assert_eq!(tools_for(Kind::Wayland), &[Tool::Grim]);
    assert_eq!(tools_for(Kind::X11), &[Tool::Maim, Tool::Import]);
    assert!(tools_for(Kind::Tty).is_empty());
    assert!(locate(Tool::Grim, &["/nonexistent-dir"]).is_none());
    assert!(Tool::Import.args().contains(&"png:-"));
}

#[test]
fn notices_exist_in_every_language() {
    for lang in ["it", "en", "fr", "es"] {
        for n in [
            Notice::Saved,
            Notice::Queued,
            Notice::Blocked,
            Notice::Failed,
        ] {
            let (title, body) = text(lang, n);
            assert!(!title.is_empty() && !body.is_empty());
        }
    }
    assert_ne!(text("it", Notice::Saved), text("en", Notice::Saved));
}

#[test]
fn trigger_is_denied_when_disabled_or_locked() {
    let root = scratch("daemon");
    let conf = root.join("c.json");
    let mut daemon = Daemon::new(conf, Format::Json, None);
    assert_eq!(
        daemon.handle_trigger(None, Instant::now()),
        Outcome::Denied(Deny::Disabled)
    );
    let _ = fs::remove_dir_all(root);
}

#[test]
fn x11_capture_end_to_end_when_tools_present() {
    let (Some(_), Some(_)) = (
        locate(Tool::Import, &["/usr/bin", "/usr/local/bin"]),
        ["/usr/bin/Xvfb", "/usr/local/bin/Xvfb"]
            .iter()
            .find(|p| Path::new(p).is_file()),
    ) else {
        return;
    };
    let display = ":97";
    let mut server = std::process::Command::new("Xvfb")
        .args([display, "-screen", "0", "320x200x24", "-nolisten", "tcp"])
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn()
        .expect("xvfb");
    std::thread::sleep(Duration::from_millis(1500));
    let session = crate::session::Session {
        id: "t".into(),
        uid: 0,
        gid: 0,
        home: PathBuf::from("/root"),
        kind: Kind::X11,
        locked: false,
        display: Some(display.into()),
    };
    let grabbed = crate::capture::from_session(&session);
    let _ = server.kill();
    let _ = server.wait();
    let bytes = grabbed.expect("capture");
    let raster = Raster::decode(&bytes).expect("decode");
    assert_eq!((raster.width, raster.height), (320, 200));
    let root = scratch("e2e");
    let roots = vec![root.to_string_lossy().into_owned()];
    let sink = DirSink::with_roots(root.clone(), "Screenshot".into(), roots);
    sink.put(&name(1_794_684_000, 9), &bytes).expect("put");
    let listed = sink.list().expect("list");
    assert_eq!(listed.len(), 1);
    assert_eq!(listed[0].size, bytes.len() as u64);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn env_file_is_filtered_and_drives_config() {
    let parsed = parse_env_text(
        "# c\nNUXIVA_SCREENSHOT=1\nexport NUXIVA_SCREENSHOT_TARGET=\"/mnt/nas\"\nNUXIVA_SMB_PASSWORD=secret\nNUXIVA_UI_LANG='en'\nOTHER=1\n",
    );
    assert_eq!(parsed.len(), 3);
    assert!(!parsed.contains_key("NUXIVA_SMB_PASSWORD"));
    assert_eq!(parsed.get("NUXIVA_UI_LANG").map(String::as_str), Some("en"));
    let dir = scratch("env");
    let file = dir.join("nuxiva.env");
    fs::write(&file, "NUXIVA_SCREENSHOT=1\nNUXIVA_SCREENSHOT_TARGET=\n").expect("write");
    let with_default = load_config(&file, Format::Env, Some(Path::new("/srv/nuxiva/condivisa")));
    assert!(with_default.active());
    assert_eq!(
        with_default.target,
        Target::Dir {
            path: PathBuf::from("/srv/nuxiva/condivisa")
        }
    );
    let without = load_config(&file, Format::Env, None);
    assert!(!without.active() && !without.enabled);
    fs::write(&file, "NUXIVA_SCREENSHOT=0\n").expect("write");
    assert!(!load_config(&file, Format::Env, Some(Path::new("/srv/nuxiva/condivisa"))).enabled);
    assert_eq!(
        load_config(&dir.join("missing"), Format::Env, None),
        Config::default()
    );
    let _ = fs::remove_dir_all(dir);
}
