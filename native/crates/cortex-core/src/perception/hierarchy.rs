use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RawSensoryFrame {
    pub timestamp_ms: f64,
    pub visual_stream: Vec<f64>,
    pub audio_frequencies: Vec<f64>,
    pub proprioceptive_joint_angles: Vec<f64>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ObjectSlot {
    pub slot_id: usize,
    pub centroid_3d: (f64, f64, f64),
    pub bounding_volume: (f64, f64, f64),
    pub surface_features: Vec<f64>,
    pub permanence_confidence: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TrackedTrajectory {
    pub object_id: usize,
    pub state_3d: (f64, f64, f64),
    pub velocity_3d: (f64, f64, f64),
    pub variance: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WorldEntityNode {
    pub entity_id: String,
    pub entity_type: String,
    pub coordinates: (f64, f64, f64),
    pub velocity: (f64, f64, f64),
    pub is_autonomous_agent: bool,
    pub inferred_goal: Option<String>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct UnifiedWorldGraph {
    pub timestamp_ms: f64,
    pub entities: BTreeMap<String, WorldEntityNode>,
    pub relations: Vec<(String, String, String)>,
}

#[derive(Debug, Clone)]
pub struct PerceptualHierarchyPipeline {
    slots: Vec<ObjectSlot>,
    kalman_tracks: BTreeMap<usize, TrackedTrajectory>,
}

impl Default for PerceptualHierarchyPipeline {
    fn default() -> Self {
        Self::new(8)
    }
}

impl PerceptualHierarchyPipeline {
    #[must_use]
    pub fn new(slot_count: usize) -> Self {
        let mut slots = Vec::with_capacity(slot_count);
        for id in 0..slot_count {
            slots.push(ObjectSlot {
                slot_id: id,
                centroid_3d: (0.0, 0.0, 0.0),
                bounding_volume: (0.1, 0.1, 0.1),
                surface_features: vec![0.0; 16],
                permanence_confidence: 0.0,
            });
        }
        Self {
            slots,
            kalman_tracks: BTreeMap::new(),
        }
    }

    pub fn process_frame(&mut self, frame: &RawSensoryFrame) -> UnifiedWorldGraph {
        let n_pixels = frame.visual_stream.len();
        let total_slots = self.slots.len();
        if n_pixels > 0 && total_slots > 0 {
            for (idx, slot) in self.slots.iter_mut().enumerate() {
                let start = idx
                    .saturating_mul(n_pixels)
                    .checked_div(total_slots)
                    .unwrap_or(0);
                let end = idx
                    .saturating_add(1)
                    .saturating_mul(n_pixels)
                    .checked_div(total_slots)
                    .unwrap_or(0);
                let chunk = frame.visual_stream.get(start..end).unwrap_or(&[]);
                let mean = if chunk.is_empty() {
                    0.0
                } else {
                    chunk.iter().sum::<f64>() / chunk.len() as f64
                };
                slot.centroid_3d = ((idx as f64) * 0.5, mean, 1.0);
                slot.permanence_confidence = (slot.permanence_confidence * 0.8 + 0.2).min(1.0);
            }
        }

        let mut world_graph = UnifiedWorldGraph {
            timestamp_ms: frame.timestamp_ms,
            entities: BTreeMap::new(),
            relations: Vec::new(),
        };

        for slot in &self.slots {
            if slot.permanence_confidence > 0.1 {
                let track = self
                    .kalman_tracks
                    .entry(slot.slot_id)
                    .or_insert(TrackedTrajectory {
                        object_id: slot.slot_id,
                        state_3d: slot.centroid_3d,
                        velocity_3d: (0.0, 0.0, 0.0),
                        variance: 0.1,
                    });

                let dt = 0.05;
                let new_vx = (slot.centroid_3d.0 - track.state_3d.0) / dt;
                let new_vy = (slot.centroid_3d.1 - track.state_3d.1) / dt;
                let new_vz = (slot.centroid_3d.2 - track.state_3d.2) / dt;
                track.velocity_3d = (new_vx, new_vy, new_vz);
                track.state_3d = slot.centroid_3d;

                let speed = (new_vx * new_vx + new_vy * new_vy + new_vz * new_vz).sqrt();
                let is_agent = speed > 0.1;

                let entity_id = format!("obj_{}", slot.slot_id);
                world_graph.entities.insert(
                    entity_id.clone(),
                    WorldEntityNode {
                        entity_id,
                        entity_type: if is_agent {
                            "agent".to_string()
                        } else {
                            "object".to_string()
                        },
                        coordinates: track.state_3d,
                        velocity: track.velocity_3d,
                        is_autonomous_agent: is_agent,
                        inferred_goal: if is_agent {
                            Some("approach_target".to_string())
                        } else {
                            None
                        },
                    },
                );
            }
        }

        world_graph
    }
}
