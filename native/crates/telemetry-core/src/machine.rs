#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MachineClass {
    Pi,
    Small,
    Standard,
    Powerful,
}

impl MachineClass {
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::Pi => "pi",
            Self::Small => "small",
            Self::Standard => "standard",
            Self::Powerful => "powerful",
        }
    }

    #[must_use]
    pub fn parse(text: &str) -> Option<Self> {
        match text {
            "pi" => Some(Self::Pi),
            "small" => Some(Self::Small),
            "standard" => Some(Self::Standard),
            "powerful" => Some(Self::Powerful),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Copy)]
pub struct MachineInputs<'a> {
    pub board: &'a str,
    pub ram_bytes: u64,
    pub gpu: bool,
}

const GIB: f64 = 1_073_741_824.0;

#[must_use]
pub fn detect_class(inputs: MachineInputs<'_>) -> MachineClass {
    if !inputs.board.is_empty() {
        return MachineClass::Pi;
    }
    let ram = crate::numbers::as_f64(inputs.ram_bytes) / GIB;
    if ram < 7.5 {
        MachineClass::Small
    } else if inputs.gpu || ram >= 28.0 {
        MachineClass::Powerful
    } else {
        MachineClass::Standard
    }
}

#[must_use]
pub fn core_runtime(configured: &str, class: MachineClass) -> &'static str {
    match configured {
        "native" => "native",
        "docker" => "docker",
        _ if matches!(class, MachineClass::Pi | MachineClass::Small) => "native",
        _ => "docker",
    }
}

#[must_use]
pub fn docker_needed(runtime: &str, sandbox: &str) -> bool {
    runtime == "docker"
        || matches!(
            sandbox.trim().to_lowercase().as_str(),
            "1" | "on" | "yes" | "true" | "auto"
        )
}
