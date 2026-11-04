use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CoordinateTransform {
    pub translation_ego_to_allo: (f64, f64, f64),
    pub rotation_yaw_radians: f64,
}

impl Default for CoordinateTransform {
    fn default() -> Self {
        Self {
            translation_ego_to_allo: (0.0, 0.0, 0.0),
            rotation_yaw_radians: 0.0,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SensoryInputBundle {
    pub id: String,
    pub visual_time: f64,
    pub visual_ego_pos: (f64, f64, f64),
    pub visual_saliency: f64,
    pub audio_time: f64,
    pub audio_loudness: f64,
    pub proprioceptive_effort: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BoundPercept {
    pub percept_id: String,
    pub timestamp_ms: f64,
    pub egocentric_pos: (f64, f64, f64),
    pub allocentric_pos: (f64, f64, f64),
    pub visual_saliency: f64,
    pub acoustic_loudness: f64,
    pub proprioceptive_effort: f64,
    pub coherence_score: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MultimodalSpatiotemporalBinding {
    pub coincidence_window_ms: f64,
    pub spatial_tolerance_meters: f64,
}

impl Default for MultimodalSpatiotemporalBinding {
    fn default() -> Self {
        Self {
            coincidence_window_ms: 50.0,
            spatial_tolerance_meters: 0.25,
        }
    }
}

impl MultimodalSpatiotemporalBinding {
    #[must_use]
    pub fn ego_to_allo(
        &self,
        ego: (f64, f64, f64),
        transform: &CoordinateTransform,
    ) -> (f64, f64, f64) {
        let cos_theta = transform.rotation_yaw_radians.cos();
        let sin_theta = transform.rotation_yaw_radians.sin();
        let rotated_x = cos_theta * ego.0 - sin_theta * ego.1;
        let rotated_y = sin_theta * ego.0 + cos_theta * ego.1;
        (
            rotated_x + transform.translation_ego_to_allo.0,
            rotated_y + transform.translation_ego_to_allo.1,
            ego.2 + transform.translation_ego_to_allo.2,
        )
    }

    #[must_use]
    pub fn bind(
        &self,
        bundle: &SensoryInputBundle,
        transform: &CoordinateTransform,
    ) -> Option<BoundPercept> {
        let time_delta = (bundle.visual_time - bundle.audio_time).abs();
        if time_delta > self.coincidence_window_ms {
            return None;
        }

        let allocentric = self.ego_to_allo(bundle.visual_ego_pos, transform);
        let time_coherence = 1.0 - (time_delta / self.coincidence_window_ms).clamp(0.0, 1.0);
        let crossmodal_intensity =
            (bundle.visual_saliency * 0.5 + bundle.audio_loudness * 0.5).clamp(0.0, 1.0);
        let coherence = (time_coherence * 0.7 + crossmodal_intensity * 0.3).clamp(0.0, 1.0);

        Some(BoundPercept {
            percept_id: bundle.id.clone(),
            timestamp_ms: bundle.visual_time,
            egocentric_pos: bundle.visual_ego_pos,
            allocentric_pos: allocentric,
            visual_saliency: bundle.visual_saliency,
            acoustic_loudness: bundle.audio_loudness,
            proprioceptive_effort: bundle.proprioceptive_effort,
            coherence_score: coherence,
        })
    }
}
