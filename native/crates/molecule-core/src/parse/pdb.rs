use super::{Lines, clip, coordinate};
use crate::element;
use crate::error::{MolError, MolResult};
use crate::model::{Atom, SecondaryKind, SecondaryRange, Structure};

fn field(line: &str, start: usize, end: usize) -> &str {
    let end = end.min(line.len());
    line.get(start..end).unwrap_or("")
}

fn seq(raw: &str, line: u32) -> MolResult<i32> {
    raw.trim().parse().map_err(|_| MolError::BadNumber(line))
}

fn atom(line: &str, number: u32) -> MolResult<Atom> {
    let name = clip(field(line, 12, 16), 4);
    let symbol = field(line, 76, 78).trim();
    let found = if symbol.is_empty() {
        element::from_atom_name(&name)
    } else {
        element::by_symbol(symbol)
    };
    Ok(Atom {
        residue: clip(field(line, 17, 20), 3),
        chain: clip(field(line, 21, 22), 4),
        seq: seq(field(line, 22, 26), number)?,
        position: [
            coordinate(field(line, 30, 38), number)?,
            coordinate(field(line, 38, 46), number)?,
            coordinate(field(line, 46, 54), number)?,
        ],
        b_factor: field(line, 60, 66)
            .trim()
            .parse()
            .ok()
            .filter(|v: &f32| v.is_finite())
            .unwrap_or(0.0),
        element: found.number,
        hetero: line.starts_with("HETATM"),
        name,
    })
}

fn range(line: &str, number: u32, kind: SecondaryKind) -> MolResult<SecondaryRange> {
    let (chain, start, end) = match kind {
        SecondaryKind::Helix => (
            field(line, 19, 20),
            field(line, 21, 25),
            field(line, 33, 37),
        ),
        SecondaryKind::Sheet => (
            field(line, 21, 22),
            field(line, 22, 26),
            field(line, 33, 37),
        ),
    };
    let (start, end) = (seq(start, number)?, seq(end, number)?);
    Ok(SecondaryRange {
        kind,
        chain: clip(chain, 4),
        start: start.min(end),
        end: start.max(end),
    })
}

pub(super) fn parse(lines: Lines<'_>, max_atoms: usize) -> MolResult<Structure> {
    let mut structure = Structure::default();
    for entry in lines {
        let (number, line) = entry?;
        if line.starts_with("ENDMDL") || line.starts_with("END   ") || line == "END" {
            break;
        }
        if line.starts_with("ATOM  ") || line.starts_with("HETATM") {
            let alt = field(line, 16, 17).trim();
            if !(alt.is_empty() || alt == "A") {
                continue;
            }
            if structure.atoms.len() >= max_atoms {
                return Err(MolError::TooManyAtoms);
            }
            structure.atoms.push(atom(line, number)?);
        } else if line.starts_with("HELIX ") {
            structure
                .secondary
                .push(range(line, number, SecondaryKind::Helix)?);
        } else if line.starts_with("SHEET ") {
            structure
                .secondary
                .push(range(line, number, SecondaryKind::Sheet)?);
        } else if line.starts_with("TITLE ") && structure.title.len() < 160 {
            let part = clip(field(line, 10, 80), 80);
            if !structure.title.is_empty() {
                structure.title.push(' ');
            }
            structure.title.push_str(&part);
        }
        if structure.secondary.len() > 100_000 {
            return Err(MolError::TooManyAtoms);
        }
    }
    structure.title = clip(&structure.title, 160);
    Ok(structure)
}
