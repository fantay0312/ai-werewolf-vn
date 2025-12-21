from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class GameConfig(BaseModel):
    player_count: int = 12
    wolf_count: int = 4
    roles: List[str] = []
    
class SessionContext(BaseModel):
    session_id: str
    start_time: str
    game_config: GameConfig = GameConfig()
    
class MetadataLayer(BaseModel):
    """
    Layer 1: Session Metadata
    Temporary, valid only for current session.
    Stores game configuration and session context.
    """
    session_context: SessionContext
