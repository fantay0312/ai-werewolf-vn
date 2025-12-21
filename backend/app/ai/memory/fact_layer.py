from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.models.game_state import GamePhase, Role

class DeathRecord(BaseModel):
    player_id: int
    day: int
    phase: GamePhase
    cause: str # "wolf_kill", "vote", "poison", "hunter_shot", "wolf_king_shot"

class CheckResult(BaseModel):
    day: int
    target_id: int
    result: str # "good" | "bad"

class ConfirmedAction(BaseModel):
    day: int
    phase: GamePhase
    action_type: str
    actor_id: int
    target_id: Optional[int] = None
    result: Optional[str] = None

class SkillStatus(BaseModel):
    # Witch
    has_antidote: bool = False
    has_poison: bool = False
    antidote_used_on: Optional[int] = None
    poison_used_on: Optional[int] = None
    
    # Guard
    last_guard_target: Optional[int] = None
    
    # Seer
    check_results: List[CheckResult] = []
    
    # Hunter/Wolf King
    can_shoot: bool = False
    shot_target: Optional[int] = None

class FactLayer(BaseModel):
    # Basic Game Info
    game_id: str
    current_day: int
    current_phase: GamePhase
    
    # Identity (Visible to AI)
    my_player_id: int
    my_role: Role
    my_camp: str # "good" | "wolf"
    
    # Wolf Specific
    wolf_teammates: List[int] = []
    
    # Survival Status
    alive_players: List[int]
    dead_players: List[DeathRecord] = []
    
    # Sheriff Info
    sheriff_id: Optional[int] = None
    sheriff_candidates: List[int] = []
    
    # Skill Status
    skill_status: SkillStatus = SkillStatus()
    
    # Confirmed Info
    confirmed_actions: List[ConfirmedAction] = []
