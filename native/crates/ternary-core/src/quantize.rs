use crate::error::TernaryError;
use crate::vector::TernaryVector;

#[allow(clippy::cast_precision_loss)]
pub fn quantize_dense(dense: &[f32], threshold_factor: f32) -> Result<TernaryVector, TernaryError> {
    if dense.is_empty() {
        return Err(TernaryError::EmptyVector);
    }
    if !threshold_factor.is_finite() || threshold_factor <= 0.0 {
        return Err(TernaryError::InvalidThreshold {
            factor: threshold_factor.to_string(),
        });
    }

    let mut sum_abs: f32 = 0.0;
    for &val in dense {
        sum_abs += val.abs();
    }
    let mean_abs = sum_abs / (dense.len() as f32);
    let tau = mean_abs * threshold_factor;

    let mut trits: Vec<i8> = Vec::with_capacity(dense.len());
    for &val in dense {
        if val > tau {
            trits.push(1);
        } else if val < -tau {
            trits.push(-1);
        } else {
            trits.push(0);
        }
    }

    TernaryVector::from_trits(&trits)
}
