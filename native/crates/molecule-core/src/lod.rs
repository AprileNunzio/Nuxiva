use crate::bonds;
use crate::element::by_number;
use crate::model::{SecondaryKind, Structure, Summary};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Lod {
    Atoms,
    Backbone,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ColorScheme {
    Element,
    Chain,
    Secondary,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Built {
    pub summary: Summary,
    pub positions: Vec<f32>,
    pub colors: Vec<u8>,
    pub bonds: Vec<u32>,
}

const PALETTE: [[u8; 3]; 8] = [
    [41, 224, 255],
    [255, 181, 71],
    [61, 255, 168],
    [255, 92, 138],
    [160, 120, 255],
    [255, 240, 110],
    [90, 160, 255],
    [255, 140, 60],
];
const BACKBONE: [&str; 2] = ["CA", "P"];
const BACKBONE_RADIUS: f32 = 0.9;
const MAX_TRACE: f32 = 7.5;

fn chain_color(chains: &[String], chain: &str) -> [u8; 3] {
    let index = chains.iter().position(|c| c == chain).unwrap_or(0);
    PALETTE
        .get(index.checked_rem(PALETTE.len()).unwrap_or(0))
        .copied()
        .unwrap_or([255, 255, 255])
}

fn secondary_color(kind: Option<SecondaryKind>) -> [u8; 3] {
    match kind {
        Some(SecondaryKind::Helix) => [255, 92, 138],
        Some(SecondaryKind::Sheet) => [255, 200, 60],
        None => [170, 190, 210],
    }
}

#[must_use]
#[allow(clippy::cast_possible_truncation)]
pub fn build(structure: &Structure, lod: Lod, scheme: ColorScheme) -> Built {
    let summary = structure.summary();
    let center = summary.center;
    let picked: Vec<u32> = structure
        .atoms
        .iter()
        .enumerate()
        .filter(|(_, a)| lod == Lod::Atoms || (!a.hetero && BACKBONE.contains(&a.name.as_str())))
        .filter_map(|(i, _)| u32::try_from(i).ok())
        .collect();
    let mut positions = Vec::with_capacity(picked.len().saturating_mul(4));
    let mut colors = Vec::with_capacity(picked.len().saturating_mul(4));
    for &i in &picked {
        let Some(atom) = structure.atoms.get(i as usize) else {
            continue;
        };
        let element = by_number(atom.element);
        let radius = if lod == Lod::Backbone {
            BACKBONE_RADIUS
        } else {
            element.vdw * 0.3
        };
        positions.extend([
            atom.position[0] - center[0],
            atom.position[1] - center[1],
            atom.position[2] - center[2],
            radius,
        ]);
        let rgb = match scheme {
            ColorScheme::Element => element.color,
            ColorScheme::Chain => chain_color(&summary.chains, &atom.chain),
            ColorScheme::Secondary => secondary_color(structure.secondary_of(atom)),
        };
        colors.extend([rgb[0], rgb[1], rgb[2], if atom.hetero { 200 } else { 255 }]);
    }
    let pairs = match lod {
        Lod::Atoms => bonds::infer(&structure.atoms, &picked),
        Lod::Backbone => trace(structure, &picked),
    };
    let lookup: std::collections::HashMap<u32, u32> = picked
        .iter()
        .enumerate()
        .filter_map(|(k, &i)| Some((i, u32::try_from(k).ok()?)))
        .collect();
    let bonds = pairs
        .iter()
        .filter_map(|[a, b]| Some([*lookup.get(a)?, *lookup.get(b)?]))
        .flatten()
        .collect();
    Built {
        summary,
        positions,
        colors,
        bonds,
    }
}

fn trace(structure: &Structure, picked: &[u32]) -> Vec<[u32; 2]> {
    picked
        .windows(2)
        .filter_map(|w| {
            let (&i, &j) = (w.first()?, w.get(1)?);
            let (a, b) = (
                structure.atoms.get(i as usize)?,
                structure.atoms.get(j as usize)?,
            );
            (a.chain == b.chain && crate::model::distance(a.position, b.position) < MAX_TRACE)
                .then_some([i, j])
        })
        .collect()
}
