from pydantic import BaseModel
from .game_state import Role

class PlayerCreate(BaseModel):
    name: str
    is_human: bool = False

class PlayerResponse(BaseModel):
    id: int
    name: str
    role: Role
    is_alive: bool
    portrait: str
