from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class PieceColor(str, Enum):
    WHITE = "white"
    BLACK = "black"

class PersonalityTone(str, Enum):
    GRANDMASTER_SARCASTIC = "sarcastic"
    FRIENDLY_COACH = "friendly"
    RIGOROUS_ACADEMIC = "academic"
    CASUAL = "casual"

class AdviceDepth(str, Enum):
    HINT_PIECE = "piece_only"
    HINT_TARGET_SQUARE = "target_square"
    FULL_EXPLANATION = "full_variation"

class CandidateLine(BaseModel):
    move_uci: str
    move_san: str
    score_centipawns: int
    strategic_intent: str

class DeliberationContext(BaseModel):
    chosen_move: CandidateLine
    alternative_moves: List[CandidateLine] = Field(default_factory=list)
    evaluation_gap: int = 0
    is_dilemma: bool = False
    is_blunder_punishment: bool = False
    user_skill_level: int = Field(default=1500, ge=800, le=3000)

class AgentDialogueOutput(BaseModel):
    spoken_move: str
    inner_thought: str
    banter_comment: Optional[str] = None
    advice_payload: Optional[str] = None
    emotional_state: str = "neutral"

class ChessGameState(BaseModel):
    fen: str
    move_history: List[str] = Field(default_factory=list)
    turn: PieceColor = PieceColor.WHITE
    is_check: bool = False
    is_game_over: bool = False
    is_paused: bool = False
    white_time_remaining_ms: int = 600000
    black_time_remaining_ms: int = 600000

class MoveCalculationRequest(BaseModel):
    fen: str
    elo: int = Field(default=1500, ge=800, le=3000)
    time_limit_ms: int = Field(default=1000, ge=100, le=10000)
    coach_mode: bool = False
    preferred_tone: PersonalityTone = PersonalityTone.FRIENDLY_COACH

class MoveCalculationResponse(BaseModel):
    best_move_uci: str
    best_move_san: str
    evaluation_score: float
    depth_reached: int
    pv_line: List[str] = Field(default_factory=list)
    dialogue: AgentDialogueOutput

class VoiceMoveRequest(BaseModel):
    transcript: str
    fen: str
    locale: str = "it"

class VoiceMoveResponse(BaseModel):
    success: bool
    san_move: Optional[str] = None
    uci_move: Optional[str] = None
    feedback_speech: str

class SessionVaultPayload(BaseModel):
    session_id: str
    user_id: str
    encrypted_state: str
    nonce: str
    tag: str
    timestamp: float
