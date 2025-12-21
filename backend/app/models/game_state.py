from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class GamePhase(str, Enum):
    GAME_START = "GAME_START"
    NIGHT_START = "NIGHT_START"
    NIGHT_WOLF_DISCUSS = "NIGHT_WOLF_DISCUSS"
    NIGHT_WOLF_VOTE = "NIGHT_WOLF_VOTE"
    NIGHT_SEER = "NIGHT_SEER"
    NIGHT_WITCH = "NIGHT_WITCH"
    NIGHT_GUARD = "NIGHT_GUARD"
    NIGHT_RESOLVE = "NIGHT_RESOLVE"
    DAY_START = "DAY_START"
    DAY_LAST_WORDS = "DAY_LAST_WORDS"
    SHERIFF_ELECTION = "SHERIFF_ELECTION"
    SHERIFF_SPEECH = "SHERIFF_SPEECH"
    SHERIFF_VOTE = "SHERIFF_VOTE"
    DAY_DISCUSS = "DAY_DISCUSS"
    DAY_VOTE = "DAY_VOTE"
    DAY_VOTE_RESULT = "DAY_VOTE_RESULT"
    DAY_PK_SPEECH = "DAY_PK_SPEECH"      # 平票PK发言
    DAY_PK_VOTE = "DAY_PK_VOTE"          # 平票PK投票
    DAY_PK_RESULT = "DAY_PK_RESULT"      # 平票PK结果
    HUNTER_SKILL = "HUNTER_SKILL"
    SHERIFF_TRANSFER = "SHERIFF_TRANSFER"
    GAME_END = "GAME_END"

class Camp(str, Enum):
    GOOD = "good"
    WOLF = "wolf"

class DeathCause(str, Enum):
    WOLF_KILL = "wolf_kill"
    VOTE_EXILE = "vote_exile"
    WITCH_POISON = "witch_poison"
    HUNTER_SHOOT = "hunter_shoot"
    WOLF_KING_SHOOT = "wolf_king_shoot"
    SELF_EXPLODE = "self_explode"

class Role(str, Enum):
    VILLAGER = "villager"
    WOLF = "wolf"
    WOLF_KING = "wolf_king"
    SEER = "seer"
    WITCH = "witch"
    GUARD = "guard"
    HUNTER = "hunter"

class Player(BaseModel):
    id: int
    name: str
    role: Role
    portrait: str
    is_human: bool = False
    is_alive: bool = True
    is_sheriff: bool = False
    has_acted: bool = False  # Current phase action status

    # Skill status
    poison_used: bool = False
    antidote_used: bool = False
    gun_used: bool = False

    # Night status (reset every night)
    protected_by_guard: bool = False
    killed_by_wolf: bool = False
    poisoned_by_witch: bool = False
    saved_by_witch: bool = False
    checked_by_seer: bool = False

    # AI Memory Persistence
    ai_memory: Optional[Dict[str, Any]] = None

class ActionType(str, Enum):
    PASS = "pass"          # Skip action
    CONFIRM = "confirm"    # Confirm/Next
    VOTE = "vote"          # Vote for player
    KILL = "kill"          # Wolf kill
    CHECK = "check"        # Seer check
    POISON = "poison"      # Witch poison
    SAVE = "save"          # Witch save
    GUARD = "guard"        # Guard protect
    SHOOT = "shoot"        # Hunter/Wolf King shoot
    SPEECH = "speech"      # Speak
    RUN_FOR_SHERIFF = "run_for_sheriff"
    WITHDRAW = "withdraw"
    SELF_EXPLODE = "self_explode"

class PlayerAction(BaseModel):
    player_id: int
    type: ActionType
    target_id: Optional[int] = None
    content: Optional[str] = None
    timestamp: float

class GameLog(BaseModel):
    id: str
    day: int
    phase: GamePhase
    content: str
    player_id: Optional[int] = None
    is_public: bool = True  # Whether all players can see this log
    type: str = "normal" # normal, broadcast, speech, action
    data: Optional[Dict[str, Any]] = None # Structured data for AI analysis

class WolfDiscussMessage(BaseModel):
    id: str
    speaker_id: int
    content: str
    round: int

class GameState(BaseModel):
    session_id: str
    day: int
    phase: GamePhase
    players: List[Player]
    game_logs: List[GameLog] = []
    time_remaining: int = 60
    winner: Optional[str] = None  # "wolf", "villager", or None

    # Temporary state for current phase
    votes: Dict[int, int] = {}  # voter_id -> target_id
    wolf_kill_target: Optional[int] = None
    dead_players: List[int] = []  # List of player IDs who died this night/day

    # Sheriff Election Status
    sheriff_candidate_ids: List[int] = []  # Players running for sheriff
    sheriff_id: Optional[int] = None
    election_explode_count: int = 0  # Track wolf self-explosions during election
    pending_sheriff_election: bool = False  # Postponed election due to single explode
    election_cancelled: bool = False  # Double explode cancels election forever

    # Track wolves who ran for sheriff (for double explode rule)
    election_wolf_candidates: List[int] = []

    # PK (Tie-break) Status
    pk_candidates: List[int] = []  # Players in PK due to tie vote
    pk_round: int = 0  # Current PK round (0 = no PK, 1 = first PK)
    pk_votes: Dict[int, int] = {}  # Votes during PK round

    # Skill Status
    last_guarded_player: Optional[int] = None  # For Guard rule
    next_phase_after_skill: Optional[GamePhase] = None  # Where to return after death skills
    wolf_discuss_round: int = 0
    wolf_discuss_messages: List[WolfDiscussMessage] = []

    # Discussion Status
    speaking_order: List[int] = []
    current_speaker_index: int = 0
