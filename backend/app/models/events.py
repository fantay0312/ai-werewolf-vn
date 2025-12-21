from dataclasses import dataclass, field
from typing import Optional, Any, Dict
from app.models.game_state import GamePhase, DeathCause
import time

@dataclass
class GameEvent:
    """游戏事件基类"""
    event_type: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=lambda: time.time())

@dataclass
class StateUpdateEvent(GameEvent):
    """状态更新事件"""
    def __init__(self, state_data: Dict[str, Any]):
        self.event_type = "state_update"
        self.data = state_data
        self.timestamp = time.time()

@dataclass
class PhaseChangeEvent(GameEvent):
    """阶段变更事件"""
    def __init__(self, phase: GamePhase, day: int):
        self.event_type = "phase_change"
        self.data = {"phase": phase, "day": day}
        self.timestamp = time.time()

@dataclass
class PlayerSpeechEvent(GameEvent):
    """玩家发言事件"""
    def __init__(self, player_id: int, content: str, is_inner_thought: bool = False):
        self.event_type = "player_speech"
        self.data = {
            "player_id": player_id,
            "content": content,
            "is_inner_thought": is_inner_thought
        }
        self.timestamp = time.time()

@dataclass
class PlayerDeathEvent(GameEvent):
    """玩家死亡事件"""
    def __init__(self, player_id: int, cause: DeathCause, day: int):
        self.event_type = "player_death"
        self.data = {
            "player_id": player_id,
            "cause": cause,
            "day": day
        }
        self.timestamp = time.time()

@dataclass
class WolfMessageEvent(GameEvent):
    """狼人消息事件（仅狼人可见）"""
    def __init__(self, speaker_id: int, content: str, round: int):
        self.event_type = "wolf_message"
        self.data = {
            "speaker_id": speaker_id,
            "content": content,
            "round": round
        }
        self.timestamp = time.time()

@dataclass
class JudgeBroadcastEvent(GameEvent):
    """法官播报事件"""
    def __init__(self, content: str, type: str = "info"):
        self.event_type = "judge_broadcast"
        self.data = {
            "content": content,
            "type": type
        }
        self.timestamp = time.time()

@dataclass
class VoteUpdateEvent(GameEvent):
    """投票更新事件"""
    def __init__(self, voter_id: int, target_id: int, weight: int = 1):
        self.event_type = "vote_update"
        self.data = {
            "voter_id": voter_id,
            "target_id": target_id,
            "weight": weight
        }
        self.timestamp = time.time()

@dataclass
class GameEndEvent(GameEvent):
    """游戏结束事件"""
    def __init__(self, winner: str, message: str):
        self.event_type = "game_end"
        self.data = {
            "winner": winner,
            "message": message
        }
        self.timestamp = time.time()
