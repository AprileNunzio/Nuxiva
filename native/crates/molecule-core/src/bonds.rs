use crate::element::by_number;
use crate::model::{Atom, distance};
use std::collections::HashMap;

const CELL: f32 = 2.2;
const TOLERANCE: f32 = 0.45;
const MIN_BOND: f32 = 0.4;
const MAX_PER_ATOM: usize = 6;

type Cell = (i32, i32, i32);

#[allow(clippy::cast_possible_truncation)]
fn cell_of(position: [f32; 3]) -> Cell {
    let f = |v: f32| (v / CELL).floor().clamp(-1.0e6, 1.0e6) as i32;
    (f(position[0]), f(position[1]), f(position[2]))
}

fn bonded(a: &Atom, b: &Atom) -> bool {
    if a.element == 1 && b.element == 1 {
        return false;
    }
    let limit = by_number(a.element).covalent + by_number(b.element).covalent + TOLERANCE;
    let d = distance(a.position, b.position);
    d > MIN_BOND && d < limit
}

#[must_use]
pub fn infer(atoms: &[Atom], indices: &[u32]) -> Vec<[u32; 2]> {
    let mut grid: HashMap<Cell, Vec<u32>> = HashMap::new();
    for &i in indices {
        if let Some(atom) = atoms.get(i as usize) {
            grid.entry(cell_of(atom.position)).or_default().push(i);
        }
    }
    let mut out = Vec::new();
    for &i in indices {
        let Some(a) = atoms.get(i as usize) else {
            continue;
        };
        let (cx, cy, cz) = cell_of(a.position);
        let mut count = 0_usize;
        for dx in -1..=1_i32 {
            for dy in -1..=1_i32 {
                for dz in -1..=1_i32 {
                    let key = (
                        cx.saturating_add(dx),
                        cy.saturating_add(dy),
                        cz.saturating_add(dz),
                    );
                    for &j in grid.get(&key).into_iter().flatten() {
                        if j <= i || count >= MAX_PER_ATOM {
                            continue;
                        }
                        if atoms.get(j as usize).is_some_and(|b| bonded(a, b)) {
                            out.push([i, j]);
                            count = count.saturating_add(1);
                        }
                    }
                }
            }
        }
    }
    out
}
