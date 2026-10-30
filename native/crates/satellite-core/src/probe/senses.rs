use serde::Serialize;

use super::root::{Root, clean_label};

const LIST_MAX: usize = 12;

#[derive(Debug, Clone, Serialize, PartialEq, Eq, Default)]
pub struct Senses {
    pub microphones: Vec<String>,
    pub speakers: Vec<String>,
    pub cameras: Vec<String>,
    pub ir_camera: bool,
    pub bluetooth: bool,
    pub usb: Vec<String>,
    pub i2c_buses: u32,
    pub gpio_chips: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BusId {
    pub vendor: u16,
    pub device: u16,
}

#[must_use]
pub fn senses(root: &Root) -> Senses {
    let (microphones, speakers) = audio(root);
    let cameras = cameras(root);
    let ir_camera = cameras.iter().any(|name| is_infrared(name));
    Senses {
        microphones,
        speakers,
        cameras,
        ir_camera,
        bluetooth: !root.entries("/sys/class/bluetooth").is_empty(),
        usb: usb_products(root),
        i2c_buses: count(root, "/sys/class/i2c-dev", "i2c-"),
        gpio_chips: count(root, "/sys/bus/gpio/devices", "gpiochip"),
    }
}

#[must_use]
pub fn usb_ids(root: &Root) -> Vec<BusId> {
    root.entries("/sys/bus/usb/devices")
        .iter()
        .filter_map(|dev| {
            Some(BusId {
                vendor: hex(&root.read_trim(&format!("/sys/bus/usb/devices/{dev}/idVendor"))?)?,
                device: hex(&root.read_trim(&format!("/sys/bus/usb/devices/{dev}/idProduct"))?)?,
            })
        })
        .collect()
}

#[must_use]
pub fn pci_ids(root: &Root) -> Vec<BusId> {
    root.entries("/sys/bus/pci/devices")
        .iter()
        .filter_map(|dev| {
            Some(BusId {
                vendor: hex(&root.read_trim(&format!("/sys/bus/pci/devices/{dev}/vendor"))?)?,
                device: hex(&root.read_trim(&format!("/sys/bus/pci/devices/{dev}/device"))?)?,
            })
        })
        .collect()
}

fn hex(raw: &str) -> Option<u16> {
    u16::from_str_radix(raw.trim_start_matches("0x"), 16).ok()
}

fn audio(root: &Root) -> (Vec<String>, Vec<String>) {
    let cards = root.read("/proc/asound/cards").unwrap_or_default();
    let mut inputs = Vec::new();
    let mut outputs = Vec::new();
    for line in cards.lines() {
        let trimmed = line.trim_start();
        let Some(index) = trimmed
            .split_whitespace()
            .next()
            .and_then(|v| v.parse::<u16>().ok())
        else {
            continue;
        };
        let name = trimmed.split_once(" - ").map_or_else(
            || format!("card {index}"),
            |(_, label)| clean_label(label, 60),
        );
        let streams = root.entries(&format!("/proc/asound/card{index}"));
        if streams
            .iter()
            .any(|s| s.starts_with("pcm") && s.ends_with('c'))
        {
            inputs.push(name.clone());
        }
        if streams
            .iter()
            .any(|s| s.starts_with("pcm") && s.ends_with('p'))
        {
            outputs.push(name);
        }
    }
    inputs.truncate(LIST_MAX);
    outputs.truncate(LIST_MAX);
    (inputs, outputs)
}

fn cameras(root: &Root) -> Vec<String> {
    let mut names: Vec<String> = root
        .entries("/sys/class/video4linux")
        .iter()
        .filter(|node| node.starts_with("video"))
        .filter(|node| {
            root.read_trim(&format!("/sys/class/video4linux/{node}/index"))
                .is_none_or(|index| index == "0")
        })
        .filter_map(|node| root.read_trim(&format!("/sys/class/video4linux/{node}/name")))
        .map(|name| clean_label(&name, 60))
        .filter(|name| !name.is_empty() && !is_codec(name))
        .collect();
    names.dedup();
    names.truncate(LIST_MAX);
    names
}

fn is_codec(name: &str) -> bool {
    let lower = name.to_ascii_lowercase();
    [
        "codec",
        "isp",
        "rga",
        "hantro",
        "rkvdec",
        "rkvenc",
        "bcm2835-isp",
        "pispbe",
        "vpu",
    ]
    .iter()
    .any(|word| lower.contains(word))
}

fn is_infrared(name: &str) -> bool {
    name.to_ascii_lowercase()
        .split(|c: char| !c.is_ascii_alphanumeric())
        .any(|word| matches!(word, "ir" | "infrared" | "infrarossi"))
}

fn usb_products(root: &Root) -> Vec<String> {
    let mut names: Vec<String> = root
        .entries("/sys/bus/usb/devices")
        .iter()
        .filter_map(|dev| root.read_trim(&format!("/sys/bus/usb/devices/{dev}/product")))
        .map(|name| clean_label(&name, 60))
        .filter(|name| !name.is_empty() && !name.to_ascii_lowercase().contains("host controller"))
        .collect();
    names.sort();
    names.dedup();
    names.truncate(LIST_MAX);
    names
}

fn count(root: &Root, dir: &str, prefix: &str) -> u32 {
    let total = root
        .entries(dir)
        .iter()
        .filter(|name| name.starts_with(prefix))
        .count();
    u32::try_from(total).unwrap_or(u32::MAX)
}
