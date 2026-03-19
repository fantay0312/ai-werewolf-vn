from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from app.core.game_manager import game_manager
from app.models.api_models import CreateGameResponse, GameStateView
from app.security import (
    PLAYER_TOKEN_HEADER,
    build_game_create_response,
    build_game_state_view,
    require_admin_access,
)

router = APIRouter()


def _require_game(session_id: str):
    game = game_manager.get_game(session_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


def _serialize_payload(payload: Any) -> dict[str, Any]:
    if is_dataclass(payload):
        return asdict(payload)
    if isinstance(payload, BaseModel):
        return payload.model_dump()
    if isinstance(payload, dict):
        return payload
    raise HTTPException(status_code=500, detail="Unsupported replay/eval payload")

@router.post("/create", response_model=CreateGameResponse)
async def create_game():
    game = game_manager.create_game()
    human_player = next(player for player in game.players if player.is_human)
    player_token = game_manager.get_player_token(game.session_id)
    return build_game_create_response(game, human_player.id, player_token)

@router.get("/{session_id}", response_model=GameStateView)
async def get_game_state(
    session_id: str,
    x_player_token: str | None = Header(default=None, alias=PLAYER_TOKEN_HEADER),
):
    game = _require_game(session_id)
    viewer_id = game_manager.authenticate_player(session_id, x_player_token)
    if x_player_token is not None and viewer_id is None:
        raise HTTPException(status_code=403, detail="玩家认证失败")
    return build_game_state_view(game, viewer_id)


@router.get("/{session_id}/replay", dependencies=[Depends(require_admin_access)])
async def get_game_replay(session_id: str):
    _require_game(session_id)
    return _serialize_payload(game_manager.get_replay_timeline(session_id))


@router.get("/{session_id}/eval", dependencies=[Depends(require_admin_access)])
async def get_game_eval(session_id: str):
    _require_game(session_id)
    return _serialize_payload(game_manager.get_eval_report(session_id))
