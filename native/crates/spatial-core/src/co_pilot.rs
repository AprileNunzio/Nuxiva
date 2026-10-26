use crate::morphology::AssistantMorphology;
use crate::z_stack::ZLayer;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum CoPilotActionKind {
    SpeakInsight,
    SuggestMove,
    SilentObserve,
    PreemptAlert,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CoPilotAction {
    pub action_kind: CoPilotActionKind,
    pub insight_key: String,
    pub suggested_move: Option<String>,
    pub confidence: f32,
    pub target_morphology: AssistantMorphology,
    pub target_layer: ZLayer,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LiveCoPilotEngine {
    pub session_id: String,
    pub game_id: String,
    pub is_active: bool,
    pub turn_count: u32,
    pub history_moves: Vec<String>,
    pub last_board_state: String,
}

impl Default for LiveCoPilotEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl LiveCoPilotEngine {
    #[must_use]
    pub fn new() -> Self {
        Self {
            session_id: String::new(),
            game_id: String::new(),
            is_active: false,
            turn_count: 0,
            history_moves: Vec::new(),
            last_board_state: String::new(),
        }
    }

    pub fn start_session(
        &mut self,
        game_id: impl Into<String>,
        initial_state: impl Into<String>,
    ) -> CoPilotAction {
        self.game_id = game_id.into();
        self.session_id = "session_live_copilot".to_string();
        self.is_active = true;
        self.turn_count = 0;
        self.history_moves.clear();
        self.last_board_state = initial_state.into();

        CoPilotAction {
            action_kind: CoPilotActionKind::SpeakInsight,
            insight_key: "copilot.game_started".to_string(),
            suggested_move: None,
            confidence: 1.0,
            target_morphology: AssistantMorphology::FloatingOrb,
            target_layer: ZLayer::Z2ContextualHud,
        }
    }

    pub fn on_move_applied(
        &mut self,
        move_key: impl Into<String>,
        board_state: impl Into<String>,
    ) -> CoPilotAction {
        if !self.is_active {
            return CoPilotAction {
                action_kind: CoPilotActionKind::SilentObserve,
                insight_key: "copilot.inactive".to_string(),
                suggested_move: None,
                confidence: 0.0,
                target_morphology: AssistantMorphology::AmbientStream,
                target_layer: ZLayer::Z0Ambient,
            };
        }

        let m_str = move_key.into();
        self.history_moves.push(m_str.clone());
        self.last_board_state = board_state.into();
        self.turn_count = self.turn_count.saturating_add(1);

        if self.turn_count <= 2 {
            CoPilotAction {
                action_kind: CoPilotActionKind::SpeakInsight,
                insight_key: "copilot.opening_acknowledged".to_string(),
                suggested_move: Some(m_str),
                confidence: 0.95,
                target_morphology: AssistantMorphology::FloatingOrb,
                target_layer: ZLayer::Z2ContextualHud,
            }
        } else if self.turn_count % 3 == 0 {
            CoPilotAction {
                action_kind: CoPilotActionKind::SuggestMove,
                insight_key: "copilot.tactical_suggestion".to_string(),
                suggested_move: Some("e2e4".to_string()),
                confidence: 0.88,
                target_morphology: AssistantMorphology::FloatingOrb,
                target_layer: ZLayer::Z2ContextualHud,
            }
        } else {
            CoPilotAction {
                action_kind: CoPilotActionKind::SilentObserve,
                insight_key: "copilot.turn_observed".to_string(),
                suggested_move: None,
                confidence: 0.9,
                target_morphology: AssistantMorphology::AmbientStream,
                target_layer: ZLayer::Z2ContextualHud,
            }
        }
    }

    pub fn end_session(&mut self) -> CoPilotAction {
        self.is_active = false;
        CoPilotAction {
            action_kind: CoPilotActionKind::SpeakInsight,
            insight_key: "copilot.game_ended".to_string(),
            suggested_move: None,
            confidence: 1.0,
            target_morphology: AssistantMorphology::CoreHero,
            target_layer: ZLayer::Z3Assistant,
        }
    }

    #[must_use]
    pub const fn is_live(&self) -> bool {
        self.is_active
    }
}
