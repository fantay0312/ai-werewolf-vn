from fastapi import APIRouter, HTTPException
from app.core.game_manager import game_manager
from app.models.action_model import ActionRequest, ActionResponse

router = APIRouter()

@router.post("/{session_id}/action", response_model=ActionResponse)
async def submit_action(session_id: str, action: ActionRequest):
    success, error_msg = await game_manager.process_action(session_id, action)
    if not success:
        raise HTTPException(status_code=400, detail=error_msg)
    return ActionResponse(success=True)
