#[cfg(target_os = "linux")]
use std::path::Path;

#[cfg(target_os = "linux")]
use landlock::{
    ABI, Access, AccessFs, AccessNet, CompatLevel, Compatible, NetPort, Ruleset, RulesetAttr,
    RulesetCreatedAttr, RulesetError, RulesetStatus, Scope, path_beneath_rules,
};

#[cfg(target_os = "linux")]
const ABI_TARGET: ABI = ABI::V6;

#[cfg(target_os = "linux")]
const READ_ONLY: [&str; 6] = [
    "/etc",
    "/usr",
    "/lib",
    "/lib64",
    "/run/systemd/resolve",
    "/run/nscd",
];

#[cfg(target_os = "linux")]
const DNS_PORT: u16 = 53;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Enforcement {
    Full,
    Partial,
    None,
}

impl Enforcement {
    #[must_use]
    pub fn label(self) -> &'static str {
        match self {
            Self::Full => "full",
            Self::Partial => "partial",
            Self::None => "none",
        }
    }
}

#[cfg(not(target_os = "linux"))]
#[derive(Debug)]
pub struct RulesetError;

#[cfg(not(target_os = "linux"))]
impl std::fmt::Display for RulesetError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "sandbox unsupported on non-linux")
    }
}

#[cfg(not(target_os = "linux"))]
impl std::error::Error for RulesetError {}

#[cfg(target_os = "linux")]
pub fn restrict(connect_ports: &[u16]) -> Result<Enforcement, RulesetError> {
    let readable: Vec<&str> = READ_ONLY
        .into_iter()
        .filter(|p| Path::new(p).exists())
        .collect();
    let mut ruleset = Ruleset::default()
        .set_compatibility(CompatLevel::BestEffort)
        .handle_access(AccessFs::from_all(ABI_TARGET))?
        .handle_access(AccessNet::BindTcp | AccessNet::ConnectTcp)?
        .scope(Scope::AbstractUnixSocket | Scope::Signal)?
        .create()?
        .add_rules(path_beneath_rules(
            readable,
            AccessFs::from_read(ABI_TARGET),
        ))?;
    for port in connect_ports.iter().copied().chain([DNS_PORT]) {
        ruleset = ruleset.add_rule(NetPort::new(port, AccessNet::ConnectTcp))?;
    }
    let status = ruleset.restrict_self()?;
    Ok(match status.ruleset {
        RulesetStatus::FullyEnforced => Enforcement::Full,
        RulesetStatus::PartiallyEnforced => Enforcement::Partial,
        RulesetStatus::NotEnforced => Enforcement::None,
    })
}

#[cfg(not(target_os = "linux"))]
pub fn restrict(_connect_ports: &[u16]) -> Result<Enforcement, RulesetError> {
    Ok(Enforcement::None)
}
