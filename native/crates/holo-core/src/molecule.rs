use serde_json::{Value, json};

use crate::dna::{ball, rod};
use crate::error::{HoloError, HoloResult};
use crate::{layout, parse};

pub const MAX_TEXT: usize = 8 * 1024 * 1024;
pub const MAX_ATOMS: usize = 160;
pub const MAX_BONDS: usize = 240;
pub const MAX_RESIDUES: usize = 190;
pub const GENERATED_PARTS: usize = 400;
const MIN_ATOMS: usize = 2;
const BOND_COLOR: &str = "#b8c4d6";
const CHAIN_COLORS: [&str; 8] = [
    "#5ef2ff", "#ff6b9d", "#ffd166", "#06d6a0", "#a78bfa", "#ff9f1c", "#4cc9f0", "#f15bb5",
];
const CA_GAP: f32 = 4.4;

fn style(element: &str) -> (&'static str, f32) {
    match element {
        "H" => ("#f1f5f9", 0.24),
        "C" => ("#8d99ae", 0.38),
        "N" => ("#3a6bff", 0.36),
        "O" => ("#ff3b3b", 0.35),
        "S" => ("#ffe14d", 0.48),
        "P" => ("#ff8c1a", 0.48),
        "F" | "Cl" => ("#3ddc84", 0.42),
        "Br" => ("#b5452f", 0.46),
        "I" => ("#9b30c7", 0.5),
        "Fe" => ("#e06633", 0.5),
        "Na" | "K" => ("#a35cf2", 0.55),
        "Ca" | "Mg" => ("#7bdc3a", 0.52),
        _ => ("#ff4fb3", 0.45),
    }
}

fn field(line: &str, from: usize, to: usize) -> Option<&str> {
    line.get(from..to.min(line.len())).map(str::trim)
}

fn number(line: &str, from: usize, to: usize) -> HoloResult<f32> {
    let value: f32 = field(line, from, to)
        .and_then(|v| v.parse().ok())
        .ok_or(HoloError::BadModel)?;
    if value.is_finite() && value.abs() < 10_000.0 {
        Ok(value)
    } else {
        Err(HoloError::BadModel)
    }
}

fn count(line: &str, from: usize, to: usize) -> HoloResult<usize> {
    field(line, from, to)
        .and_then(|v| v.parse().ok())
        .ok_or(HoloError::BadModel)
}

fn element(raw: &str) -> String {
    let mut chars = raw.chars().filter(char::is_ascii_alphabetic);
    let mut out = String::new();
    if let Some(first) = chars.next() {
        out.push(first.to_ascii_uppercase());
    }
    if let Some(second) = chars.next() {
        out.push(second.to_ascii_lowercase());
    }
    out
}

fn bond_radius(order: usize) -> f32 {
    match order {
        2 => 0.17,
        3 => 0.22,
        _ => 0.12,
    }
}

pub fn sdf_parts(text: &str) -> HoloResult<Vec<Value>> {
    if text.len() > MAX_TEXT {
        return Err(HoloError::TooLarge);
    }
    let lines: Vec<&str> = text.lines().collect();
    let counts = lines.get(3).ok_or(HoloError::BadModel)?;
    if !counts.contains("V2000") {
        return Err(HoloError::BadModel);
    }
    let atoms = count(counts, 0, 3)?;
    let bonds = count(counts, 3, 6)?;
    if !(MIN_ATOMS..=MAX_ATOMS).contains(&atoms) || bonds > MAX_BONDS {
        return Err(HoloError::BadModel);
    }
    let mut placed: Vec<([f32; 3], String)> = Vec::with_capacity(atoms);
    for line in lines.iter().skip(4).take(atoms) {
        let at = [
            number(line, 0, 10)?,
            number(line, 10, 20)?,
            number(line, 20, 30)?,
        ];
        let symbol = element(field(line, 31, 34).unwrap_or(""));
        if symbol.is_empty() {
            return Err(HoloError::BadModel);
        }
        placed.push((at, symbol));
    }
    if placed.len() != atoms {
        return Err(HoloError::BadModel);
    }
    let mut out = Vec::with_capacity(atoms.saturating_add(bonds));
    for line in lines.iter().skip(atoms.saturating_add(4)).take(bonds) {
        let a = count(line, 0, 3)?
            .checked_sub(1)
            .ok_or(HoloError::BadModel)?;
        let b = count(line, 3, 6)?
            .checked_sub(1)
            .ok_or(HoloError::BadModel)?;
        let order = count(line, 6, 9).unwrap_or(1);
        let (Some(from), Some(to)) = (placed.get(a), placed.get(b)) else {
            return Err(HoloError::BadModel);
        };
        out.push(rod("bond", from.0, to.0, bond_radius(order), BOND_COLOR, 0));
    }
    for (at, symbol) in &placed {
        let (color, radius) = style(symbol);
        out.push(ball(&format!("atom_{symbol}"), *at, radius, color, 0));
    }
    Ok(out)
}

fn chain_color(index: usize) -> &'static str {
    let slot = index.checked_rem(CHAIN_COLORS.len()).unwrap_or(0);
    CHAIN_COLORS.get(slot).copied().unwrap_or("#5ef2ff")
}

fn distance(a: [f32; 3], b: [f32; 3]) -> f32 {
    ((a[0] - b[0]).powi(2) + (a[1] - b[1]).powi(2) + (a[2] - b[2]).powi(2)).sqrt()
}

fn carbons(text: &str) -> HoloResult<Vec<([f32; 3], char)>> {
    let mut found = Vec::new();
    for line in text.lines() {
        if line.starts_with("ENDMDL") {
            break;
        }
        if !line.starts_with("ATOM") || field(line, 12, 16) != Some("CA") {
            continue;
        }
        let alt = line.get(16..17).unwrap_or(" ");
        if alt != " " && alt != "A" {
            continue;
        }
        let chain = line
            .get(21..22)
            .and_then(|c| c.chars().next())
            .unwrap_or('A');
        let chain = if chain.is_ascii_alphanumeric() {
            chain
        } else {
            'A'
        };
        found.push((
            [
                number(line, 30, 38)?,
                number(line, 38, 46)?,
                number(line, 46, 54)?,
            ],
            chain,
        ));
    }
    if found.len() < MIN_ATOMS {
        return Err(HoloError::BadModel);
    }
    Ok(found)
}

pub fn pdb_parts(text: &str) -> HoloResult<Vec<Value>> {
    if text.len() > MAX_TEXT {
        return Err(HoloError::TooLarge);
    }
    let all = carbons(text)?;
    let stride = all.len().div_ceil(MAX_RESIDUES).max(1);
    let mut chains: Vec<char> = Vec::new();
    let mut out = Vec::new();
    let mut previous: Option<([f32; 3], char)> = None;
    #[allow(clippy::cast_precision_loss)]
    let gap = CA_GAP * stride as f32 * 1.25;
    for (at, chain) in all.into_iter().step_by(stride) {
        let index = if let Some(found) = chains.iter().position(|c| *c == chain) {
            found
        } else {
            chains.push(chain);
            chains.len().saturating_sub(1)
        };
        let color = chain_color(index);
        let name = format!("protein_chain_{chain}");
        if let Some((last, last_chain)) = previous
            && last_chain == chain
            && distance(last, at) <= gap
        {
            out.push(rod(&name, last, at, 0.75, color, 0));
        }
        out.push(ball(&name, at, 1.25, color, 0));
        previous = Some((at, chain));
    }
    Ok(out)
}

fn scene(title: &str, parts: &[Value]) -> HoloResult<String> {
    let input = json!({"title": title, "source": "model", "parts": parts});
    let built = layout::arrange(parse::scene_limited(&input, GENERATED_PARTS)?);
    serde_json::to_string(&built).map_err(|_| HoloError::BadJson)
}

pub fn generate(kind: &str, text: &str, title: &str) -> HoloResult<String> {
    match kind {
        "sdf" => scene(title, &sdf_parts(text)?),
        "pdb" => scene(title, &pdb_parts(text)?),
        _ => Err(HoloError::BadModel),
    }
}
