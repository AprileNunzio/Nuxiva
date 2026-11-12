#![allow(clippy::cast_precision_loss, clippy::arithmetic_side_effects)]

pub const MAX_VOICES: usize = 2000;
pub const MAX_DIM: usize = 1024;

fn norm(v: &[f32]) -> f32 {
    v.iter().map(|x| x * x).sum::<f32>().sqrt()
}

fn cosine(a: &[f32], b: &[f32]) -> f32 {
    let denom = norm(a) * norm(b);
    if denom <= f32::EPSILON || a.len() != b.len() {
        return -1.0;
    }
    a.iter().zip(b).map(|(x, y)| x * y).sum::<f32>() / denom
}

#[must_use]
pub fn cluster_voices(embeddings: &[Vec<f32>], threshold: f32) -> Option<Vec<usize>> {
    if embeddings.len() > MAX_VOICES
        || embeddings
            .iter()
            .any(|e| e.len() > MAX_DIM || e.iter().any(|x| !x.is_finite()))
    {
        return None;
    }
    let mut centroids: Vec<(Vec<f32>, f32)> = Vec::new();
    let mut labels = Vec::with_capacity(embeddings.len());
    for e in embeddings {
        let mut best: Option<(usize, f32)> = None;
        for (i, (c, _)) in centroids.iter().enumerate() {
            let s = cosine(e, c);
            if s >= threshold && best.is_none_or(|(_, b)| s > b) {
                best = Some((i, s));
            }
        }
        if let Some((i, (c, n))) =
            best.and_then(|(i, _)| centroids.get_mut(i).map(|slot| (i, slot)))
        {
            let count = *n;
            for (ci, ei) in c.iter_mut().zip(e) {
                *ci = (*ci * count + ei) / (count + 1.0);
            }
            *n = count + 1.0;
            labels.push(i);
        } else {
            labels.push(centroids.len());
            centroids.push((e.clone(), 1.0));
        }
    }
    Some(labels)
}
