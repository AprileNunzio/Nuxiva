#![forbid(unsafe_code)]

pub mod capability;
pub mod cell;
pub mod decide;
pub mod error;
pub mod floor;
pub mod matrix;
pub mod origin;
pub mod pki;
pub mod remote_kiosk;
pub mod role;
pub mod smb_sync;

pub use capability::Capability;
pub use cell::Cell;
pub use decide::{Request, Strength, Verdict, decide};
pub use error::AccessError;
pub use matrix::Matrix;
pub use pki::{
    EnterprisePkiConfig, InterfaceSnapshot, KeyAlgorithm, NetworkCategory, PkiPlan, SanItem,
    SanKind, build_pki_plan, classify_network_address, sanitize_dns_name,
};
pub use remote_kiosk::{
    ClientContext, KioskAdvisory, KioskScheme, MediaCapabilities, RemoteKioskConfig,
    RemoteKioskVerdict, evaluate_remote_kiosk,
};
pub use role::Role;

#[cfg(test)]
mod tests;
#[cfg(test)]
mod tests_matrix;
#[cfg(test)]
mod tests_origin;
#[cfg(test)]
mod tests_pki;
#[cfg(test)]
mod tests_remote_kiosk;
