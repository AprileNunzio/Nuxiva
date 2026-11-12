#![forbid(unsafe_code)]

pub mod gate;
pub mod hands;
pub mod owner;

#[cfg(target_arch = "wasm32")]
mod bindings;

pub use gate::{Audience, PUBLIC_ACTIONS, public_only};
pub use hands::{HandsEngine, HandsError};
pub use owner::{Face, Owner, assign};

#[cfg(test)]
mod tests;
