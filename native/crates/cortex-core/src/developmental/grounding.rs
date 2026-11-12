use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GroundedSymbol {
    pub symbol_id: String,
    pub cluster_centroid: Vec<f64>,
    pub variance: f64,
    pub observed_instances: u64,
    pub sensory_provenance_keys: Vec<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SymbolGroundingEngine {
    symbols: BTreeMap<String, GroundedSymbol>,
    distance_threshold: f64,
}

impl SymbolGroundingEngine {
    #[must_use]
    pub fn new(distance_threshold: f64) -> Self {
        Self {
            symbols: BTreeMap::new(),
            distance_threshold,
        }
    }

    fn euclidean_distance(a: &[f64], b: &[f64]) -> f64 {
        let mut sum = 0.0;
        for (x, y) in a.iter().zip(b.iter()) {
            let diff = x - y;
            sum += diff * diff;
        }
        sum.sqrt()
    }

    pub fn ground_observation(&mut self, features: &[f64], provenance_tag: &str) -> String {
        let mut closest_match: Option<(String, f64)> = None;
        for (id, sym) in &self.symbols {
            let d = Self::euclidean_distance(&sym.cluster_centroid, features);
            if d < self.distance_threshold {
                match &closest_match {
                    Some((_, min_d)) if d < *min_d => {
                        closest_match = Some((id.clone(), d));
                    }
                    None => {
                        closest_match = Some((id.clone(), d));
                    }
                    _ => {}
                }
            }
        }

        if let Some((best_id, _)) = closest_match {
            if let Some(sym) = self.symbols.get_mut(&best_id) {
                sym.observed_instances = sym.observed_instances.saturating_add(1);
                let n = sym.observed_instances as f64;
                for (centroid_val, &feat_val) in
                    sym.cluster_centroid.iter_mut().zip(features.iter())
                {
                    *centroid_val += (feat_val - *centroid_val) / n;
                }
                if !sym
                    .sensory_provenance_keys
                    .iter()
                    .any(|k| k == provenance_tag)
                {
                    sym.sensory_provenance_keys.push(provenance_tag.to_string());
                }
            }
            best_id
        } else {
            let new_id = format!("sym_{}", self.symbols.len().saturating_add(1));
            self.symbols.insert(
                new_id.clone(),
                GroundedSymbol {
                    symbol_id: new_id.clone(),
                    cluster_centroid: features.to_vec(),
                    variance: 0.1,
                    observed_instances: 1,
                    sensory_provenance_keys: vec![provenance_tag.to_string()],
                },
            );
            new_id
        }
    }

    #[must_use]
    pub fn get_symbol(&self, symbol_id: &str) -> Option<&GroundedSymbol> {
        self.symbols.get(symbol_id)
    }

    #[must_use]
    pub fn symbol_count(&self) -> usize {
        self.symbols.len()
    }
}
