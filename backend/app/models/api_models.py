from typing import List, Literal, Optional

from pydantic import BaseModel

from app.models.game_state import GamePhase, Role

VisibleRole = Role | Literal["unknown"]


class PlayerView(BaseModel):
    id: int
    name: str
    role: VisibleRole
    portrait: str
    is_human: bool = False
    is_alive: bool = True
    is_sheriff: bool = False
    has_acted: bool = False
    poison_used: bool = False
    antidote_used: bool = False
    gun_used: bool = False


class GameLogView(BaseModel):
    id: str
    day: int
    phase: GamePhase
    content: str
    player_id: Optional[int] = None
    is_public: bool = True
    type: str = "normal"
    data: Optional[dict] = None


class WolfDiscussMessageView(BaseModel):
    id: str
    speaker_id: int
    content: str
    round: int


class GameStateView(BaseModel):
    session_id: str
    day: int
    phase: GamePhase
    players: List[PlayerView]
    game_logs: List[GameLogView] = []
    time_remaining: int = 60
    winner: Optional[str] = None
    votes: dict[int, int] = {}
    pk_votes: dict[int, int] = {}
    pk_candidates: List[int] = []
    wolf_kill_target: Optional[int] = None
    dead_players: List[int] = []
    sheriff_candidate_ids: List[int] = []
    sheriff_id: Optional[int] = None
    election_explode_count: int = 0
    pending_sheriff_election: bool = False
    election_cancelled: bool = False
    speaking_order: List[int] = []
    current_speaker_index: int = 0
    wolf_discuss_messages: List[WolfDiscussMessageView] = []


class CreateGameResponse(BaseModel):
    player_token: str
    state: GameStateView
