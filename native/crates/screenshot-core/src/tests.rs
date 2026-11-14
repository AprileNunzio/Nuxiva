use crate::config::{Config, Mask, Target, parse_masks, parse_target};
use crate::evdev::{KEY_PRINT, KEY_SYSRQ, bit_set, is_print_press, print_capable};
use crate::fb::{Geometry, convert, geometry};
use crate::naming::{civil, file_name, host_label, is_managed, stamp_secs};
use crate::pathguard::{valid_host, valid_share, valid_subdir};
use crate::policy::{Deny, State, decide};
use crate::raster::Raster;
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

pub(super) fn scratch(tag: &str) -> PathBuf {
    let mut raw = [0u8; 6];
    getrandom::fill(&mut raw).expect("random");
    let suffix: String = raw
        .iter()
        .fold(String::new(), |acc, b| acc + &format!("{b:02x}"));
    let dir = std::env::temp_dir().join(format!("nuxiva-shot-{tag}-{suffix}"));
    fs::create_dir_all(&dir).expect("scratch");
    dir
}

fn event(kind: u16, code: u16, value: i32) -> Vec<u8> {
    let mut raw = vec![0u8; std::mem::size_of::<usize>() * 2];
    raw.extend_from_slice(&kind.to_ne_bytes());
    raw.extend_from_slice(&code.to_ne_bytes());
    raw.extend_from_slice(&value.to_ne_bytes());
    raw
}

pub(super) fn name(secs: u64, seq: u32) -> String {
    file_name("Nodo Uno", secs, seq)
}

#[test]
fn print_key_only_on_press() {
    assert!(is_print_press(&event(1, KEY_SYSRQ, 1)));
    assert!(is_print_press(&event(1, KEY_PRINT, 1)));
    assert!(!is_print_press(&event(1, KEY_SYSRQ, 0)));
    assert!(!is_print_press(&event(1, KEY_SYSRQ, 2)));
    assert!(!is_print_press(&event(1, 30, 1)));
    assert!(!is_print_press(&event(4, KEY_SYSRQ, 1)));
    assert!(!is_print_press(&[1, 2, 3]));
}

#[test]
fn capability_bitmap() {
    let mut words = vec!["0".to_owned(); 4];
    let bits = usize::BITS as usize;
    let index = usize::from(KEY_SYSRQ) / bits;
    let within = usize::from(KEY_SYSRQ) % bits;
    let slot = words.len() - 1 - index;
    words[slot] = format!("{:x}", 1u64 << within);
    let text = words.join(" ");
    assert!(bit_set(&text, KEY_SYSRQ));
    assert!(print_capable(&text));
    assert!(!bit_set(&text, 30));
    assert!(!print_capable("0 0 0 0"));
    assert!(!print_capable(""));
}

#[test]
fn naming_is_stable_and_safe() {
    assert_eq!(host_label("Nodo Uno!"), "nodo-uno");
    assert_eq!(host_label("../../etc"), "etc");
    assert_eq!(host_label("***"), "nodo");
    assert_eq!(civil(0), (1970, 1, 1, 0, 0, 0));
    assert_eq!(civil(1_794_684_000), (2026, 11, 14, 19, 20, 0));
    let n = name(1_794_684_000, 7);
    assert_eq!(n, "nodo-uno_20261114-192000_007.png");
    assert!(is_managed(&n));
    assert_eq!(stamp_secs(&n), Some(1_794_684_000));
    assert!(!is_managed("../x.png"));
    assert!(!is_managed("nodo_20261114-192000_007.jpg"));
    assert!(!is_managed("notes.png"));
    assert!(!is_managed("A_20261114-192000_007.png"));
    assert_eq!(stamp_secs("nodo_20261314-192000_007.png"), None);
}

#[test]
fn subdir_and_hosts_validation() {
    assert!(valid_subdir("05 Scambio/Screenshot"));
    assert!(valid_subdir(""));
    assert!(!valid_subdir("../x"));
    assert!(!valid_subdir("a/../b"));
    assert!(!valid_subdir("/abs"));
    assert!(!valid_subdir("a//b"));
    assert!(!valid_subdir(".hidden"));
    assert!(!valid_subdir("a/b/c/d/e"));
    assert!(!valid_subdir("a\\b"));
    assert!(valid_host("nas.local"));
    assert!(valid_host("192.168.1.5"));
    assert!(!valid_host("-oProxyCommand"));
    assert!(!valid_host("a b"));
    assert!(!valid_host("a;b"));
    assert!(valid_share("condivisa"));
    assert!(!valid_share("con divisa"));
    assert!(!valid_share("a/b"));
    assert!(!valid_share(""));
}

#[test]
fn config_defaults_off_and_validates() {
    let c = Config::default();
    assert!(!c.enabled && !c.active());
    assert!(c.block_locked && c.block_guests && c.notice);
    assert!(Config::parse("{").is_err());
    assert!(Config::parse(r#"{"unknown":1}"#).is_err());
    assert!(Config::parse(r#"{"subdir":"../x"}"#).is_err());
    assert!(Config::parse(r#"{"target":{"kind":"dir","path":"/etc"}}"#).is_err());
    assert!(Config::parse(r#"{"target":{"kind":"dir","path":"/srv/nuxiva/condivisa"}}"#).is_ok());
    assert!(Config::parse(r#"{"target":{"kind":"smb","host":"-x","share":"s"}}"#).is_err());
    assert!(Config::parse(r#"{"masks":[{"x":900,"y":0,"w":200,"h":10}]}"#).is_err());
    assert!(Config::parse(r#"{"lang":"de"}"#).is_err());
    assert!(Config::parse(r#"{"spool":"relative"}"#).is_err());
    assert!(Config::parse(&"x".repeat(20_000)).is_err());
}

#[test]
fn settings_map_to_config() {
    let mut s = HashMap::new();
    s.insert("NUXIVA_SCREENSHOT".to_owned(), "1".to_owned());
    s.insert(
        "NUXIVA_SCREENSHOT_TARGET".to_owned(),
        "smb://nas.local/condivisa".to_owned(),
    );
    s.insert(
        "NUXIVA_SCREENSHOT_MASK".to_owned(),
        "0,0,1000,50; 10,900,200,100;bad".to_owned(),
    );
    s.insert(
        "NUXIVA_SCREENSHOT_RETENTION_DAYS".to_owned(),
        "7".to_owned(),
    );
    s.insert("NUXIVA_SCREENSHOT_BLOCK_GUESTS".to_owned(), "0".to_owned());
    s.insert("NUXIVA_UI_LANG".to_owned(), "fr".to_owned());
    let c = Config::from_settings(&s);
    assert!(c.active());
    assert_eq!(c.masks.len(), 2);
    assert_eq!(c.retention.days, 7);
    assert!(!c.block_guests && c.block_locked);
    assert_eq!(c.lang, "fr");
    assert_eq!(
        c.target,
        Target::Smb {
            host: "nas.local".into(),
            share: "condivisa".into()
        }
    );
    s.insert("NUXIVA_SCREENSHOT_TARGET".to_owned(), "/etc".to_owned());
    assert_eq!(Config::from_settings(&s), Config::default());
    assert_eq!(parse_target("smb://onlyhost"), Target::None);
    assert_eq!(parse_masks("1,2,3"), Vec::<Mask>::new());
}

#[test]
fn policy_gates() {
    let mut c = Config {
        enabled: true,
        target: Target::Dir {
            path: "/srv/nuxiva/x".into(),
        },
        ..Config::default()
    };
    let free = State {
        locked: false,
        guests: false,
    };
    assert_eq!(decide(&c, free), Ok(()));
    assert_eq!(
        decide(
            &c,
            State {
                locked: true,
                guests: false
            }
        ),
        Err(Deny::Locked)
    );
    assert_eq!(
        decide(
            &c,
            State {
                locked: false,
                guests: true
            }
        ),
        Err(Deny::Guests)
    );
    c.block_locked = false;
    c.block_guests = false;
    assert_eq!(
        decide(
            &c,
            State {
                locked: true,
                guests: true
            }
        ),
        Ok(())
    );
    c.enabled = false;
    assert_eq!(decide(&c, free), Err(Deny::Disabled));
    c.enabled = true;
    c.target = Target::None;
    assert_eq!(decide(&c, free), Err(Deny::NoTarget));
}

#[test]
fn mask_blanks_regions_only() {
    let mut r = Raster::new(10, 10, vec![200; 300]).expect("raster");
    r.apply_masks(&[
        Mask {
            x: 0,
            y: 0,
            w: 1000,
            h: 100,
        },
        Mask {
            x: 500,
            y: 500,
            w: 500,
            h: 500,
        },
    ]);
    assert!(r.rgb[..30].iter().all(|v| *v == 0));
    assert_eq!(r.rgb[30], 200);
    let at = (5 * 10 + 5) * 3;
    assert_eq!(r.rgb[at], 0);
    assert_eq!(r.rgb[(5 * 10 + 4) * 3], 200);
    let png = r.encode().expect("encode");
    assert_eq!(Raster::decode(&png).expect("decode"), r);
}

#[test]
fn raster_rejects_bad_input() {
    assert!(Raster::new(0, 5, vec![]).is_err());
    assert!(Raster::new(2, 2, vec![0; 5]).is_err());
    assert!(Raster::new(20_000, 1, vec![]).is_err());
    assert!(Raster::decode(b"not a png").is_err());
}

#[test]
fn framebuffer_conversion() {
    let geo = Geometry {
        width: 2,
        height: 1,
        bpp: 32,
        stride: 8,
    };
    let r = convert(&[10, 20, 30, 0, 40, 50, 60, 0], &geo).expect("fb32");
    assert_eq!(r.rgb, vec![30, 20, 10, 60, 50, 40]);
    let geo16 = Geometry {
        width: 1,
        height: 1,
        bpp: 16,
        stride: 2,
    };
    let r16 = convert(&[0x00, 0xf8], &geo16).expect("fb16");
    assert_eq!(r16.rgb, vec![255, 0, 0]);
    let dir = scratch("fb");
    let base = dir.join("fb0");
    fs::create_dir_all(&base).expect("dir");
    fs::write(base.join("virtual_size"), "640,480\n").expect("w");
    fs::write(base.join("bits_per_pixel"), "32\n").expect("w");
    fs::write(base.join("stride"), "2560\n").expect("w");
    let g = geometry(&dir, 0).expect("geometry");
    assert_eq!((g.width, g.height, g.bpp, g.stride), (640, 480, 32, 2560));
    fs::write(base.join("bits_per_pixel"), "8\n").expect("w");
    assert!(geometry(&dir, 0).is_err());
    let _ = fs::remove_dir_all(dir);
}
