mod cif;
mod pdb;

use crate::error::{MolError, MolResult};
use crate::model::Structure;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Format {
    Pdb,
    Cif,
    Auto,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Limits {
    pub max_bytes: usize,
    pub max_atoms: usize,
    pub max_line: usize,
}

impl Default for Limits {
    fn default() -> Self {
        Self {
            max_bytes: 64 * 1024 * 1024,
            max_atoms: 2_000_000,
            max_line: 4096,
        }
    }
}

pub(crate) struct Lines<'a> {
    inner: std::str::Lines<'a>,
    number: u32,
    max: usize,
}

impl<'a> Lines<'a> {
    fn new(text: &'a str, max: usize) -> Self {
        Self {
            inner: text.lines(),
            number: 0,
            max,
        }
    }
}

impl<'a> Iterator for Lines<'a> {
    type Item = MolResult<(u32, &'a str)>;

    fn next(&mut self) -> Option<Self::Item> {
        let line = self.inner.next()?;
        self.number = self.number.saturating_add(1);
        Some(if line.len() > self.max {
            Err(MolError::LineTooLong(self.number))
        } else {
            Ok((self.number, line))
        })
    }
}

fn detect(text: &str) -> MolResult<Format> {
    for line in text.lines().take(2000) {
        let trimmed = line.trim_start();
        if trimmed.starts_with("data_")
            || trimmed.starts_with("_atom_site.")
            || trimmed.starts_with("loop_")
        {
            return Ok(Format::Cif);
        }
        if [
            "ATOM  ", "HETATM", "HEADER", "TITLE ", "COMPND", "REMARK", "CRYST1", "HELIX ",
            "SHEET ", "MODEL ",
        ]
        .iter()
        .any(|tag| line.starts_with(tag))
        {
            return Ok(Format::Pdb);
        }
    }
    Err(MolError::UnknownFormat)
}

pub fn parse(bytes: &[u8], format: Format, limits: Limits) -> MolResult<Structure> {
    if bytes.len() > limits.max_bytes {
        return Err(MolError::TooLarge);
    }
    let text = std::str::from_utf8(bytes).map_err(|_| MolError::NotText)?;
    if text.contains('\0') {
        return Err(MolError::NotText);
    }
    let format = if format == Format::Auto {
        detect(text)?
    } else {
        format
    };
    let structure = match format {
        Format::Cif => cif::parse(Lines::new(text, limits.max_line), limits.max_atoms)?,
        Format::Pdb | Format::Auto => {
            pdb::parse(Lines::new(text, limits.max_line), limits.max_atoms)?
        }
    };
    if structure.atoms.is_empty() {
        return Err(MolError::Empty);
    }
    Ok(structure)
}

pub(crate) fn coordinate(raw: &str, line: u32) -> MolResult<f32> {
    let value: f32 = raw.trim().parse().map_err(|_| MolError::BadNumber(line))?;
    if value.is_finite() && value.abs() < 1.0e5 {
        Ok(value)
    } else {
        Err(MolError::BadNumber(line))
    }
}

pub(crate) fn clip(raw: &str, max: usize) -> String {
    raw.trim()
        .chars()
        .filter(|c| c.is_ascii_graphic() || *c == ' ')
        .take(max)
        .collect()
}
