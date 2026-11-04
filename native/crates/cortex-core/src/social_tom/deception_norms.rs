use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SocialCommunication {
    pub speaker_id: String,
    pub stated_fact_key: String,
    pub stated_fact_value: String,
    pub claimed_intention: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PragmaticAssessment {
    pub is_deception_detected: bool,
    pub truth_value_divergence: f64,
    pub cooperative_reputation_delta: f64,
    pub recommended_response_posture: String,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SocialNormEngine {
    tolerance_threshold: f64,
}

impl SocialNormEngine {
    #[must_use]
    pub fn new(tolerance_threshold: f64) -> Self {
        Self {
            tolerance_threshold,
        }
    }

    #[must_use]
    pub fn assess_communication(
        &self,
        comm: &SocialCommunication,
        ground_truth_value: Option<&str>,
        speaker_believed_value: Option<&str>,
    ) -> PragmaticAssessment {
        let matches_truth = ground_truth_value.is_none_or(|v| v == comm.stated_fact_value);
        let matches_speaker_belief =
            speaker_believed_value.is_none_or(|v| v == comm.stated_fact_value);

        let is_deliberate_lie = !matches_truth && !matches_speaker_belief;
        let is_honest_mistake = !matches_truth && matches_speaker_belief;

        if is_deliberate_lie {
            PragmaticAssessment {
                is_deception_detected: true,
                truth_value_divergence: 1.0,
                cooperative_reputation_delta: -0.35,
                recommended_response_posture: "defensive_verification".to_string(),
            }
        } else if is_honest_mistake {
            PragmaticAssessment {
                is_deception_detected: false,
                truth_value_divergence: 0.5,
                cooperative_reputation_delta: -0.05,
                recommended_response_posture: "gentle_clarification".to_string(),
            }
        } else {
            PragmaticAssessment {
                is_deception_detected: false,
                truth_value_divergence: 0.0,
                cooperative_reputation_delta: 0.05,
                recommended_response_posture: "cooperative_alignment".to_string(),
            }
        }
    }
}
