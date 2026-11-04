pub mod root;
pub mod senses;
pub mod soc;
pub mod system;

use serde::Serialize;

use crate::backends::{self, Accelerator, Descriptor};
use root::Root;

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct Profile {
    pub system: system::System,
    pub soc: soc::Soc,
    pub senses: senses::Senses,
    pub accelerators: Vec<Accelerator>,
}

#[must_use]
pub fn profile(root: &Root, descriptors: &[Descriptor], extra_library_dirs: &[String]) -> Profile {
    let soc = soc::soc(root);
    let accelerators = backends::discover(root, &soc, descriptors, extra_library_dirs);
    Profile {
        system: system::system(root),
        senses: senses::senses(root),
        soc,
        accelerators,
    }
}
