#![allow(clippy::cast_precision_loss)]

use crate::image::Gray;

pub const SIDE: usize = 112;
pub const GRID: usize = 7;
pub const BINS: usize = 59;
pub const CELLS: usize = GRID * GRID;
pub const HIST_DIM: usize = CELLS * BINS;
pub const MARKS_DIM: usize = HIST_DIM + CELLS;
pub const PAIR_WEIGHT: f32 = 10.0;
pub const MAX_WEIGHT: f32 = 60.0;

const OFFSETS: [(isize, isize); 8] = [
    (-1, -1),
    (0, -1),
    (1, -1),
    (1, 0),
    (1, 1),
    (0, 1),
    (-1, 1),
    (-1, 0),
];

fn transitions(code: u8) -> u32 {
    (code ^ code.rotate_left(1)).count_ones()
}

fn uniform_table() -> [u8; 256] {
    let mut table = [0_u8; 256];
    let mut next = 0_u8;
    for (code, slot) in (0_u8..=255).zip(table.iter_mut()) {
        if transitions(code) <= 2 {
            *slot = next;
            next = next.saturating_add(1);
        } else {
            *slot = 58;
        }
    }
    table
}

fn pixel(img: &[f32], x: usize, y: usize) -> f32 {
    img.get(y.saturating_mul(SIDE).saturating_add(x))
        .copied()
        .unwrap_or(0.0)
}

fn lbp_grid(img: &[f32], mirror: bool) -> Vec<f32> {
    let table = uniform_table();
    let mut hist = vec![0.0_f32; HIST_DIM];
    let cell = SIDE / GRID;
    for y in 1..SIDE.saturating_sub(1) {
        for x in 1..SIDE.saturating_sub(1) {
            let sx = if mirror {
                SIDE.saturating_sub(1).saturating_sub(x)
            } else {
                x
            };
            let centre = pixel(img, sx, y);
            let mut code = 0_u8;
            for (bit, (dx, dy)) in OFFSETS.iter().enumerate() {
                let dx = if mirror { dx.saturating_neg() } else { *dx };
                let nx = sx.saturating_add_signed(dx);
                let ny = y.saturating_add_signed(*dy);
                if pixel(img, nx, ny) >= centre {
                    code |= 1_u8 << bit;
                }
            }
            let c = (y / cell)
                .min(GRID.saturating_sub(1))
                .saturating_mul(GRID)
                .saturating_add((x / cell).min(GRID.saturating_sub(1)));
            let bin = usize::from(table.get(usize::from(code)).copied().unwrap_or(58));
            if let Some(slot) = hist.get_mut(c.saturating_mul(BINS).saturating_add(bin)) {
                *slot += 1.0;
            }
        }
    }
    for chunk in hist.chunks_exact_mut(BINS) {
        let total: f32 = chunk.iter().sum();
        let mut norm = 0.0_f32;
        for v in chunk.iter_mut() {
            *v = (*v / total.max(1.0)).sqrt();
            norm += *v * *v;
        }
        let norm = norm.sqrt().max(1e-9);
        for v in chunk.iter_mut() {
            *v /= norm;
        }
    }
    hist
}

#[must_use]
pub fn cell_similarity(a: &[f32], b: &[f32]) -> Vec<f32> {
    a.chunks_exact(BINS)
        .zip(b.chunks_exact(BINS))
        .take(CELLS)
        .map(|(x, y)| x.iter().zip(y).map(|(p, q)| p * q).sum())
        .collect()
}

#[must_use]
pub fn signature(gray: &Gray<'_>) -> Vec<f32> {
    let img = gray.resample(SIDE);
    let mean = img.iter().sum::<f32>() / img.len().max(1) as f32;
    let var = img.iter().map(|v| (v - mean) * (v - mean)).sum::<f32>() / img.len().max(1) as f32;
    let std = var.sqrt().max(1.0);
    let normalised: Vec<f32> = img.iter().map(|v| (v - mean) / std).collect();
    let plain = lbp_grid(&normalised, false);
    let mirrored = lbp_grid(&normalised, true);
    let asym: Vec<f32> = cell_similarity(&plain, &mirrored)
        .into_iter()
        .map(|s| (1.0 - s).clamp(0.0, 1.0))
        .collect();
    let mut out = plain;
    out.extend(asym);
    out
}

#[must_use]
pub fn mean_signature(rows: &[Vec<f32>]) -> Option<Vec<f32>> {
    if rows.is_empty() {
        return None;
    }
    let mut sum = vec![0.0_f32; MARKS_DIM];
    for row in rows {
        for (s, v) in sum.iter_mut().zip(row) {
            *s += v;
        }
    }
    #[allow(clippy::cast_precision_loss)]
    let n = rows.len() as f32;
    let (hist, asym) = sum.split_at_mut(HIST_DIM);
    for chunk in hist.chunks_exact_mut(BINS) {
        let norm = chunk.iter().map(|v| v * v).sum::<f32>().sqrt().max(1e-9);
        for v in chunk.iter_mut() {
            *v /= norm;
        }
    }
    for v in asym.iter_mut() {
        *v /= n;
    }
    Some(sum)
}

#[must_use]
pub fn pair_weights(a: &[f32], b: &[f32]) -> Vec<f32> {
    let gaps: Vec<f32> = cell_similarity(a, b)
        .iter()
        .map(|s| (1.0 - s).max(0.0))
        .collect();
    let mut sorted = gaps.clone();
    sorted.sort_by(f32::total_cmp);
    let median = sorted
        .get(sorted.len() / 2)
        .copied()
        .unwrap_or(0.0)
        .max(1e-4);
    gaps.iter()
        .map(|g| 1.0 + (PAIR_WEIGHT * (g - median).max(0.0) / median).min(MAX_WEIGHT))
        .collect()
}

#[must_use]
pub fn pair_scores(probe: &[f32], a: &[f32], b: &[f32]) -> (f32, f32) {
    let weights = pair_weights(a, b);
    let total: f32 = weights.iter().sum::<f32>().max(1e-9);
    let score = |m: &[f32]| {
        let cells = cell_similarity(probe, m);
        let asym_p = probe.get(HIST_DIM..).unwrap_or_default();
        let asym_m = m.get(HIST_DIM..).unwrap_or_default();
        let asym = 1.0
            - asym_p
                .iter()
                .zip(asym_m)
                .zip(&weights)
                .map(|((x, y), w)| (x - y).abs() * w)
                .sum::<f32>()
                / total;
        let texture = cells.iter().zip(&weights).map(|(s, w)| s * w).sum::<f32>() / total;
        0.85 * texture + 0.15 * asym
    };
    (score(a), score(b))
}

fn row_deviation(mean: &[f32]) -> Vec<f32> {
    let hist = mean.get(..HIST_DIM).unwrap_or_default();
    let cells: Vec<&[f32]> = hist.chunks_exact(BINS).collect();
    (0..CELLS)
        .map(|c| {
            let row = c / GRID;
            let Some(own) = cells.get(c) else {
                return 0.0;
            };
            let mut avg = vec![0.0_f32; BINS];
            for other in (row.saturating_mul(GRID)..row.saturating_add(1).saturating_mul(GRID))
                .filter(|o| *o != c)
            {
                if let Some(h) = cells.get(other) {
                    for (a, v) in avg.iter_mut().zip(h.iter()) {
                        *a += v;
                    }
                }
            }
            let norm = avg.iter().map(|v| v * v).sum::<f32>().sqrt().max(1e-9);
            1.0 - own.iter().zip(&avg).map(|(a, b)| a * b / norm).sum::<f32>()
        })
        .collect()
}

#[derive(Debug, Clone, PartialEq)]
pub struct Mark {
    pub region: &'static str,
    pub side: &'static str,
    pub strength: f32,
}

fn region(row: usize) -> &'static str {
    match row {
        0 => "forehead",
        1 => "brow",
        2 => "eye",
        3 => "cheek",
        4 => "nose",
        5 => "mouth",
        _ => "chin",
    }
}

#[must_use]
pub fn distinctive(rows: &[Vec<f32>], limit: f32, max: usize) -> Vec<Mark> {
    if rows.len() < 3 {
        return Vec::new();
    }
    let stats: Vec<(usize, f32, f32)> = (0..CELLS)
        .map(|c| {
            let values: Vec<f32> = rows
                .iter()
                .filter_map(|r| r.get(HIST_DIM.saturating_add(c)).copied())
                .collect();
            let n = values.len().max(1) as f32;
            let mean = values.iter().sum::<f32>() / n;
            let var = values.iter().map(|v| (v - mean) * (v - mean)).sum::<f32>() / n;
            (c, mean, var.sqrt())
        })
        .filter(|(c, _, _)| c % GRID != GRID / 2)
        .collect();
    let mut means: Vec<f32> = stats.iter().map(|s| s.1).collect();
    means.sort_by(f32::total_cmp);
    let median = means.get(means.len() / 2).copied().unwrap_or(0.0);
    let deviation = row_deviation(&mean_signature(rows).unwrap_or_default());
    let dev = |c: usize| deviation.get(c).copied().unwrap_or(0.0);
    let mut cells: Vec<(usize, f32)> = stats
        .into_iter()
        .map(|(c, mean, std)| (c, mean - std - median))
        .filter(|(c, v)| {
            let row = c / GRID;
            let mirror = row
                .saturating_mul(GRID)
                .saturating_add(GRID.saturating_sub(1).saturating_sub(c % GRID));
            *v >= limit && dev(*c) >= dev(mirror)
        })
        .collect();
    cells.sort_by(|a, b| b.1.total_cmp(&a.1));
    cells
        .into_iter()
        .take(max)
        .map(|(c, strength)| {
            let col = c % GRID;
            Mark {
                region: region(c / GRID),
                side: if col < GRID / 2 { "right" } else { "left" },
                strength,
            }
        })
        .collect()
}
