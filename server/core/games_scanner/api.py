from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Path, Query
from server.core.games_scanner.contracts import (
    GameManifest,
    GameCommand,
    GameCapability,
    CommandExecutionRequest,
    CommandExecutionResult,
)
from server.core.games_scanner.scanner import games_scanner

class ToggleStatusRequest(BaseModel):
    enabled: Optional[bool] = None

class ToggleStatusResponse(BaseModel):
    game_id: str
    is_active: bool

router = APIRouter(prefix="/api/v2/games", tags=["Games"])

@router.get("", response_model=List[GameManifest])
async def list_all_games(include_disabled: bool = Query(True)) -> List[GameManifest]:
    return games_scanner.list_games(include_disabled=include_disabled)

@router.post("/rescan", response_model=List[GameManifest])
async def trigger_rescan() -> List[GameManifest]:
    games_scanner.scan_all(force=True)
    return games_scanner.list_games(include_disabled=True)

@router.get("/{game_id}", response_model=GameManifest)
async def get_game_details(game_id: str = Path(..., pattern="^[a-zA-Z0-9_\\-]+$")) -> GameManifest:
    game = games_scanner.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game '{game_id}' not found")
    return game

@router.post("/{game_id}/status", response_model=ToggleStatusResponse)
async def toggle_game_status(
    payload: ToggleStatusRequest,
    game_id: str = Path(..., pattern="^[a-zA-Z0-9_\\-]+$"),
) -> ToggleStatusResponse:
    try:
        new_state = games_scanner.toggle_game_status(game_id, payload.enabled)
        return ToggleStatusResponse(game_id=game_id, is_active=new_state)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Game '{game_id}' not found")

@router.get("/{game_id}/commands", response_model=List[GameCommand])
async def get_game_commands(game_id: str = Path(..., pattern="^[a-zA-Z0-9_\\-]+$")) -> List[GameCommand]:
    game = games_scanner.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game '{game_id}' not found")
    return game.commands

@router.get("/{game_id}/capabilities", response_model=List[GameCapability])
async def get_game_capabilities(game_id: str = Path(..., pattern="^[a-zA-Z0-9_\\-]+$")) -> List[GameCapability]:
    game = games_scanner.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game '{game_id}' not found")
    return game.capabilities

@router.post("/{game_id}/execute", response_model=CommandExecutionResult)
async def execute_game_command(
    request: CommandExecutionRequest,
    game_id: str = Path(..., pattern="^[a-zA-Z0-9_\\-]+$"),
) -> CommandExecutionResult:
    game = games_scanner.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game '{game_id}' not found")
    if not game.is_active:
        raise HTTPException(status_code=403, detail=f"Game '{game_id}' is disabled")

    matching_cmd = next((c for c in game.commands if c.command_id == request.command_id), None)
    if not matching_cmd:
        raise HTTPException(status_code=400, detail=f"Command '{request.command_id}' not supported by '{game_id}'")

    return CommandExecutionResult(
        success=True,
        command_id=request.command_id,
        result_data={"status": "dispatched", "game_id": game_id, "params": request.parameters},
        feedback_speech_key=f"{request.command_id}_executed",
    )
