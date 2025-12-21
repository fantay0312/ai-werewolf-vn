from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.models.game_state import GamePhase, Role

class VoteRecord(BaseModel):
    day: int
    voted_for: Optional[int] = None # None means abstain

class NotableSpeech(BaseModel):
    speaker_id: int
    day: int
    summary: str
    tags: List[str] = []

class PlayerProfile(BaseModel):
    player_id: int
    
    # Analysis
    claimed_role: Optional[Role] = None
    claim_day: Optional[int] = None
    
    # Trust
    trust_level: str = "neutral" # "trusted", "neutral", "suspicious", "confirmed_wolf"
    trust_reasons: List[str] = []
    
    # Voting
    voting_pattern: List[VoteRecord] = []
    
    # Relation
    relation_to_me: str = "unknown" # "teammate", "enemy", "unknown"

class VoteResult(BaseModel):
    target: int
    vote_count: int
    voters: List[int]

class DailyDeaths(BaseModel):
    night_deaths: List[int] = []
    day_deaths: List[int] = []

class DailySummary(BaseModel):
    day: int
    headline: str = "" # Brief title of the day's events
    night_summary: str = ""
    day_summary: str = ""
    snippets: List[str] = [] # Key quotes or snippets
    deaths: DailyDeaths = DailyDeaths()
    vote_result: Optional[VoteResult] = None
    notable_speeches: List[NotableSpeech] = []

class KeyEvent(BaseModel):
    day: int
    phase: GamePhase
    event_type: str
    description: str
    involved_players: List[int] = []
    importance: str = "medium" # "critical", "high", "medium", "low"

class SummaryLayer(BaseModel):
    daily_summaries: List[DailySummary] = []
    player_profiles: List[PlayerProfile] = []
    key_events: List[KeyEvent] = []
