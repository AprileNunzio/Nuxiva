use serde::Serialize;

use crate::geom::Part;
use crate::plan::Shape;

const TOUCH: f64 = 0.03;
const FLAT: f64 = 0.06;
const SPARSE: usize = 5;

#[derive(Debug, Clone, Serialize)]
pub struct Report {
    pub parts: usize,
    pub extent: [f64; 3],
    pub components: usize,
    pub loose: Vec<LoosePart>,
    pub asymmetry: f64,
    pub issues: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct LoosePart {
    pub shape: Shape,
    pub at: [f64; 3],
}

type Box3 = ([f64; 3], [f64; 3]);

fn rotate(p: [f64; 3], deg: [f64; 3]) -> [f64; 3] {
    let [rx, ry, rz] = deg.map(f64::to_radians);
    let [x, y, z] = p;
    let (y, z) = (y * rx.cos() - z * rx.sin(), y * rx.sin() + z * rx.cos());
    let (x, z) = (x * ry.cos() + z * ry.sin(), -x * ry.sin() + z * ry.cos());
    let (x, y) = (x * rz.cos() - y * rz.sin(), x * rz.sin() + y * rz.cos());
    [x, y, z]
}

fn bounds(part: &Part) -> Box3 {
    let mut lo = [f64::MAX; 3];
    let mut hi = [f64::MIN; 3];
    let [sx, sy, sz] = part.size;
    for ix in [-1.0, 1.0] {
        for iy in [-1.0, 1.0] {
            for iz in [-1.0, 1.0] {
                let p = rotate([sx * ix, sy * iy, sz * iz], part.rot);
                for (axis, value) in p.iter().enumerate() {
                    let centre = part.at.get(axis).copied().unwrap_or(0.0) + value;
                    if let Some(l) = lo.get_mut(axis) {
                        *l = l.min(centre);
                    }
                    if let Some(h) = hi.get_mut(axis) {
                        *h = h.max(centre);
                    }
                }
            }
        }
    }
    (lo, hi)
}

fn touches(a: &Box3, b: &Box3, gap: f64) -> bool {
    a.0.iter()
        .zip(&a.1)
        .zip(b.0.iter().zip(&b.1))
        .all(|((alo, ahi), (blo, bhi))| *alo <= bhi + gap && *blo <= ahi + gap)
}

fn root(parent: &mut [usize], mut i: usize) -> usize {
    while let Some(next) = parent.get(i).copied() {
        if next == i {
            break;
        }
        let up = parent.get(next).copied().unwrap_or(next);
        if let Some(slot) = parent.get_mut(i) {
            *slot = up;
        }
        i = up;
    }
    i
}

#[must_use]
pub fn inspect(parts: &[Part], scale: f64) -> Report {
    let k = if scale.is_finite() && scale > 1e-9 {
        scale
    } else {
        1.0
    };
    let boxes: Vec<Box3> = parts.iter().map(bounds).collect();
    let mut lo = [f64::MAX; 3];
    let mut hi = [f64::MIN; 3];
    for (blo, bhi) in &boxes {
        for axis in 0..3 {
            if let (Some(l), Some(b)) = (lo.get_mut(axis), blo.get(axis)) {
                *l = l.min(*b);
            }
            if let Some((h, b)) = hi.get_mut(axis).zip(bhi.get(axis)) {
                *h = h.max(*b);
            }
        }
    }
    let extent = [0, 1, 2]
        .map(|a| (hi.get(a).copied().unwrap_or(0.0) - lo.get(a).copied().unwrap_or(0.0)).max(0.0));
    let size = extent.map(|v| v / k);
    let longest = extent.iter().copied().fold(0.0_f64, f64::max);
    let gap = TOUCH * longest;
    let mut parent: Vec<usize> = (0..boxes.len()).collect();
    for i in 0..boxes.len() {
        for j in i.saturating_add(1)..boxes.len() {
            if boxes
                .get(i)
                .zip(boxes.get(j))
                .is_some_and(|(a, b)| touches(a, b, gap))
            {
                let (ri, rj) = (root(&mut parent, i), root(&mut parent, j));
                if let Some(slot) = parent.get_mut(rj.max(ri)) {
                    *slot = rj.min(ri);
                }
            }
        }
    }
    let mut sizes = vec![0_usize; boxes.len()];
    for i in 0..boxes.len() {
        let r = root(&mut parent, i);
        if let Some(count) = sizes.get_mut(r) {
            *count = count.saturating_add(1);
        }
    }
    let components = sizes.iter().filter(|c| **c > 0).count();
    let main = sizes
        .iter()
        .enumerate()
        .max_by_key(|(i, c)| (**c, usize::MAX.saturating_sub(*i)))
        .map_or(0, |(i, _)| i);
    let loose: Vec<LoosePart> = (0..boxes.len())
        .filter(|i| root(&mut parent, *i) != main)
        .filter_map(|i| parts.get(i))
        .map(|p| LoosePart {
            shape: p.shape,
            at: p.at.map(|v| v / k),
        })
        .collect();
    let mass: f64 = parts.iter().map(|p| p.weight).sum();
    let moment: f64 = parts
        .iter()
        .map(|p| p.weight * p.at.first().copied().unwrap_or(0.0))
        .sum();
    let width = extent.first().copied().unwrap_or(0.0);
    let asymmetry = if mass > 0.0 && width > 0.0 {
        (moment / mass).abs() / width
    } else {
        0.0
    };
    let mut issues = Vec::new();
    if components > 1 {
        issues.push("detached_parts".to_owned());
    }
    if longest > 0.0 && extent.iter().copied().fold(f64::MAX, f64::min) < FLAT * longest {
        issues.push("flat".to_owned());
    }
    if parts.len() < SPARSE {
        issues.push("too_few_parts".to_owned());
    }
    Report {
        parts: parts.len(),
        extent: size,
        components,
        loose,
        asymmetry,
        issues,
    }
}
