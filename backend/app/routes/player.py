from fastapi import APIRouter, Header, HTTPException
from app.core.game_manager import game_manager
from app.models.action_model import ActionRequest, ActionResponse
from app.security import PLAYER_TOKEN_HEADER

router = APIRouter()

@router.post("/{session_id}/action", response_model=ActionResponse)
async def submit_action(
    session_id: str,
    action: ActionRequest,
    x_player_token: str | None = Header(default=None, alias=PLAYER_TOKEN_HEADER),
):
    if not game_manager.get_game(session_id):
        raise HTTPException(status_code=404, detail="Game not found")

    player_id = game_manager.authenticate_player(session_id, x_player_token)
    if player_id is None:
        raise HTTPException(status_code=403, detail="玩家认证失败")

    authenticated_action = action.model_copy(update={"player_id": player_id})
    success, error_msg = await game_manager.process_action(session_id, authenticated_action)
    if not success:
        raise HTTPException(status_code=400, detail=error_msg)
    return ActionResponse(success=True)
