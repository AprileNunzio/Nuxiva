use std::fs;
use std::io::Read;
use std::path::Path;

use super::{Descriptor, Kind};

pub const EXTENSIONS_DIR: &str = "/etc/nuxiva/accelerators.d";
const MAX_FILES: usize = 32;
const MAX_BYTES: u64 = 16 * 1024;
const MAX_ITEMS: usize = 16;

#[derive(Debug, PartialEq, Eq)]
pub struct Rejected {
    pub file: String,
    pub reason: &'static str,
}

pub fn load_extensions(dir: &Path) -> (Vec<Descriptor>, Vec<Rejected>) {
    let mut accepted = Vec::new();
    let mut rejected = Vec::new();
    let Ok(entries) = fs::read_dir(dir) else {
        return (accepted, rejected);
    };
    let mut paths: Vec<_> = entries
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| path.extension().is_some_and(|ext| ext == "json"))
        .collect();
    paths.sort();
    for path in paths.into_iter().take(MAX_FILES) {
        let file = path
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_default();
        match read(&path).and_then(|text| parse(&text)) {
            Ok(descriptor) => accepted.push(descriptor),
            Err(reason) => rejected.push(Rejected { file, reason }),
        }
    }
    (accepted, rejected)
}

#[must_use]
pub fn merge(builtin: Vec<Descriptor>, extensions: Vec<Descriptor>) -> Vec<Descriptor> {
    let mut merged: Vec<Descriptor> = builtin
        .into_iter()
        .filter(|base| !extensions.iter().any(|ext| ext.id == base.id))
        .collect();
    merged.extend(extensions);
    merged
}

fn read(path: &Path) -> Result<String, &'static str> {
    let meta = fs::symlink_metadata(path).map_err(|_| "unreadable")?;
    if !meta.is_file() {
        return Err("not_a_file");
    }
    let mut text = String::new();
    fs::File::open(path)
        .map_err(|_| "unreadable")?
        .take(MAX_BYTES.saturating_add(1))
        .read_to_string(&mut text)
        .map_err(|_| "unreadable")?;
    if u64::try_from(text.len()).unwrap_or(u64::MAX) > MAX_BYTES {
        return Err("too_large");
    }
    Ok(text)
}

pub fn parse(text: &str) -> Result<Descriptor, &'static str> {
    let descriptor: Descriptor = serde_json::from_str(text).map_err(|_| "invalid_json")?;
    validate(&descriptor)?;
    Ok(descriptor)
}

fn validate(d: &Descriptor) -> Result<(), &'static str> {
    if !token(&d.id, 2, 32) || d.id == "cpu" {
        return Err("invalid_id");
    }
    if d.kind == Kind::Cpu {
        return Err("invalid_kind");
    }
    if d.vendor.chars().count() > 40 || d.vendor.chars().any(char::is_control) {
        return Err("invalid_vendor");
    }
    let lists = [
        &d.devices,
        &d.modules,
        &d.drm_drivers,
        &d.accel_drivers,
        &d.compatible,
        &d.runtimes,
    ];
    if lists.iter().any(|list| list.len() > MAX_ITEMS)
        || d.usb.len() > MAX_ITEMS
        || d.pci_vendors.len() > MAX_ITEMS
    {
        return Err("too_many_items");
    }
    if !d.devices.iter().all(|dev| device_path(dev)) {
        return Err("invalid_device");
    }
    let names = [&d.modules, &d.drm_drivers, &d.accel_drivers];
    if !names
        .iter()
        .all(|list| list.iter().all(|name| token(name, 1, 48)))
    {
        return Err("invalid_driver");
    }
    if !d.runtimes.iter().all(|lib| library(lib)) {
        return Err("invalid_runtime");
    }
    if !d
        .compatible
        .iter()
        .all(|c| c.len() <= 64 && c.chars().all(|ch| ch.is_ascii_graphic()))
    {
        return Err("invalid_compatible");
    }
    if d.tasks.is_empty() {
        return Err("no_tasks");
    }
    if d.devices.is_empty()
        && d.modules.is_empty()
        && d.drm_drivers.is_empty()
        && d.accel_drivers.is_empty()
        && d.usb.is_empty()
        && d.pci_vendors.is_empty()
    {
        return Err("no_evidence");
    }
    Ok(())
}

fn token(value: &str, min: usize, max: usize) -> bool {
    (min..=max).contains(&value.len())
        && value
            .chars()
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || matches!(c, '-' | '_'))
}

fn device_path(value: &str) -> bool {
    value.len() <= 96
        && value.starts_with("/dev/")
        && !value.split('/').any(|part| part == ".." || part == ".")
        && value
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '/' | '-' | '_' | '.'))
}

fn library(value: &str) -> bool {
    value.len() <= 96
        && value.starts_with("lib")
        && value.contains(".so")
        && value
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '-' | '_' | '.'))
}
