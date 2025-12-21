from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.models.game_state import GamePhase

class DialogueEntry(BaseModel):
    speaker_id: int
    speaker_name: str
    content: str
    timestamp: float
    phase: GamePhase
    day: int
    
    # Metadata
    mentions: List[int] = []
    sentiment: str = "neutral" # "positive", "negative", "neutral"
    claims: List[str] = []

class DiscussionFocus(BaseModel):
    topic: str = ""
    key_players: List[int] = []

class RecentLayer(BaseModel):
    current_phase_dialogue: List[DialogueEntry] = []
    previous_phase_dialogue: List[DialogueEntry] = []
    current_focus: DiscussionFocus = DiscussionFocus()
