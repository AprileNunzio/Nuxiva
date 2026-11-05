use serde::Serialize;
use std::collections::BTreeSet;

#[derive(Debug, Clone, PartialEq)]
pub struct Atom {
    pub name: String,
    pub residue: String,
    pub chain: String,
    pub seq: i32,
    pub element: u8,
    pub position: [f32; 3],
    pub hetero: bool,
    pub b_factor: f32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SecondaryKind {
    Helix,
    Sheet,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct SecondaryRange {
    pub kind: SecondaryKind,
    pub chain: String,
    pub start: i32,
    pub end: i32,
}

#[derive(Debug, Clone, PartialEq, Default)]
pub struct Structure {
    pub title: String,
    pub atoms: Vec<Atom>,
    pub secondary: Vec<SecondaryRange>,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Summary {
    pub title: String,
    pub atoms: usize,
    pub hetero_atoms: usize,
    pub chains: Vec<String>,
    pub residues: usize,
    pub helices: usize,
    pub sheets: usize,
    pub center: [f32; 3],
    pub radius: f32,
}

impl Structure {
    #[must_use]
    pub fn secondary_of(&self, atom: &Atom) -> Option<SecondaryKind> {
        self.secondary
            .iter()
            .find(|s| s.chain == atom.chain && (s.start..=s.end).contains(&atom.seq))
            .map(|s| s.kind)
    }

    #[must_use]
    pub fn bounds(&self) -> ([f32; 3], f32) {
        let mut low = [f32::MAX; 3];
        let mut high = [f32::MIN; 3];
        for atom in &self.atoms {
            for ((l, h), v) in low.iter_mut().zip(high.iter_mut()).zip(atom.position) {
                *l = l.min(v);
                *h = h.max(v);
            }
        }
        if self.atoms.is_empty() {
            return ([0.0; 3], 0.0);
        }
        let center = [
            (low[0] + high[0]) * 0.5,
            (low[1] + high[1]) * 0.5,
            (low[2] + high[2]) * 0.5,
        ];
        let radius = self
            .atoms
            .iter()
            .map(|a| distance(a.position, center))
            .fold(0.0_f32, f32::max);
        (center, radius)
    }

    #[must_use]
    pub fn summary(&self) -> Summary {
        let chains: BTreeSet<&str> = self.atoms.iter().map(|a| a.chain.as_str()).collect();
        let residues: BTreeSet<(&str, i32)> = self
            .atoms
            .iter()
            .filter(|a| !a.hetero)
            .map(|a| (a.chain.as_str(), a.seq))
            .collect();
        let (center, radius) = self.bounds();
        Summary {
            title: self.title.clone(),
            atoms: self.atoms.len(),
            hetero_atoms: self.atoms.iter().filter(|a| a.hetero).count(),
            chains: chains.into_iter().map(str::to_owned).collect(),
            residues: residues.len(),
            helices: self
                .secondary
                .iter()
                .filter(|s| s.kind == SecondaryKind::Helix)
                .count(),
            sheets: self
                .secondary
                .iter()
                .filter(|s| s.kind == SecondaryKind::Sheet)
                .count(),
            center,
            radius,
        }
    }
}

#[must_use]
pub fn distance(a: [f32; 3], b: [f32; 3]) -> f32 {
    let (dx, dy, dz) = (a[0] - b[0], a[1] - b[1], a[2] - b[2]);
    (dx * dx + dy * dy + dz * dz).sqrt()
}
