use tract_onnx::prelude::*;

use crate::error::{BrainError, BrainResult};
use crate::fbank::{Fbank, MELS};
use crate::model::ModelSpec;
use crate::sensory::Embedder;

pub const EMBEDDING_DIM: usize = 256;

type Plan = std::sync::Arc<TypedRunnableModel>;

pub struct OnnxEmbedder {
    plan: Plan,
    fbank: Fbank,
}

impl std::fmt::Debug for OnnxEmbedder {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("OnnxEmbedder(..)")
    }
}

fn fail<E>(_: E) -> BrainError {
    BrainError::Embedding("onnx")
}

impl OnnxEmbedder {
    pub fn from_verified(spec: &ModelSpec, data: &[u8]) -> BrainResult<Self> {
        spec.verify(data)?;
        let mut reader = data;
        let plan = tract_onnx::onnx()
            .model_for_read(&mut reader)
            .map_err(fail)?
            .into_optimized()
            .map_err(fail)?
            .into_runnable()
            .map_err(fail)?;
        Ok(Self {
            plan,
            fbank: Fbank::new(),
        })
    }
}

impl Embedder for OnnxEmbedder {
    fn embed(&self, pcm: &[f32]) -> BrainResult<Vec<f32>> {
        let feats = self.fbank.compute(pcm)?;
        let frames = feats.len() / MELS;
        let tensor = tract_ndarray::Array3::from_shape_vec((1, frames, MELS), feats)
            .map_err(fail)?
            .into_tensor();
        let outputs = self.plan.run(tvec!(tensor.into())).map_err(fail)?;
        let first = outputs.first().ok_or(BrainError::Embedding("onnx"))?;
        let view = first.to_plain_array_view::<f32>().map_err(fail)?;
        let vector: Vec<f32> = view.iter().copied().collect();
        if vector.len() != EMBEDDING_DIM || vector.iter().any(|v| !v.is_finite()) {
            return Err(BrainError::Embedding("onnx_output"));
        }
        Ok(vector)
    }
}
