import json
from typing import Any, Dict, Optional


class CoPilotAction:
    def __init__(
        self,
        action_kind: str,
        insight_key: str,
        suggested_move: Optional[str] = None,
        confidence: float = 1.0,
        target_morphology: str = "FloatingOrb",
        target_layer: str = "Z2ContextualHud",
    ) -> None:
        self.action_kind = str(action_kind)
        self.insight_key = insight_key
        self.suggested_move = suggested_move
        self.confidence = float(confidence)
        self.target_morphology = target_morphology
        self.target_layer = target_layer

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_kind": self.action_kind,
            "insight_key": self.insight_key,
            "suggested_move": self.suggested_move,
            "confidence": self.confidence,
            "target_morphology": self.target_morphology,
            "target_layer": self.target_layer,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CoPilotAction":
        return cls(
            action_kind=str(data.get("action_kind", "SILENT_OBSERVE")),
            insight_key=str(data.get("insight_key", "copilot.turn_observed")),
            suggested_move=data.get("suggested_move"),
            confidence=float(data.get("confidence", 0.0)),
            target_morphology=str(data.get("target_morphology", "AmbientStream")),
            target_layer=str(data.get("target_layer", "Z2ContextualHud")),
        )


class LiveCoPilotBridge:
    def __init__(self) -> None:
        self._native = None
        self._is_active = False
        self._game_id = ""
        self._turn_count = 0
        self._history: list[str] = []
        self._board_state = ""

        try:
            import nuxiva_native
            if hasattr(nuxiva_native, "RustLiveCoPilot"):
                self._native = nuxiva_native.RustLiveCoPilot()
        except ImportError:
            self._native = None

    def start_session(self, game_id: str, initial_state: str) -> CoPilotAction:
        if self._native is not None:
            raw = self._native.start_session_json(game_id, initial_state)
            return CoPilotAction.from_dict(json.loads(raw))

        self._game_id = game_id
        self._is_active = True
        self._turn_count = 0
        self._history.clear()
        self._board_state = initial_state

        return CoPilotAction(
            action_kind="SPEAK_INSIGHT",
            insight_key="copilot.game_started",
            suggested_move=None,
            confidence=1.0,
            target_morphology="FloatingOrb",
            target_layer="Z2ContextualHud",
        )

    def on_move_applied(self, move_key: str, board_state: str) -> CoPilotAction:
        if self._native is not None:
            raw = self._native.on_move_applied_json(move_key, board_state)
            return CoPilotAction.from_dict(json.loads(raw))

        if not self._is_active:
            return CoPilotAction(
                action_kind="SILENT_OBSERVE",
                insight_key="copilot.inactive",
                suggested_move=None,
                confidence=0.0,
                target_morphology="AmbientStream",
                target_layer="Z0Ambient",
            )

        self._history.append(move_key)
        self._board_state = board_state
        self._turn_count += 1

        if self._turn_count <= 2:
            return CoPilotAction(
                action_kind="SPEAK_INSIGHT",
                insight_key="copilot.opening_acknowledged",
                suggested_move=move_key,
                confidence=0.95,
                target_morphology="FloatingOrb",
                target_layer="Z2ContextualHud",
            )

        if self._turn_count % 3 == 0:
            return CoPilotAction(
                action_kind="SUGGEST_MOVE",
                insight_key="copilot.tactical_suggestion",
                suggested_move="e2e4",
                confidence=0.88,
                target_morphology="FloatingOrb",
                target_layer="Z2ContextualHud",
            )

        return CoPilotAction(
            action_kind="SILENT_OBSERVE",
            insight_key="copilot.turn_observed",
            suggested_move=None,
            confidence=0.9,
            target_morphology="AmbientStream",
            target_layer="Z2ContextualHud",
        )

    def end_session(self) -> CoPilotAction:
        if self._native is not None:
            raw = self._native.end_session_json()
            return CoPilotAction.from_dict(json.loads(raw))

        self._is_active = False
        return CoPilotAction(
            action_kind="SPEAK_INSIGHT",
            insight_key="copilot.game_ended",
            suggested_move=None,
            confidence=1.0,
            target_morphology="CoreHero",
            target_layer="Z3Assistant",
        )

    def is_live(self) -> bool:
        if self._native is not None:
            return bool(self._native.is_live())
        return self._is_active

    def analyze_moves(self, moves: Any, turn: str = "white") -> CoPilotAction:
        if isinstance(moves, list):
            moves_str = " ".join(str(m) for m in moves)
        else:
            moves_str = str(moves or "")

        if self._native is not None and hasattr(self._native, "analyze_tactics_json"):
            try:
                raw = self._native.analyze_tactics_json(moves_str, turn)
                return CoPilotAction.from_dict(json.loads(raw))
            except Exception:
                pass

        moves_list = [m for m in moves_str.replace(",", " ").split() if m]
        count = len(moves_list)
        is_white = turn.lower() == "white"

        if count == 0:
            if is_white:
                return CoPilotAction("SUGGEST_MOVE", "copilot.chess.open_center", "e2e4", 0.98)
            return CoPilotAction("SILENT_OBSERVE", "copilot.chess.waiting_white", None, 0.90)
        if count == 1 and not is_white:
            first = moves_list[0]
            sug = "e7e5" if first == "e2e4" else "d7d5"
            return CoPilotAction("SUGGEST_MOVE", "copilot.chess.reply_center", sug, 0.96)
        if count == 2 and is_white:
            return CoPilotAction("SUGGEST_MOVE", "copilot.chess.develop_knight", "g1f3", 0.96)
        if count == 3 and not is_white:
            return CoPilotAction("SUGGEST_MOVE", "copilot.chess.protect_pawn", "b8c6", 0.95)
        if count == 4 and is_white:
            return CoPilotAction("SUGGEST_MOVE", "copilot.chess.develop_bishop", "f1c4", 0.94)
        if count == 5 and not is_white:
            return CoPilotAction("SUGGEST_MOVE", "copilot.chess.develop_kingside", "g8f6", 0.93)

        has_castle = any(m in ("e1g1", "e1c1", "e8g8", "e8c8") for m in moves_list)
        if not has_castle and 6 <= count <= 14:
            castle_move = "e1g1" if is_white else "e8g8"
            return CoPilotAction("SUGGEST_MOVE", "copilot.chess.castle_king", castle_move, 0.91)

        return CoPilotAction("SUGGEST_MOVE", "copilot.chess.control_center", "d2d4", 0.88)


live_copilot = LiveCoPilotBridge()
