from dataclasses import dataclass, field
from typing import Optional, Any, Dict, Iterable
from app.models.game_state import GamePhase, DeathCause
import time


def _with_delivery_meta(
    data: Dict[str, Any],
    *,
    session_id: str | None = None,
    viewer_ids: Iterable[int] | None = None,
) -> Dict[str, Any]:
    payload = dict(data)
    if session_id is not None:
        payload["session_id"] = session_id
    if viewer_ids is not None:
        payload["viewer_ids"] = list(viewer_ids)
    return payload


@dataclass
class GameEvent:
    """游戏事件基类"""
    event_type: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=lambda: time.time())

@dataclass
class StateUpdateEvent(GameEvent):
    """状态更新事件"""
    def __init__(self, state_data: Dict[str, Any], *, session_id: str | None = None):
        self.event_type = "state_update"
        self.data = _with_delivery_meta(state_data, session_id=session_id)
        self.timestamp = time.time()

@dataclass
class PhaseChangeEvent(GameEvent):
    """阶段变更事件"""
    def __init__(self, phase: GamePhase, day: int, *, session_id: str | None = None):
        self.event_type = "phase_change"
        self.data = _with_delivery_meta({"phase": phase, "day": day}, session_id=session_id)
        self.timestamp = time.time()

@dataclass
class PlayerSpeechEvent(GameEvent):
    """玩家发言事件"""
    def __init__(
        self,
        player_id: int,
        content: str,
        is_inner_thought: bool = False,
        *,
        session_id: str | None = None,
        viewer_ids: Iterable[int] | None = None,
    ):
        self.event_type = "player_speech"
        self.data = _with_delivery_meta(
            {
                "player_id": player_id,
                "content": content,
                "is_inner_thought": is_inner_thought,
            },
            session_id=session_id,
            viewer_ids=viewer_ids,
        )
        self.timestamp = time.time()

@dataclass
class PlayerDeathEvent(GameEvent):
    """玩家死亡事件"""
    def __init__(self, player_id: int, cause: DeathCause, day: int, *, session_id: str | None = None):
        self.event_type = "player_death"
        self.data = _with_delivery_meta(
            {
                "player_id": player_id,
                "cause": cause,
                "day": day,
            },
            session_id=session_id,
        )
        self.timestamp = time.time()

@dataclass
class WolfMessageEvent(GameEvent):
    """狼人消息事件（仅狼人可见）"""
    def __init__(
        self,
        speaker_id: int,
        content: str,
        round: int,
        *,
        session_id: str | None = None,
        viewer_ids: Iterable[int] | None = None,
    ):
        self.event_type = "wolf_message"
        self.data = _with_delivery_meta(
            {
                "speaker_id": speaker_id,
                "content": content,
                "round": round,
            },
            session_id=session_id,
            viewer_ids=viewer_ids,
        )
        self.timestamp = time.time()

@dataclass
class JudgeBroadcastEvent(GameEvent):
    """法官播报事件"""
    def __init__(self, content: str, type: str = "info", *, session_id: str | None = None):
        self.event_type = "judge_broadcast"
        self.data = _with_delivery_meta(
            {
                "content": content,
                "type": type,
            },
            session_id=session_id,
        )
        self.timestamp = time.time()

@dataclass
class VoteUpdateEvent(GameEvent):
    """投票更新事件"""
    def __init__(self, voter_id: int, target_id: int, weight: int = 1, *, session_id: str | None = None):
        self.event_type = "vote_update"
        self.data = _with_delivery_meta(
            {
                "voter_id": voter_id,
                "target_id": target_id,
                "weight": weight,
            },
            session_id=session_id,
        )
        self.timestamp = time.time()

@dataclass
class GameEndEvent(GameEvent):
    """游戏结束事件"""
    def __init__(self, winner: str, message: str, *, session_id: str | None = None):
        self.event_type = "game_end"
        self.data = _with_delivery_meta(
            {
                "winner": winner,
                "message": message,
            },
            session_id=session_id,
        )
        self.timestamp = time.time()
