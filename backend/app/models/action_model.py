from pydantic import BaseModel
from typing import Optional
from app.models.game_state import ActionType

class ActionRequest(BaseModel):
    player_id: int
    type: ActionType
    target_id: Optional[int] = None
    content: Optional[str] = None

class ActionResponse(BaseModel):
    success: bool
    message: Optional[str] = None
