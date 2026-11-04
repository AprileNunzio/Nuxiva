use crate::platform::error::{CortexError, CortexResult};

pub fn normalize(vector: &[f32]) -> CortexResult<Vec<f32>> {
    if vector.is_empty() {
        return Err(CortexError::EmptyVector);
    }
    if vector.iter().any(|value| !value.is_finite()) {
        return Err(CortexError::NonFiniteVector);
    }
    let norm = vector.iter().map(|value| value * value).sum::<f32>().sqrt();
    if !norm.is_finite() || norm <= f32::EPSILON {
        return Err(CortexError::EmptyVector);
    }
    Ok(vector.iter().map(|value| value / norm).collect())
}

#[must_use]
pub fn dot(left: &[f32], right: &[f32]) -> f32 {
    left.iter().zip(right).map(|(a, b)| a * b).sum()
}

#[must_use]
pub fn best_similarity(query: &[f32], candidates: &[Vec<f32>]) -> Option<f32> {
    candidates
        .iter()
        .map(|candidate| dot(query, candidate))
        .reduce(f32::max)
}

#[cfg(test)]
mod tests {
    use super::{CortexError, best_similarity, dot, normalize};

    #[test]
    fn normalised_vectors_have_unit_length() -> Result<(), CortexError> {
        let unit = normalize(&[3.0, 4.0])?;
        assert!((dot(&unit, &unit) - 1.0).abs() < 1e-6);
        Ok(())
    }

    #[test]
    fn degenerate_vectors_are_rejected() {
        assert_eq!(normalize(&[]), Err(CortexError::EmptyVector));
        assert_eq!(normalize(&[0.0, 0.0]), Err(CortexError::EmptyVector));
        assert_eq!(
            normalize(&[1.0, f32::NAN]),
            Err(CortexError::NonFiniteVector)
        );
        assert_eq!(
            normalize(&[f32::INFINITY, 1.0]),
            Err(CortexError::NonFiniteVector)
        );
    }

    #[test]
    fn best_similarity_picks_the_closest_candidate() -> Result<(), CortexError> {
        let query = normalize(&[1.0, 0.0])?;
        let near = normalize(&[1.0, 0.1])?;
        let far = normalize(&[0.0, 1.0])?;
        let best = best_similarity(&query, &[far, near.clone()]);
        assert_eq!(best, Some(dot(&query, &near)));
        assert_eq!(best_similarity(&query, &[]), None);
        Ok(())
    }
}
