pub const MIN_DIM: usize = 16;
pub const MAX_DIM: usize = 1024;
pub const MAX_ROWS: usize = 4096;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RowsError {
    Dimension,
    Misaligned,
    TooMany,
}

impl RowsError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Dimension => "face.rows.dimension",
            Self::Misaligned => "face.rows.misaligned",
            Self::TooMany => "face.rows.too_many",
        }
    }
}

#[must_use]
pub fn dot(a: &[f32], b: &[f32]) -> f32 {
    a.iter().zip(b).map(|(x, y)| x * y).sum()
}

#[must_use]
pub fn norm(v: &[f32]) -> f32 {
    dot(v, v).sqrt()
}

#[must_use]
pub fn unit(v: &[f32]) -> Vec<f32> {
    let n = norm(v).max(1e-9);
    v.iter().map(|x| x / n).collect()
}

pub fn decode_rows(bytes: &[u8], dim: usize) -> Result<Vec<Vec<f32>>, RowsError> {
    if !(MIN_DIM..=MAX_DIM).contains(&dim) {
        return Err(RowsError::Dimension);
    }
    let width = dim.saturating_mul(4);
    if bytes.len().checked_rem(width) != Some(0) {
        return Err(RowsError::Misaligned);
    }
    if bytes.len().checked_div(width).unwrap_or(usize::MAX) > MAX_ROWS {
        return Err(RowsError::TooMany);
    }
    Ok(bytes
        .chunks_exact(width)
        .map(|row| {
            let values: Vec<f32> = row
                .chunks_exact(4)
                .map(|c| {
                    let v = f32::from_le_bytes([
                        c.first().copied().unwrap_or(0),
                        c.get(1).copied().unwrap_or(0),
                        c.get(2).copied().unwrap_or(0),
                        c.get(3).copied().unwrap_or(0),
                    ]);
                    if v.is_finite() { v } else { 0.0 }
                })
                .collect();
            unit(&values)
        })
        .collect())
}

#[must_use]
pub fn encode_rows(rows: &[Vec<f32>]) -> Vec<u8> {
    rows.iter()
        .flat_map(|r| r.iter().flat_map(|v| v.to_le_bytes()))
        .collect()
}

#[must_use]
pub fn sum_rows(rows: &[Vec<f32>], dim: usize) -> Vec<f32> {
    let mut sum = vec![0.0_f32; dim];
    for row in rows {
        for (s, v) in sum.iter_mut().zip(row) {
            *s += v;
        }
    }
    sum
}

#[must_use]
pub fn centroid(rows: &[Vec<f32>], dim: usize) -> Vec<f32> {
    unit(&sum_rows(rows, dim))
}

#[must_use]
pub fn score_against(rows: &[Vec<f32>], probe: &[f32]) -> f32 {
    let p = unit(probe);
    rows.iter()
        .map(|r| dot(r, &p))
        .fold(f32::NEG_INFINITY, f32::max)
        .max(-1.0)
}

#[must_use]
pub fn redundancy(rows: &[Vec<f32>]) -> Vec<f32> {
    if rows.len() < 2 {
        return vec![0.0; rows.len()];
    }
    rows.iter()
        .enumerate()
        .map(|(i, a)| {
            rows.iter()
                .enumerate()
                .filter(|(j, _)| *j != i)
                .map(|(_, b)| dot(a, b))
                .fold(-1.0_f32, f32::max)
        })
        .collect()
}

#[must_use]
pub fn prune(mut rows: Vec<Vec<f32>>, limit: usize) -> Vec<Vec<f32>> {
    while rows.len() > limit.max(1) {
        let mut scores = redundancy(&rows);
        if let Some(last) = scores.last_mut() {
            *last = -2.0;
        }
        let worst = scores
            .iter()
            .enumerate()
            .fold((0_usize, f32::NEG_INFINITY), |acc, (i, s)| {
                if *s > acc.1 { (i, *s) } else { acc }
            })
            .0;
        rows.remove(worst);
    }
    rows
}

#[must_use]
pub fn merge(old: Vec<Vec<f32>>, new: Vec<Vec<f32>>, limit: usize) -> Vec<Vec<f32>> {
    let mut all = old;
    all.extend(new);
    prune(all, limit)
}

#[must_use]
pub fn leave_one_out(rows: &[Vec<f32>], dim: usize) -> Vec<f32> {
    let sum = sum_rows(rows, dim);
    rows.iter()
        .map(|r| {
            let rest: Vec<f32> = sum.iter().zip(r).map(|(s, v)| s - v).collect();
            dot(r, &unit(&rest))
        })
        .collect()
}

#[must_use]
pub fn percentile(values: &[f32], p: f32) -> Option<f32> {
    if values.is_empty() {
        return None;
    }
    let mut sorted = values.to_vec();
    sorted.sort_by(f32::total_cmp);
    let top = sorted.len().saturating_sub(1);
    #[allow(
        clippy::cast_possible_truncation,
        clippy::cast_sign_loss,
        clippy::cast_precision_loss
    )]
    let at = ((top as f32) * p.clamp(0.0, 1.0)).floor() as usize;
    sorted.get(at.min(top)).copied()
}

#[must_use]
pub fn mean_std(values: &[f32]) -> Option<(f32, f32)> {
    if values.is_empty() {
        return None;
    }
    #[allow(clippy::cast_precision_loss)]
    let n = values.len() as f32;
    let mean = values.iter().sum::<f32>() / n;
    let var = values.iter().map(|v| (v - mean) * (v - mean)).sum::<f32>() / n;
    Some((mean, var.sqrt()))
}
