#![forbid(unsafe_code)]
pub mod dna;
pub mod error;
pub mod glb;
pub mod layout;
pub mod model;
pub mod parse;

pub use error::{HoloError, HoloResult};
pub use model::{Part, Scene, Shape};

pub const MAX_INPUT: usize = 262_144;

pub fn prepare(input: &str) -> HoloResult<String> {
    if input.len() > MAX_INPUT {
        return Err(HoloError::TooLarge);
    }
    let raw: serde_json::Value = serde_json::from_str(input).map_err(|_| HoloError::BadJson)?;
    let scene = layout::arrange(parse::scene(&raw)?);
    serde_json::to_string(&scene).map_err(|_| HoloError::BadJson)
}

#[cfg(test)]
mod tests;
