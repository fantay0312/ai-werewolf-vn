import uuid
import random
import time
import logging
import asyncio
from typing import List, Dict, Optional

from app.models.game_state import GameState, GamePhase, Player, Role, GameLog, ActionType
from app.models.action_model import ActionRequest
from app.core.phase_handler import PhaseHandler
from app.core.judge import JudgeSystem
from app.core.event_manager import event_manager
from app.models.events import PhaseChangeEvent, JudgeBroadcastEvent
from app.ai.agent import AIAgent

# Handlers
from app.core.handlers.game_start import GameStartHandler
from app.core.handlers.night_start import NightStartHandler
from app.core.handlers.night_wolf_discuss import NightWolfDiscussHandler
from app.core.handlers.night_wolf_vote import NightWolfVoteHandler
from app.core.handlers.night_seer import NightSeerHandler
from app.core.handlers.night_witch import NightWitchHandler
from app.core.handlers.night_guard import NightGuardHandler
from app.core.handlers.night_resolve import NightResolveHandler
from app.core.handlers.day_start import DayStartHandler
from app.core.handlers.day_discuss import DayDiscussHandler
from app.core.handlers.day_vote import DayVoteHandler
from app.core.handlers.day_vote_result import DayVoteResultHandler
from app.core.handlers.sheriff_election import SheriffElectionHandler
from app.core.handlers.sheriff_speech import SheriffSpeechHandler
from app.core.handlers.sheriff_vote import SheriffVoteHandler
from app.core.handlers.hunter_skill import HunterSkillHandler
from app.core.handlers.sheriff_transfer import SheriffTransferHandler
from app.core.handlers.day_last_words import DayLastWordsHandler
from app.core.handlers.day_pk_speech import DayPKSpeechHandler
from app.core.handlers.day_pk_vote import DayPKVoteHandler
from app.core.handlers.day_pk_result import DayPKResultHandler

logger = logging.getLogger(__name__)

# Maximum content length for player speech
MAX_SPEECH_LENGTH = 500

# Phase display names
PHASE_DISPLAY_NAMES = {
    GamePhase.GAME_START: "游戏开始",
    GamePhase.NIGHT_START: "夜晚开始",
    GamePhase.NIGHT_WOLF_DISCUSS: "狼人讨论",
    GamePhase.NIGHT_WOLF_VOTE: "狼人投票",
    GamePhase.NIGHT_SEER: "预言家查验",
    GamePhase.NIGHT_WITCH: "女巫行动",
    GamePhase.NIGHT_GUARD: "守卫守护",
    GamePhase.NIGHT_RESOLVE: "夜晚结算",
    GamePhase.DAY_START: "白天开始",
    GamePhase.DAY_LAST_WORDS: "遗言阶段",
    GamePhase.DAY_DISCUSS: "讨论阶段",
    GamePhase.DAY_VOTE: "投票阶段",
    GamePhase.DAY_VOTE_RESULT: "投票结果",
    GamePhase.SHERIFF_ELECTION: "警长竞选",
    GamePhase.SHERIFF_SPEECH: "警长发言",
    GamePhase.SHERIFF_VOTE: "警长投票",
    GamePhase.HUNTER_SKILL: "猎人/狼王开枪",
    GamePhase.SHERIFF_TRANSFER: "警徽移交",
}

ACTION_DISPLAY_NAMES = {
    ActionType.CONFIRM: "确认",
    ActionType.SPEECH: "发言",
    ActionType.VOTE: "投票",
    ActionType.KILL: "刀人",
    ActionType.CHECK: "查验",
    ActionType.SAVE: "救人",
    ActionType.POISON: "毒人",
    ActionType.GUARD: "守护",
    ActionType.SHOOT: "开枪",
    ActionType.PASS: "跳过",
    ActionType.RUN_FOR_SHERIFF: "竞选警长",
    ActionType.WITHDRAW: "退出竞选",
    ActionType.SELF_EXPLODE: "自爆",
}

# Portrait asset mapping
PORTRAIT_MAP = {
    Role.VILLAGER: "/images/portraits/村民.jpg",
    Role.WOLF: "/images/portraits/狼人.png",
    Role.WOLF_KING: "/images/portraits/狼王.png",
    Role.SEER: "/images/portraits/预言家.jpg",
    Role.WITCH: "/images/portraits/女巫.png",
    Role.GUARD: "/images/portraits/守卫.png",
    Role.HUNTER: "/images/portraits/猎人.png",
}

# Phase -> broadcast type mapping
BROADCAST_PHASES = {
    GamePhase.NIGHT_START: "night_start",
    GamePhase.DAY_START: "day_start",
    GamePhase.SHERIFF_ELECTION: "sheriff_election",
    GamePhase.DAY_VOTE: "vote_start",
}

# Phase -> handler class mapping
PHASE_HANDLERS: Dict[GamePhase, type] = {
    GamePhase.GAME_START: GameStartHandler,
    GamePhase.NIGHT_START: NightStartHandler,
    GamePhase.NIGHT_WOLF_DISCUSS: NightWolfDiscussHandler,
    GamePhase.NIGHT_WOLF_VOTE: NightWolfVoteHandler,
    GamePhase.NIGHT_SEER: NightSeerHandler,
    GamePhase.NIGHT_WITCH: NightWitchHandler,
    GamePhase.NIGHT_GUARD: NightGuardHandler,
    GamePhase.NIGHT_RESOLVE: NightResolveHandler,
    GamePhase.DAY_START: DayStartHandler,
    GamePhase.DAY_LAST_WORDS: DayLastWordsHandler,
    GamePhase.DAY_DISCUSS: DayDiscussHandler,
    GamePhase.DAY_VOTE: DayVoteHandler,
    GamePhase.DAY_VOTE_RESULT: DayVoteResultHandler,
    GamePhase.DAY_PK_SPEECH: DayPKSpeechHandler,
    GamePhase.DAY_PK_VOTE: DayPKVoteHandler,
    GamePhase.DAY_PK_RESULT: DayPKResultHandler,
    GamePhase.SHERIFF_ELECTION: SheriffElectionHandler,
    GamePhase.SHERIFF_SPEECH: SheriffSpeechHandler,
    GamePhase.SHERIFF_VOTE: SheriffVoteHandler,
    GamePhase.HUNTER_SKILL: HunterSkillHandler,
    GamePhase.SHERIFF_TRANSFER: SheriffTransferHandler,
}

# Phase -> set of roles/conditions that should act
PHASE_ACTOR_RULES = {
    GamePhase.GAME_START: lambda p, g: True,
    GamePhase.NIGHT_WOLF_DISCUSS: lambda p, g: p.role in (Role.WOLF, Role.WOLF_KING),
    GamePhase.NIGHT_WOLF_VOTE: lambda p, g: p.role in (Role.WOLF, Role.WOLF_KING),
    GamePhase.NIGHT_SEER: lambda p, g: p.role == Role.SEER,
    GamePhase.NIGHT_WITCH: lambda p, g: p.role == Role.WITCH,
    GamePhase.NIGHT_GUARD: lambda p, g: p.role == Role.GUARD,
    GamePhase.DAY_DISCUSS: lambda p, g: True,
    GamePhase.DAY_VOTE: lambda p, g: True,
    GamePhase.SHERIFF_ELECTION: lambda p, g: True,
    GamePhase.SHERIFF_SPEECH: lambda p, g: p.id in g.sheriff_candidate_ids,
    GamePhase.SHERIFF_VOTE: lambda p, g: True,
}


class GameManager:
    def __init__(self):
        self.games: Dict[str, GameState] = {}
        self.game_timestamps: Dict[str, float] = {}
        self.max_games = 100
        self.game_ttl = 3600 * 24
        self.judge_system = JudgeSystem()

    def _get_handler(self, game: GameState) -> Optional[PhaseHandler]:
        handler_cls = PHASE_HANDLERS.get(game.phase)
        if handler_cls:
            return handler_cls(self, game)
        return None

    def create_game(self) -> GameState:
        self._cleanup_old_games()

        session_id = str(uuid.uuid4())
        players = self._init_players(session_id)

        game_state = GameState(
            session_id=session_id,
            day=1,
            phase=GamePhase.GAME_START,
            players=players,
            time_remaining=60,
        )

        self.games[session_id] = game_state
        self.game_timestamps[session_id] = time.time()

        handler = self._get_handler(game_state)
        if handler:
            handler.on_enter()

        logger.info(f"Created new game {session_id}. Total active games: {len(self.games)}")
        return game_state

    def get_game(self, session_id: str) -> Optional[GameState]:
        return self.games.get(session_id)

    def _init_players(self, session_id: str) -> List[Player]:
        roles = [
            Role.WOLF, Role.WOLF, Role.WOLF, Role.WOLF_KING,
            Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,
            Role.SEER, Role.WITCH, Role.GUARD, Role.HUNTER,
        ]
        random.shuffle(roles)

        players = []
        for i, role in enumerate(roles):
            is_human = (i == 0)
            portrait = PORTRAIT_MAP.get(role, "/images/portraits/村民.jpg")

            player = Player(
                id=i + 1,
                name=f"{i + 1}号玩家",
                role=role,
                portrait=portrait,
                is_human=is_human,
            )

            if not is_human:
                from app.ai.memory.memory_manager import MemoryManager
                mm = MemoryManager(player)
                mm.init_metadata(
                    session_id=session_id,
                    game_config={
                        "player_count": 12,
                        "wolf_count": 4,
                        "roles": [r.value for r in roles],
                    },
                )
                mm.save_to_player(player)

            players.append(player)
        return players

    async def process_action(self, session_id: str, action: ActionRequest) -> tuple[bool, str]:
        """Process action and return (success, error_message)"""
        game = self.games.get(session_id)
        if not game:
            logger.warning(f"Action attempted on non-existent game: {session_id}")
            return False, "游戏不存在或已结束"

        player = next((p for p in game.players if p.id == action.player_id), None)
        if not player:
            logger.warning(f"Invalid player_id {action.player_id} in game {session_id}")
            return False, "无效的玩家"

        # Validate player is alive (with exceptions for death-phase actions)
        if not player.is_alive:
            if game.phase == GamePhase.HUNTER_SKILL and action.type in (ActionType.SHOOT, ActionType.PASS):
                pass
            elif action.type == ActionType.PASS:
                pass
            else:
                logger.warning(f"Dead player {action.player_id} attempted action {action.type}")
                return False, "你已死亡，无法执行此操作"

        # Validate speech content length
        if action.content and len(action.content) > MAX_SPEECH_LENGTH:
            return False, f"发言内容过长，最多{MAX_SPEECH_LENGTH}字"

        handler = self._get_handler(game)
        if not handler:
            logger.error(f"No handler found for phase {game.phase}")
            return False, "当前阶段无法处理操作"

        success = handler.process_action(action)
        if not success:
            phase_name = PHASE_DISPLAY_NAMES.get(game.phase, str(game.phase))
            action_name = ACTION_DISPLAY_NAMES.get(action.type, str(action.type))
            logger.warning(
                f"Handler {handler.__class__.__name__} rejected {action.type} "
                f"from player {action.player_id} in phase {game.phase}"
            )
            return False, f"当前是{phase_name}，无法执行{action_name}操作"

        # Check if phase should advance
        next_phase = handler.try_advance()
        if next_phase:
            await self._advance_phase(game, next_phase)
        else:
            asyncio.create_task(self.trigger_ai_actions(session_id))

        return True, ""

    async def _advance_phase(self, game: GameState, next_phase: GamePhase):
        logger.info(f"Advancing phase from {game.phase} to {next_phase}")

        game.phase = next_phase
        game.time_remaining = self.judge_system.get_time_limit(next_phase)

        handler = self._get_handler(game)
        if handler:
            broadcast_type = BROADCAST_PHASES.get(next_phase)
            if broadcast_type:
                broadcast_content = self.judge_system.generate_broadcast(broadcast_type)
                game.game_logs.append(GameLog(
                    id=str(uuid.uuid4()),
                    day=game.day,
                    phase=game.phase,
                    player_id=0,
                    content=broadcast_content,
                    type="broadcast",
                ))
                await event_manager.publish(JudgeBroadcastEvent(content=broadcast_content, type=broadcast_type))

            await event_manager.publish(PhaseChangeEvent(phase=next_phase, day=game.day))

            handler.on_enter()

            auto_next = handler.try_advance()
            if auto_next:
                await self._advance_phase(game, auto_next)
            else:
                asyncio.create_task(self.trigger_ai_actions(game.session_id))

    def _cleanup_old_games(self):
        """Remove expired games and enforce max game limit"""
        current_time = time.time()
        expired = [sid for sid, t in self.game_timestamps.items() if current_time - t > self.game_ttl]

        for sid in expired:
            del self.games[sid]
            del self.game_timestamps[sid]
            logger.info(f"Cleaned up expired game {sid}")

        if len(self.games) >= self.max_games:
            sorted_games = sorted(self.game_timestamps.items(), key=lambda x: x[1])
            to_remove = len(self.games) - self.max_games + 1
            for sid, _ in sorted_games[:to_remove]:
                del self.games[sid]
                del self.game_timestamps[sid]
                logger.warning(f"Removed game {sid} due to max games limit")

    async def trigger_ai_actions(self, session_id: str):
        """Check if any AI players need to act and trigger them."""
        game = self.games.get(session_id)
        if not game:
            return

        pending_ais = self._get_pending_ai_players(game)
        if not pending_ais:
            return

        ai_player = pending_ais[0]
        agent = AIAgent(ai_player)
        logger.info(f"Triggering AI {ai_player.id} ({ai_player.role}) for phase {game.phase}")

        try:
            action_request = await agent.decide_action(game)
            logger.info(f"AI {ai_player.id} decided: type={action_request.type}, target={action_request.target_id}")
            await self.process_action(session_id, action_request)
        except Exception as e:
            logger.error(
                f"AI {ai_player.id} ({ai_player.role}) failed in phase {game.phase}: {e}",
                exc_info=True,
            )
            fallback = self._get_fallback_action(game, ai_player)
            logger.info(f"Using fallback action for AI {ai_player.id}: {fallback.type}")
            success, _ = await self.process_action(session_id, fallback)
            if not success:
                ai_player.has_acted = True

    def _get_pending_ai_players(self, game: GameState) -> List[Player]:
        """Identify AI players that need to act in the current phase."""
        pending = []

        for p in game.players:
            if p.has_acted:
                continue

            # Special: last words phase - only dead AI players
            if game.phase == GamePhase.DAY_LAST_WORDS:
                if not p.is_human and p.id in game.dead_players:
                    pending.append(p)
                continue

            # Special: hunter skill - dead hunter/wolf_king who can shoot
            if game.phase == GamePhase.HUNTER_SKILL:
                if (not p.is_human and not p.is_alive
                        and p.role in (Role.HUNTER, Role.WOLF_KING)
                        and not p.gun_used and not p.poisoned_by_witch):
                    pending.append(p)
                continue

            # Normal phases: only alive AI players
            if p.is_human or not p.is_alive:
                continue

            rule = PHASE_ACTOR_RULES.get(game.phase)
            if rule and rule(p, game):
                pending.append(p)

        return pending

    def _get_fallback_action(self, game: GameState, player: Player) -> ActionRequest:
        if game.phase == GamePhase.NIGHT_WOLF_VOTE:
            targets = [p for p in game.players if p.is_alive and p.role not in (Role.WOLF, Role.WOLF_KING)]
            target_id = random.choice(targets).id if targets else game.players[0].id
            return ActionRequest(player_id=player.id, type=ActionType.KILL, target_id=target_id)
        return ActionRequest(player_id=player.id, type=ActionType.PASS)


game_manager = GameManager()
