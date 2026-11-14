#![allow(clippy::indexing_slicing, clippy::arithmetic_side_effects)]

use crate::mel::{DIM, Feat};

fn cost(a: &Feat, b: &Feat) -> f32 {
    let sum: f32 = a.iter().zip(b).map(|(x, y)| (x - y) * (x - y)).sum();
    (sum / DIM as f32).sqrt()
}

#[must_use]
pub fn distance(a: &[Feat], b: &[Feat], abandon: f32) -> Option<f32> {
    let (n, m) = (a.len(), b.len());
    if n == 0 || m == 0 {
        return None;
    }
    let longer = n.max(m);
    let shorter = n.min(m);
    if longer > shorter.saturating_mul(2).saturating_add(4) {
        return None;
    }
    let band = (longer / 3).max(6);
    let norm = (n + m) as f32;
    let limit = abandon * norm;
    let mut prev = vec![f32::INFINITY; m + 1];
    let mut cur = vec![f32::INFINITY; m + 1];
    prev[0] = 0.0;
    for i in 1..=n {
        cur.fill(f32::INFINITY);
        let centre = (i * m) / n;
        let lo = centre.saturating_sub(band).max(1);
        let hi = (centre + band).min(m);
        let mut row_min = f32::INFINITY;
        for j in lo..=hi {
            let best = prev[j].min(prev[j - 1]).min(cur[j - 1]);
            if best.is_finite() {
                let c = cost(&a[i - 1], &b[j - 1]) + best;
                cur[j] = c;
                row_min = row_min.min(c);
            }
        }
        if row_min > limit {
            return None;
        }
        std::mem::swap(&mut prev, &mut cur);
    }
    let total = prev[m];
    total.is_finite().then_some(total / norm)
}
