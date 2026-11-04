use serde::Serialize;

use super::root::{Root, clean_label};

const VENDORS: &[(&str, &str)] = &[
    ("rockchip", "Rockchip"),
    ("brcm", "Broadcom"),
    ("raspberrypi", "Raspberry Pi"),
    ("nvidia", "NVIDIA"),
    ("amlogic", "Amlogic"),
    ("allwinner", "Allwinner"),
    ("qcom", "Qualcomm"),
    ("mediatek", "MediaTek"),
    ("fsl", "NXP"),
    ("nxp", "NXP"),
    ("ti", "Texas Instruments"),
    ("samsung", "Samsung"),
    ("sophgo", "Sophgo"),
    ("starfive", "StarFive"),
    ("spacemit", "SpacemiT"),
    ("thead", "T-Head"),
    ("canaan", "Canaan"),
    ("renesas", "Renesas"),
    ("st", "STMicroelectronics"),
    ("xlnx", "AMD Xilinx"),
];

const X86: &[(&str, &str)] = &[
    ("GenuineIntel", "Intel"),
    ("AuthenticAMD", "AMD"),
    ("HygonGenuine", "Hygon"),
];

#[derive(Debug, Clone, Serialize, PartialEq, Eq, Default)]
pub struct Soc {
    pub vendor: String,
    pub family: String,
    pub compatible: Vec<String>,
}

impl Soc {
    #[must_use]
    pub fn matches(&self, prefixes: &[&str]) -> bool {
        self.compatible
            .iter()
            .any(|entry| prefixes.iter().any(|prefix| entry.starts_with(prefix)))
    }
}

#[must_use]
pub fn soc(root: &Root) -> Soc {
    let compatible = compatible(root);
    if compatible.is_empty() {
        return x86(root);
    }
    let chip = compatible.last().cloned().unwrap_or_default();
    let (prefix, family) = chip.split_once(',').unwrap_or(("", chip.as_str()));
    let vendor = VENDORS
        .iter()
        .find(|(key, _)| *key == prefix)
        .map_or_else(|| clean_label(prefix, 30), |(_, name)| (*name).to_owned());
    Soc {
        vendor,
        family: clean_label(family, 40),
        compatible,
    }
}

fn compatible(root: &Root) -> Vec<String> {
    root.read("/proc/device-tree/compatible")
        .or_else(|| root.read("/sys/firmware/devicetree/base/compatible"))
        .map(|raw| {
            raw.split('\0')
                .map(str::trim)
                .filter(|entry| !entry.is_empty())
                .map(|entry| {
                    entry
                        .chars()
                        .filter(char::is_ascii_graphic)
                        .take(64)
                        .collect::<String>()
                })
                .take(16)
                .collect()
        })
        .unwrap_or_default()
}

fn x86(root: &Root) -> Soc {
    let text = root.read("/proc/cpuinfo").unwrap_or_default();
    let field = |name: &str| {
        text.lines().find_map(|line| {
            let (key, value) = line.split_once(':')?;
            (key.trim() == name).then(|| value.trim().to_owned())
        })
    };
    let raw_vendor = field("vendor_id").unwrap_or_default();
    let vendor = X86.iter().find(|(key, _)| *key == raw_vendor).map_or_else(
        || clean_label(&raw_vendor, 30),
        |(_, name)| (*name).to_owned(),
    );
    Soc {
        vendor,
        family: clean_label(&field("model name").unwrap_or_default(), 60),
        compatible: Vec::new(),
    }
}
