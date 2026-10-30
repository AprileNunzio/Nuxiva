mod catalog;
mod extend;

use serde::{Deserialize, Serialize};

use crate::probe::root::Root;
use crate::probe::senses::{BusId, pci_ids, usb_ids};
use crate::probe::soc::Soc;

pub use catalog::builtin;
pub use extend::{EXTENSIONS_DIR, Rejected, load_extensions, merge, parse};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Task {
    WakeWord,
    Vad,
    Stt,
    Tts,
    Vision,
    Llm,
}

impl Task {
    pub const ALL: [Self; 6] = [
        Self::WakeWord,
        Self::Vad,
        Self::Stt,
        Self::Tts,
        Self::Vision,
        Self::Llm,
    ];
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    Npu,
    Gpu,
    Tpu,
    Dsp,
    Cpu,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Descriptor {
    pub id: String,
    pub vendor: String,
    pub kind: Kind,
    pub devices: Vec<String>,
    pub modules: Vec<String>,
    pub drm_drivers: Vec<String>,
    pub accel_drivers: Vec<String>,
    pub usb: Vec<[u16; 2]>,
    pub pci_vendors: Vec<u16>,
    pub compatible: Vec<String>,
    pub runtimes: Vec<String>,
    pub tasks: Vec<Task>,
    pub priority: u8,
    pub llm_min_ram_mb: u32,
}

impl Default for Descriptor {
    fn default() -> Self {
        Self {
            id: String::new(),
            vendor: String::new(),
            kind: Kind::Npu,
            devices: Vec::new(),
            modules: Vec::new(),
            drm_drivers: Vec::new(),
            accel_drivers: Vec::new(),
            usb: Vec::new(),
            pci_vendors: Vec::new(),
            compatible: Vec::new(),
            runtimes: Vec::new(),
            tasks: Vec::new(),
            priority: 50,
            llm_min_ram_mb: 6144,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Accelerator {
    pub id: String,
    pub vendor: String,
    pub kind: Kind,
    pub evidence: Vec<String>,
    pub runtime: Option<String>,
    pub ready: bool,
    pub tasks: Vec<Task>,
    pub priority: u8,
    pub llm_min_ram_mb: u32,
}

#[derive(Debug)]
pub struct Bus {
    usb: Vec<BusId>,
    pci: Vec<BusId>,
    drm: Vec<String>,
    accel: Vec<String>,
    libraries: Vec<String>,
}

const LIBRARY_DIRS: &[&str] = &[
    "/usr/lib",
    "/usr/lib64",
    "/usr/local/lib",
    "/usr/local/lib64",
    "/lib",
    "/usr/lib/aarch64-linux-gnu",
    "/usr/lib/x86_64-linux-gnu",
    "/usr/lib/arm-linux-gnueabihf",
    "/usr/lib/riscv64-linux-gnu",
    "/usr/lib/aarch64-linux-gnu/tegra",
    "/usr/local/cuda/lib64",
    "/usr/local/cuda/targets/aarch64-linux/lib",
    "/opt/rocm/lib",
    "/opt/intel/openvino/runtime/lib/intel64",
    "/opt/qcom/aistack/lib",
];

impl Bus {
    #[must_use]
    pub fn scan(root: &Root, extra_library_dirs: &[String]) -> Self {
        let mut libraries: Vec<String> = LIBRARY_DIRS
            .iter()
            .map(|dir| (*dir).to_owned())
            .chain(extra_library_dirs.iter().cloned())
            .flat_map(|dir| root.entries(&dir))
            .collect();
        libraries.sort();
        libraries.dedup();
        Self {
            usb: usb_ids(root),
            pci: pci_ids(root),
            drm: drivers(root, "/sys/class/drm"),
            accel: drivers(root, "/sys/class/accel"),
            libraries,
        }
    }

    fn runtime(&self, wanted: &[String]) -> Option<String> {
        wanted.iter().find_map(|name| {
            self.libraries
                .iter()
                .find(|lib| {
                    *lib == name
                        || lib
                            .strip_prefix(name.as_str())
                            .is_some_and(|rest| rest.starts_with('.'))
                })
                .cloned()
        })
    }
}

fn drivers(root: &Root, class: &str) -> Vec<String> {
    let mut found: Vec<String> = root
        .entries(class)
        .iter()
        .filter_map(|node| root.link_name(&format!("{class}/{node}/device/driver")))
        .collect();
    found.sort();
    found.dedup();
    found
}

pub fn detect(root: &Root, soc: &Soc, bus: &Bus, descriptor: &Descriptor) -> Option<Accelerator> {
    let mut evidence = Vec::new();
    evidence.extend(
        descriptor
            .devices
            .iter()
            .filter(|d| root.exists(d))
            .cloned(),
    );
    evidence.extend(
        descriptor
            .modules
            .iter()
            .filter(|m| root.exists(&format!("/sys/module/{m}")))
            .map(|m| format!("module:{m}")),
    );
    evidence.extend(
        descriptor
            .drm_drivers
            .iter()
            .filter(|d| bus.drm.contains(d))
            .map(|d| format!("drm:{d}")),
    );
    evidence.extend(
        descriptor
            .accel_drivers
            .iter()
            .filter(|d| bus.accel.contains(d))
            .map(|d| format!("accel:{d}")),
    );
    evidence.extend(
        descriptor
            .usb
            .iter()
            .filter(|[v, p]| bus.usb.iter().any(|id| id.vendor == *v && id.device == *p))
            .map(|[v, p]| format!("usb:{v:04x}:{p:04x}")),
    );
    evidence.extend(
        descriptor
            .pci_vendors
            .iter()
            .filter(|v| bus.pci.iter().any(|id| id.vendor == **v))
            .map(|v| format!("pci:{v:04x}")),
    );
    let always = descriptor.kind == Kind::Cpu;
    if evidence.is_empty() && !always {
        return None;
    }
    let refs: Vec<&str> = descriptor.compatible.iter().map(String::as_str).collect();
    if !refs.is_empty() && soc.matches(&refs) {
        evidence.push(format!("soc:{}", soc.family));
    }
    let runtime = bus.runtime(&descriptor.runtimes);
    Some(Accelerator {
        id: descriptor.id.clone(),
        vendor: descriptor.vendor.clone(),
        kind: descriptor.kind,
        evidence,
        ready: descriptor.runtimes.is_empty() || runtime.is_some(),
        runtime,
        tasks: descriptor.tasks.clone(),
        priority: descriptor.priority,
        llm_min_ram_mb: descriptor.llm_min_ram_mb,
    })
}

#[must_use]
pub fn discover(
    root: &Root,
    soc: &Soc,
    descriptors: &[Descriptor],
    extra_library_dirs: &[String],
) -> Vec<Accelerator> {
    let bus = Bus::scan(root, extra_library_dirs);
    let mut found: Vec<Accelerator> = descriptors
        .iter()
        .filter_map(|descriptor| detect(root, soc, &bus, descriptor))
        .collect();
    found.sort_by(|a, b| b.priority.cmp(&a.priority).then_with(|| a.id.cmp(&b.id)));
    found.dedup_by(|a, b| a.id == b.id);
    found
}
