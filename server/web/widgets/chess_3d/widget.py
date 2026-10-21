from typing import Dict, Any
from server.core.scanner.base import DiscoveryManifest
from server.web.widgets.base import BaseWidget

class ChessDeckWidget(BaseWidget):
    def __init__(self, manifest_data: Dict[str, Any] = None) -> None:
        super().__init__(manifest_data)
        self._is_paused = False
        self._current_turn = "white"
        self._fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        self._move_count = 0

    @property
    def manifest(self) -> DiscoveryManifest:
        return DiscoveryManifest(
            id=self._manifest_data.get("id", "chess_3d"),
            name=self._manifest_data.get("name", "Scacchi 3D Deck"),
            category="widget",
            description=self._manifest_data.get("description", "3D Chess Deck Widget"),
            icon=self._manifest_data.get("icon", "♟️"),
            metadata={
                "render_type": self._manifest_data.get("render_type", "chess_deck"),
                "grid_span": self._manifest_data.get("grid_span", {"col": 2, "row": 2}),
                "target_game": "scacchi-3d",
            },
        )

    async def get_state(self, user_id: str = "") -> Dict[str, Any]:
        return {
            "game_id": "scacchi-3d",
            "fen": self._fen,
            "turn": self._current_turn,
            "is_paused": self._is_paused,
            "move_count": self._move_count,
            "voice_active": True,
        }

    async def execute_action(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if action == "pause":
            self._is_paused = True
            return {"status": "success", "is_paused": True}
        if action == "resume":
            self._is_paused = False
            return {"status": "success", "is_paused": False}
        if action == "reset":
            self._fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            self._is_paused = False
            self._move_count = 0
            self._current_turn = "white"
            return {"status": "success", "reset": True}
        if action == "move":
            self._move_count += 1
            self._current_turn = "black" if self._current_turn == "white" else "white"
            return {"status": "success", "move_count": self._move_count, "turn": self._current_turn}
        return {"status": "unsupported", "action": action}
