use std::cmp::Ordering;

use serde::{Deserialize, Serialize};

use super::arbiter::decide;
use super::similarity::{best_similarity, dot, normalize};
use super::types::{Candidate, Decision, Neuron, Thresholds};
use crate::platform::error::{CortexError, CortexResult};
use crate::platform::sanitizer::sanitize_identifier;

pub const MAX_NEURONS: usize = 100_000;
pub const MAX_VECTORS_PER_NEURON: usize = 256;
pub const MAX_DIMENSION: usize = 4096;
pub const MAX_SNAPSHOT_BYTES: usize = 268_435_456;
const DUPLICATE_SIMILARITY: f32 = 0.9999;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NeuronIndex {
    dimension: usize,
    neurons: Vec<Neuron>,
}

fn valid_weight(weight: f32) -> CortexResult<f32> {
    if weight.is_finite() && (0.0..=1.0).contains(&weight) {
        Ok(weight)
    } else {
        Err(CortexError::InvalidWeight)
    }
}

fn outranks(candidate: &Candidate<'_>, incumbent: &Candidate<'_>) -> bool {
    candidate
        .positive_similarity
        .total_cmp(&incumbent.positive_similarity)
        .then(candidate.neuron.weight.total_cmp(&incumbent.neuron.weight))
        .then_with(|| incumbent.neuron.id.cmp(&candidate.neuron.id))
        == Ordering::Greater
}

impl NeuronIndex {
    pub fn new(dimension: usize) -> CortexResult<Self> {
        if (1..=MAX_DIMENSION).contains(&dimension) {
            Ok(Self {
                dimension,
                neurons: Vec::new(),
            })
        } else {
            Err(CortexError::InvalidDimension)
        }
    }

    #[must_use]
    pub const fn dimension(&self) -> usize {
        self.dimension
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.neurons.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.neurons.is_empty()
    }

    #[must_use]
    pub fn neuron_ids(&self) -> Vec<String> {
        self.neurons.iter().map(|n| n.id.clone()).collect()
    }

    #[must_use]
    pub fn weight(&self, id: &str) -> Option<f32> {
        self.neurons.iter().find(|n| n.id == id).map(|n| n.weight)
    }

    fn prepare(&self, vector: &[f32]) -> CortexResult<Vec<f32>> {
        if vector.len() != self.dimension {
            return Err(CortexError::DimensionMismatch);
        }
        normalize(vector)
    }

    fn prepare_all(&self, vectors: &[Vec<f32>]) -> CortexResult<Vec<Vec<f32>>> {
        if vectors.is_empty() {
            return Err(CortexError::EmptyVector);
        }
        if vectors.len() > MAX_VECTORS_PER_NEURON {
            return Err(CortexError::CapacityExceeded);
        }
        vectors.iter().map(|v| self.prepare(v)).collect()
    }

    fn neuron_mut(&mut self, id: &str) -> CortexResult<&mut Neuron> {
        self.neurons
            .iter_mut()
            .find(|n| n.id == id)
            .ok_or(CortexError::UnknownNeuron)
    }

    pub fn upsert(&mut self, id: &str, weight: f32, dendrites: &[Vec<f32>]) -> CortexResult<()> {
        let id = sanitize_identifier(id)?;
        let weight = valid_weight(weight)?;
        let dendrites = self.prepare_all(dendrites)?;
        if let Some(existing) = self.neurons.iter_mut().find(|n| n.id == id) {
            existing.weight = weight;
            existing.dendrites = dendrites;
            return Ok(());
        }
        if self.neurons.len() >= MAX_NEURONS {
            return Err(CortexError::CapacityExceeded);
        }
        self.neurons.push(Neuron {
            id,
            weight,
            dendrites,
            inhibitions: Vec::new(),
        });
        Ok(())
    }

    pub fn remove(&mut self, id: &str) -> bool {
        let before = self.neurons.len();
        self.neurons.retain(|n| n.id != id);
        self.neurons.len() != before
    }

    pub fn set_weight(&mut self, id: &str, weight: f32) -> CortexResult<()> {
        let weight = valid_weight(weight)?;
        self.neuron_mut(id)?.weight = weight;
        Ok(())
    }

    pub fn add_dendrite(&mut self, id: &str, vector: &[f32]) -> CortexResult<()> {
        let prepared = self.prepare(vector)?;
        let neuron = self.neuron_mut(id)?;
        Self::append(&mut neuron.dendrites, prepared)
    }

    pub fn add_inhibition(&mut self, id: &str, vector: &[f32]) -> CortexResult<()> {
        let prepared = self.prepare(vector)?;
        let neuron = self.neuron_mut(id)?;
        Self::append(&mut neuron.inhibitions, prepared)
    }

    fn append(store: &mut Vec<Vec<f32>>, prepared: Vec<f32>) -> CortexResult<()> {
        if store.len() >= MAX_VECTORS_PER_NEURON {
            return Err(CortexError::CapacityExceeded);
        }
        if best_similarity(&prepared, store).is_some_and(|s| s >= DUPLICATE_SIMILARITY) {
            return Err(CortexError::DuplicateVector);
        }
        store.push(prepared);
        Ok(())
    }

    fn best_candidate<'a>(&'a self, query: &[f32]) -> Option<Candidate<'a>> {
        self.neurons
            .iter()
            .map(|neuron| Candidate {
                neuron,
                positive_similarity: best_similarity(query, &neuron.dendrites)
                    .unwrap_or(f32::NEG_INFINITY),
                negative_similarity: best_similarity(query, &neuron.inhibitions).unwrap_or(0.0),
            })
            .reduce(|best, next| if outranks(&next, &best) { next } else { best })
    }

    pub fn route(&self, query: &[f32], thresholds: &Thresholds) -> CortexResult<Decision> {
        thresholds.validate()?;
        let prepared = self.prepare(query)?;
        Ok(decide(self.best_candidate(&prepared).as_ref(), thresholds))
    }

    pub fn similarity_to(&self, id: &str, query: &[f32]) -> CortexResult<f32> {
        let prepared = self.prepare(query)?;
        let neuron = self
            .neurons
            .iter()
            .find(|n| n.id == id)
            .ok_or(CortexError::UnknownNeuron)?;
        Ok(neuron
            .dendrites
            .iter()
            .map(|d| dot(&prepared, d))
            .fold(f32::NEG_INFINITY, f32::max))
    }

    pub fn snapshot_json(&self) -> CortexResult<String> {
        serde_json::to_string(self).map_err(|_| CortexError::SnapshotInvalid)
    }

    pub fn from_snapshot_json(snapshot: &str) -> CortexResult<Self> {
        if snapshot.len() > MAX_SNAPSHOT_BYTES {
            return Err(CortexError::CapacityExceeded);
        }
        let raw: Self = serde_json::from_str(snapshot).map_err(|_| CortexError::SnapshotInvalid)?;
        let mut restored = Self::new(raw.dimension)?;
        if raw.neurons.len() > MAX_NEURONS {
            return Err(CortexError::CapacityExceeded);
        }
        for neuron in &raw.neurons {
            if restored.neurons.iter().any(|n| n.id == neuron.id) {
                return Err(CortexError::SnapshotInvalid);
            }
            if neuron.inhibitions.len() > MAX_VECTORS_PER_NEURON {
                return Err(CortexError::CapacityExceeded);
            }
            restored.upsert(&neuron.id, neuron.weight, &neuron.dendrites)?;
            for inhibition in &neuron.inhibitions {
                let prepared = restored.prepare(inhibition)?;
                restored.neuron_mut(&neuron.id)?.inhibitions.push(prepared);
            }
        }
        Ok(restored)
    }
}

#[cfg(test)]
mod tests {
    use super::{CortexError, MAX_VECTORS_PER_NEURON, NeuronIndex};
    use crate::hippocampus::types::{SlowReason, Thresholds, Verdict};

    fn index() -> Result<NeuronIndex, CortexError> {
        let mut index = NeuronIndex::new(3)?;
        index.upsert(
            "light.on",
            0.80,
            &[vec![1.0, 0.0, 0.0], vec![0.9, 0.1, 0.0]],
        )?;
        index.upsert("music.play", 0.80, &[vec![0.0, 1.0, 0.0]])?;
        Ok(index)
    }

    #[test]
    fn routes_to_the_closest_neuron() -> Result<(), CortexError> {
        let decision = index()?.route(&[0.95, 0.05, 0.0], &Thresholds::default())?;
        assert_eq!(decision.verdict, Verdict::FastPath);
        assert_eq!(decision.neuron_id.as_deref(), Some("light.on"));
        Ok(())
    }

    #[test]
    fn unrelated_queries_fall_to_the_slow_path() -> Result<(), CortexError> {
        let decision = index()?.route(&[0.0, 0.0, 1.0], &Thresholds::default())?;
        assert_eq!(decision.verdict, Verdict::SlowPath);
        assert_eq!(decision.reason, Some(SlowReason::LowSimilarity));
        Ok(())
    }

    #[test]
    fn inhibition_vectors_block_a_false_positive() -> Result<(), CortexError> {
        let mut index = index()?;
        index.add_inhibition("light.on", &[1.0, 0.0, 0.0])?;
        let decision = index.route(&[1.0, 0.0, 0.0], &Thresholds::default())?;
        assert_eq!(decision.verdict, Verdict::SlowPath);
        assert_eq!(decision.reason, Some(SlowReason::Inhibited));
        Ok(())
    }

    #[test]
    fn empty_index_has_no_neurons_to_offer() -> Result<(), CortexError> {
        let decision = NeuronIndex::new(3)?.route(&[1.0, 0.0, 0.0], &Thresholds::default())?;
        assert_eq!(decision.reason, Some(SlowReason::NoNeurons));
        Ok(())
    }

    #[test]
    fn lowering_the_weight_demotes_the_decision() -> Result<(), CortexError> {
        let mut index = index()?;
        index.set_weight("light.on", 0.40)?;
        let decision = index.route(&[1.0, 0.0, 0.0], &Thresholds::default())?;
        assert_eq!(decision.reason, Some(SlowReason::LowWeight));
        Ok(())
    }

    #[test]
    fn rejects_malformed_input() -> Result<(), CortexError> {
        let mut index = index()?;
        assert_eq!(
            index.route(&[1.0, 0.0], &Thresholds::default()),
            Err(CortexError::DimensionMismatch)
        );
        assert_eq!(
            index.upsert("Bad Id", 0.5, &[vec![1.0, 0.0, 0.0]]),
            Err(CortexError::InvalidIdentifier)
        );
        assert_eq!(
            index.upsert("x", 1.5, &[vec![1.0, 0.0, 0.0]]),
            Err(CortexError::InvalidWeight)
        );
        assert_eq!(
            index.add_dendrite("ghost", &[1.0, 0.0, 0.0]),
            Err(CortexError::UnknownNeuron)
        );
        assert_eq!(
            index.add_dendrite("light.on", &[1.0, 0.0, 0.0]),
            Err(CortexError::DuplicateVector)
        );
        assert_eq!(
            NeuronIndex::new(0).map(|_| ()),
            Err(CortexError::InvalidDimension)
        );
        Ok(())
    }

    #[test]
    fn dendrite_capacity_is_bounded() -> Result<(), CortexError> {
        let mut index = NeuronIndex::new(2)?;
        index.upsert("n", 0.8, &[vec![1.0, 0.0]])?;
        let mut accepted = 1;
        for step in 1..=(MAX_VECTORS_PER_NEURON * 2) {
            let angle = f32::from(u16::try_from(step).unwrap_or(u16::MAX)) * 0.01;
            if index.add_dendrite("n", &[angle.cos(), angle.sin()]).is_ok() {
                accepted += 1;
            }
        }
        assert_eq!(accepted, MAX_VECTORS_PER_NEURON);
        assert_eq!(
            index.add_dendrite("n", &[0.3, 0.7]),
            Err(CortexError::CapacityExceeded)
        );
        Ok(())
    }

    #[test]
    fn remove_and_ids_reflect_membership() -> Result<(), CortexError> {
        let mut index = index()?;
        assert_eq!(index.len(), 2);
        assert!(index.remove("music.play"));
        assert!(!index.remove("music.play"));
        assert_eq!(index.neuron_ids(), vec!["light.on".to_owned()]);
        assert_eq!(index.weight("light.on"), Some(0.80));
        assert!(!index.is_empty());
        Ok(())
    }

    #[test]
    fn snapshot_round_trip_preserves_routing() -> Result<(), CortexError> {
        let mut original = index()?;
        original.add_inhibition("music.play", &[0.0, 0.0, 1.0])?;
        let restored = NeuronIndex::from_snapshot_json(&original.snapshot_json()?)?;
        assert_eq!(restored, original);
        assert_eq!(
            restored.route(&[0.0, 1.0, 0.0], &Thresholds::default())?,
            original.route(&[0.0, 1.0, 0.0], &Thresholds::default())?
        );
        assert_eq!(restored.dimension(), 3);
        Ok(())
    }

    #[test]
    fn corrupted_snapshots_are_refused() {
        assert_eq!(
            NeuronIndex::from_snapshot_json("{not json"),
            Err(CortexError::SnapshotInvalid)
        );
        let duplicated = r#"{"dimension":2,"neurons":[
            {"id":"a","weight":0.5,"dendrites":[[1.0,0.0]],"inhibitions":[]},
            {"id":"a","weight":0.5,"dendrites":[[1.0,0.0]],"inhibitions":[]}]}"#;
        assert_eq!(
            NeuronIndex::from_snapshot_json(duplicated),
            Err(CortexError::SnapshotInvalid)
        );
        let wrong_dimension = r#"{"dimension":2,"neurons":[
            {"id":"a","weight":0.5,"dendrites":[[1.0,0.0,0.0]],"inhibitions":[]}]}"#;
        assert_eq!(
            NeuronIndex::from_snapshot_json(wrong_dimension),
            Err(CortexError::DimensionMismatch)
        );
    }

    #[test]
    fn similarity_to_reports_the_match_for_one_neuron() -> Result<(), CortexError> {
        let index = index()?;
        let score = index.similarity_to("music.play", &[0.0, 2.0, 0.0])?;
        assert!((score - 1.0).abs() < 1e-6);
        assert_eq!(
            index.similarity_to("ghost", &[0.0, 1.0, 0.0]),
            Err(CortexError::UnknownNeuron)
        );
        Ok(())
    }
}
