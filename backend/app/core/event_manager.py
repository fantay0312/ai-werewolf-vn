import asyncio
from typing import Dict, List, Callable, Optional
from app.models.events import GameEvent
import logging

logger = logging.getLogger(__name__)

class EventManager:
    """事件管理器"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._sse_queues: Dict[int, asyncio.Queue] = {}  # player_id -> queue
        # Global queue for observers or general events if needed, 
        # but for now we map queues to player_ids. 
        # Use player_id=0 for public/observer stream?
        self._sse_queues[0] = asyncio.Queue() 

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    async def publish(self, event: GameEvent) -> None:
        """发布事件"""
        # 1. Notify internal subscribers
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in subscriber for {event.event_type}: {e}")

        # 2. Push to SSE queues
        # By default, broadcast to all queues unless filtered
        # Logic for filtering (e.g. wolf messages) should be handled here or by the caller?
        # Ideally, the event itself should know who can see it, or we have specific methods.
        
        if event.event_type == "wolf_message":
            # Only push to wolf players (we need to know who they are, or just push to all and frontend filters? NO, security risk)
            # We need a way to know which queue belongs to a wolf.
            # For MVP, we might push to all but encrypt? Or just rely on caller to use push_to_player?
            # Better: use broadcast with exclusion or specific targeting.
            pass # Handled by specific methods
        else:
            await self.broadcast(event)

    async def push_to_player(self, player_id: int, event: GameEvent) -> None:
        """推送事件给指定玩家"""
        if player_id in self._sse_queues:
            await self._sse_queues[player_id].put(event)

    async def broadcast(self, event: GameEvent, exclude_players: List[int] = None) -> None:
        """广播事件给所有玩家"""
        exclude = set(exclude_players or [])
        for pid, queue in self._sse_queues.items():
            if pid not in exclude:
                await queue.put(event)

    async def create_sse_queue(self, player_id: int) -> asyncio.Queue:
        """为玩家创建SSE队列"""
        if player_id not in self._sse_queues:
            self._sse_queues[player_id] = asyncio.Queue()
        return self._sse_queues[player_id]

    def remove_sse_queue(self, player_id: int) -> None:
        """移除玩家的SSE队列"""
        if player_id in self._sse_queues:
            del self._sse_queues[player_id]

event_manager = EventManager()
