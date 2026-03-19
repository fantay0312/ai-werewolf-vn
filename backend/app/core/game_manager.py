import uuid
import random
import time
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

from app.application.ai.memory_lifecycle import MemoryLifecycleManager
from app.config import get_server_config
from app.domain.commands.player_commands import PlayerCommand
from app.domain.events.gameplay import (
    ai_decision_recorded,
    game_created,
    game_log_recorded,
    phase_entered,
    player_action_received,
)
from app.domain.kernel.snapshot import GameSnapshot
from app.domain.services.phase_director import PhaseDirector, PhaseValidationError
from app.eval.metrics import EvalMetricsService
from app.eval.replay_service import ReplayService
from app.infrastructure.event_store import event_store
from app.infrastructure.game_snapshot_store import GameSnapshotStore
from app.infrastructure.runtime_metrics import runtime_metrics
from app.models.game_state import GameState, GamePhase, Player, Role, GameLog, ActionType
from app.models.action_model import ActionRequest
from app.core.phase_handler import PhaseHandler
from app.core.judge import JudgeSystem
from app.core.event_manager import event_manager
from app.models.events import PhaseChangeEvent, JudgeBroadcastEvent
from app.ai.agent import AIAgent
from app.security import generate_access_token

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
    GamePhase.DAY_PK_VOTE: lambda p, g: p.id not in g.pk_candidates,
    GamePhase.SHERIFF_ELECTION: lambda p, g: True,
    GamePhase.SHERIFF_SPEECH: lambda p, g: p.id in g.sheriff_candidate_ids,
    GamePhase.SHERIFF_VOTE: lambda p, g: True,
}


class GameManager:
    def __init__(self):
        self.games: Dict[str, GameState] = {}
        self.game_timestamps: Dict[str, float] = {}
        self.player_tokens: Dict[str, str] = {}
        self.ai_locks: Dict[str, asyncio.Lock] = {}
        self.max_games = 100
        self.game_ttl = 3600 * 24
        self.judge_system = JudgeSystem()
        self.phase_director = PhaseDirector()
        self.memory_lifecycle = MemoryLifecycleManager()
        self.event_store = event_store
        self.replay_service = ReplayService()
        self.eval_metrics_service = EvalMetricsService()
        self._snapshot_store: GameSnapshotStore | None = None
        self._refresh_runtime_limits()
        self.restore_persisted_games()

    def _get_handler(self, game: GameState) -> Optional[PhaseHandler]:
        handler_cls = PHASE_HANDLERS.get(game.phase)
        if handler_cls:
            return handler_cls(self, game)
        return None

    def _get_snapshot_store(self) -> GameSnapshotStore:
        snapshot_dir = Path(get_server_config().snapshot_dir).expanduser()
        if self._snapshot_store is None or self._snapshot_store.base_dir != snapshot_dir:
            self._snapshot_store = GameSnapshotStore(snapshot_dir)
        return self._snapshot_store

    def _refresh_runtime_limits(self) -> None:
        server_config = get_server_config()
        self.max_games = max(1, server_config.max_games)
        self.game_ttl = max(60, server_config.game_expire_time)

    def persistence_enabled(self) -> bool:
        return get_server_config().persist_games

    def persistence_ready(self) -> bool:
        if not self.persistence_enabled():
            return True
        return self._get_snapshot_store().is_ready()

    def restore_persisted_games(self) -> int:
        self._refresh_runtime_limits()
        if not self.persistence_enabled():
            runtime_metrics.set_gauge(
                "active_games",
                len(self.games),
                help_text="Current number of active games in memory",
            )
            return 0

        restored = 0
        for record in self._get_snapshot_store().load_all():
            session_id = record.session_id
            self.games[session_id] = record.game_state
            self.game_timestamps[session_id] = record.last_activity_at or record.updated_at.timestamp()
            self.player_tokens[session_id] = record.player_token
            self.ai_locks[session_id] = asyncio.Lock()
            self.event_store.clear(session_id)
            self.event_store.append_many(record.to_domain_events())
            restored += 1

        runtime_metrics.set_gauge(
            "active_games",
            len(self.games),
            help_text="Current number of active games in memory",
        )
        return restored

    def reset_runtime_state(self, preserve_snapshots: bool = True) -> None:
        session_ids = list(self.games.keys())
        self.games.clear()
        self.game_timestamps.clear()
        self.player_tokens.clear()
        self.ai_locks.clear()
        for session_id in session_ids:
            self.event_store.clear(session_id)
            if not preserve_snapshots and self.persistence_enabled():
                self._get_snapshot_store().delete(session_id)
        runtime_metrics.set_gauge(
            "active_games",
            0,
            help_text="Current number of active games in memory",
        )

    def persist_all_games(self) -> int:
        persisted = 0
        for game in self.games.values():
            persisted += int(self._persist_game_snapshot(game))
        return persisted

    def run_maintenance(self) -> None:
        self._refresh_runtime_limits()
        self._cleanup_old_games()
        self.persist_all_games()
        runtime_metrics.set_gauge(
            "active_games",
            len(self.games),
            help_text="Current number of active games in memory",
        )

    def create_game(self) -> GameState:
        self._refresh_runtime_limits()
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
        self.player_tokens[session_id] = generate_access_token()
        self.ai_locks[session_id] = asyncio.Lock()

        handler = self._get_handler(game_state)
        log_start = len(game_state.game_logs)
        if handler:
            handler.on_enter()

        self._roll_memory_for_phase_change(game_state)
        self._record_domain_event_nowait(game_created(game_state))
        self._record_new_logs_nowait(game_state, log_start)
        self._persist_game_snapshot(game_state)
        runtime_metrics.record_business_counter(
            "game_sessions_created_total",
            help_text="Total number of created game sessions",
        )
        runtime_metrics.set_gauge(
            "active_games",
            len(self.games),
            help_text="Current number of active games in memory",
        )
        logger.info(f"Created new game {session_id}. Total active games: {len(self.games)}")
        return game_state

    def get_game(self, session_id: str) -> Optional[GameState]:
        game = self.games.get(session_id)
        if game is not None:
            self.game_timestamps[session_id] = time.time()
        return game

    def get_player_token(self, session_id: str) -> Optional[str]:
        return self.player_tokens.get(session_id)

    def authenticate_player(self, session_id: str, player_token: str | None) -> Optional[int]:
        if not player_token:
            return None
        game = self.games.get(session_id)
        if not game:
            return None
        expected_token = self.player_tokens.get(session_id)
        if not expected_token or player_token != expected_token:
            return None
        human_player = next((player for player in game.players if player.is_human), None)
        return human_player.id if human_player else None

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
            self._record_player_action_metric(action, "unknown", "missing_game")
            return False, "游戏不存在或已结束"

        player = next((p for p in game.players if p.id == action.player_id), None)
        if not player:
            logger.warning(f"Invalid player_id {action.player_id} in game {session_id}")
            self._record_player_action_metric(action, "unknown", "invalid_player")
            return False, "无效的玩家"

        source = "human" if player.is_human else "ai"

        # Validate player is alive (with exceptions for death-phase actions)
        if not player.is_alive:
            if game.phase == GamePhase.HUNTER_SKILL and action.type in (ActionType.SHOOT, ActionType.PASS):
                pass
            elif game.phase == GamePhase.SHERIFF_TRANSFER and action.type == ActionType.VOTE:
                pass
            elif action.type == ActionType.PASS:
                pass
            else:
                logger.warning(f"Dead player {action.player_id} attempted action {action.type}")
                self._record_player_action_metric(action, source, "dead_player")
                return False, "你已死亡，无法执行此操作"

        # Validate speech content length
        if action.content and len(action.content) > MAX_SPEECH_LENGTH:
            self._record_player_action_metric(action, source, "speech_too_long")
            return False, f"发言内容过长，最多{MAX_SPEECH_LENGTH}字"

        try:
            self.phase_director.validate(
                GameSnapshot.from_game_state(game),
                PlayerCommand.from_action(
                    game_id=session_id,
                    phase=game.phase,
                    action=action,
                    source=source,
                ),
            )
        except PhaseValidationError as exc:
            logger.warning(
                "PhaseDirector rejected %s from player %s in %s: %s",
                action.type,
                player.id,
                game.phase,
                exc,
            )
            self._record_player_action_metric(action, source, "phase_rejected")
            return False, str(exc)

        handler = self._get_handler(game)
        if not handler:
            logger.error(f"No handler found for phase {game.phase}")
            self._record_player_action_metric(action, source, "missing_handler")
            return False, "当前阶段无法处理操作"

        log_start = len(game.game_logs)
        success = handler.process_action(action)
        if not success:
            phase_name = PHASE_DISPLAY_NAMES.get(game.phase, str(game.phase))
            action_name = ACTION_DISPLAY_NAMES.get(action.type, str(action.type))
            logger.warning(
                f"Handler {handler.__class__.__name__} rejected {action.type} "
                f"from player {action.player_id} in phase {game.phase}"
            )
            self._record_player_action_metric(action, source, "handler_rejected")
            return False, f"当前是{phase_name}，无法执行{action_name}操作"

        self.game_timestamps[session_id] = time.time()
        self._record_player_action_metric(action, source, "accepted")

        await self._record_domain_event(
            player_action_received(
                game,
                actor_id=player.id,
                action_type=action.type,
                target_id=action.target_id,
                source=source,
            )
        )
        await self._record_new_logs(game, log_start)

        # Check if phase should advance
        next_phase = handler.try_advance()
        if next_phase:
            await self._advance_phase(game, next_phase)
        else:
            self._persist_game_snapshot(game)
            asyncio.create_task(self.trigger_ai_actions(session_id))

        return True, ""

    async def _advance_phase(self, game: GameState, next_phase: GamePhase):
        logger.info(f"Advancing phase from {game.phase} to {next_phase}")

        previous_phase = game.phase
        game.phase = next_phase
        game.time_remaining = self.judge_system.get_time_limit(next_phase)
        self.game_timestamps[game.session_id] = time.time()
        self._roll_memory_for_phase_change(game)
        await self._record_domain_event(phase_entered(game, previous_phase))

        handler = self._get_handler(game)
        if handler:
            log_start = len(game.game_logs)
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
                await event_manager.publish(
                    JudgeBroadcastEvent(
                        content=broadcast_content,
                        type=broadcast_type,
                        session_id=game.session_id,
                    )
                )

            await event_manager.publish(
                PhaseChangeEvent(phase=next_phase, day=game.day, session_id=game.session_id)
            )

            handler.on_enter()
            await self._record_new_logs(game, log_start)
            self._persist_game_snapshot(game)

            auto_next = handler.try_advance()
            if auto_next:
                await self._advance_phase(game, auto_next)
            else:
                asyncio.create_task(self.trigger_ai_actions(game.session_id))

    def _cleanup_old_games(self):
        """Remove expired games and enforce max game limit"""
        self._refresh_runtime_limits()
        current_time = time.time()
        expired = [sid for sid, t in self.game_timestamps.items() if current_time - t > self.game_ttl]

        for sid in expired:
            del self.games[sid]
            del self.game_timestamps[sid]
            self.player_tokens.pop(sid, None)
            self.ai_locks.pop(sid, None)
            self.event_store.clear(sid)
            if self.persistence_enabled():
                self._get_snapshot_store().delete(sid)
            logger.info(f"Cleaned up expired game {sid}")

        if len(self.games) >= self.max_games:
            sorted_games = sorted(self.game_timestamps.items(), key=lambda x: x[1])
            to_remove = len(self.games) - self.max_games + 1
            for sid, _ in sorted_games[:to_remove]:
                del self.games[sid]
                del self.game_timestamps[sid]
                self.player_tokens.pop(sid, None)
                self.ai_locks.pop(sid, None)
                self.event_store.clear(sid)
                if self.persistence_enabled():
                    self._get_snapshot_store().delete(sid)
                logger.warning(f"Removed game {sid} due to max games limit")

        runtime_metrics.set_gauge(
            "active_games",
            len(self.games),
            help_text="Current number of active games in memory",
        )

    async def trigger_ai_actions(self, session_id: str):
        """Check if any AI players need to act and trigger them."""
        lock = self.ai_locks.setdefault(session_id, asyncio.Lock())
        async with lock:
            game = self.games.get(session_id)
            if not game:
                return

            pending_ais = self._get_pending_ai_players(game)
            if not pending_ais:
                return

            ai_player = pending_ais[0]
            agent = AIAgent(ai_player)
            logger.debug("Triggering AI player %s for phase %s", ai_player.id, game.phase)

            fallback_used = False
            issues: list[str] = []
            action_type = ActionType.PASS.value
            decision_phase = game.phase

            try:
                action_request = await agent.decide_action(game)
                action_type = action_request.type.value
                logger.debug("AI player %s produced action in phase %s", ai_player.id, game.phase)
                success, error_msg = await self.process_action(session_id, action_request)
                if not success:
                    fallback_used = True
                    if error_msg:
                        issues.append(error_msg)
                    fallback = self._get_fallback_action(game, ai_player)
                    action_type = fallback.type.value
                    logger.debug("AI player %s fallback action in phase %s", ai_player.id, game.phase)
                    success, fallback_error = await self.process_action(session_id, fallback)
                    if not success:
                        if fallback_error:
                            issues.append(fallback_error)
                        ai_player.has_acted = True
                        self._persist_game_snapshot(game)
                        handler = self._get_handler(game)
                        if handler:
                            next_phase = handler.try_advance()
                            if next_phase:
                                await self._advance_phase(game, next_phase)
                            else:
                                asyncio.create_task(self.trigger_ai_actions(session_id))
            except Exception as e:
                fallback_used = True
                issues.append(str(e))
                logger.error("AI player %s failed in phase %s: %s", ai_player.id, game.phase, e, exc_info=True)
                try:
                    fallback = self._get_fallback_action(game, ai_player)
                    action_type = fallback.type.value
                    logger.debug("Using fallback action for AI player %s in phase %s", ai_player.id, game.phase)
                    success, fallback_error = await self.process_action(session_id, fallback)
                    if not success:
                        if fallback_error:
                            issues.append(fallback_error)
                        ai_player.has_acted = True
                        self._persist_game_snapshot(game)
                except Exception as fallback_err:
                    logger.error("Fallback also failed for AI player %s: %s", ai_player.id, fallback_err)
                    issues.append(str(fallback_err))
                    ai_player.has_acted = True
                    self._persist_game_snapshot(game)
                handler = self._get_handler(game)
                if handler:
                    next_phase = handler.try_advance()
                    if next_phase:
                        await self._advance_phase(game, next_phase)
                    else:
                        asyncio.create_task(self.trigger_ai_actions(session_id))
            finally:
                trace = getattr(agent, "last_decision_trace", {})
                if trace.get("issues"):
                    issues.extend(str(issue) for issue in trace["issues"])
                runtime_metrics.record_business_counter(
                    "ai_decisions_total",
                    labels={"fallback_used": str(fallback_used or bool(trace.get("fallback_used"))).lower()},
                    help_text="Total number of AI decisions by fallback status",
                )
                await self._record_domain_event(
                    ai_decision_recorded(
                        game,
                        actor_id=ai_player.id,
                        model=trace.get("model", agent.model),
                        phase=decision_phase,
                        action_type=trace.get("action_type", action_type),
                        fallback_used=fallback_used or bool(trace.get("fallback_used")),
                        issues=list(dict.fromkeys(issues)),
                    )
                )

    def _get_pending_ai_players(self, game: GameState) -> List[Player]:
        """Identify AI players that need to act in the current phase."""
        pending = []

        if game.phase in {GamePhase.DAY_DISCUSS, GamePhase.SHERIFF_SPEECH, GamePhase.DAY_PK_SPEECH}:
            current_speaker_id = None
            if game.speaking_order and game.current_speaker_index < len(game.speaking_order):
                current_speaker_id = game.speaking_order[game.current_speaker_index]
            if current_speaker_id is None:
                return pending
            player = next((p for p in game.players if p.id == current_speaker_id), None)
            if (
                player
                and not player.is_human
                and not player.has_acted
                and (player.is_alive or game.phase == GamePhase.DAY_PK_SPEECH)
            ):
                return [player]
            return pending

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
                from app.core.rules import Rules
                alive_wolves = len([
                    wolf for wolf in game.players
                    if wolf.is_alive and wolf.role in (Role.WOLF, Role.WOLF_KING)
                ])
                if (
                    not p.is_human
                    and not p.is_alive
                    and p.role in (Role.HUNTER, Role.WOLF_KING)
                    and not p.gun_used
                    and Rules.can_shoot(p, p.death_cause, alive_wolves=alive_wolves)
                ):
                    pending.append(p)
                continue

            # Special: sheriff transfer - dead sheriff must hand over or tear badge
            if game.phase == GamePhase.SHERIFF_TRANSFER:
                if not p.is_human and not p.is_alive and p.is_sheriff and not p.has_acted:
                    pending.append(p)
                continue

            # Normal phases: only alive AI players
            if p.is_human or not p.is_alive:
                continue

            rule = PHASE_ACTOR_RULES.get(game.phase)
            if rule and rule(p, game):
                pending.append(p)

        return pending

    def _roll_memory_for_phase_change(self, game: GameState) -> None:
        for player in game.players:
            if player.is_human:
                continue
            plan = self.memory_lifecycle.build_plan_from_player(player, game)
            player.ai_memory = self.memory_lifecycle.apply_legacy_rollover(player.ai_memory, plan)

    def get_domain_events(self, session_id: str):
        return self.event_store.by_session(session_id)

    def get_replay_timeline(self, session_id: str):
        return self.replay_service.build_timeline(session_id, self.get_domain_events(session_id))

    def get_eval_report(self, session_id: str):
        return self.eval_metrics_service.build_report(session_id, self.get_domain_events(session_id))

    async def _record_domain_event(self, event) -> None:
        runtime_metrics.record_business_counter(
            "domain_events_total",
            labels={"event_name": event.name, "visibility": event.visibility.value},
            help_text="Total number of emitted domain events",
        )
        self.event_store.append(event)
        await event_manager.publish(event)

    def _record_domain_event_nowait(self, event) -> None:
        runtime_metrics.record_business_counter(
            "domain_events_total",
            labels={"event_name": event.name, "visibility": event.visibility.value},
            help_text="Total number of emitted domain events",
        )
        self.event_store.append(event)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(event_manager.publish(event))

    async def _record_new_logs(self, game: GameState, start_index: int) -> None:
        for log in game.game_logs[start_index:]:
            await self._record_domain_event(game_log_recorded(game, log))

    def _record_new_logs_nowait(self, game: GameState, start_index: int) -> None:
        for log in game.game_logs[start_index:]:
            self._record_domain_event_nowait(game_log_recorded(game, log))

    def _get_fallback_action(self, game: GameState, player: Player) -> ActionRequest:
        alive_players = [p for p in game.players if p.is_alive]
        other_alive_players = [p for p in alive_players if p.id != player.id]
        wolf_targets = [p for p in alive_players]

        if game.phase == GamePhase.SHERIFF_ELECTION:
            return ActionRequest(player_id=player.id, type=ActionType.PASS)
        if game.phase == GamePhase.SHERIFF_SPEECH:
            if player.id in game.sheriff_candidate_ids:
                return ActionRequest(player_id=player.id, type=ActionType.PASS)
            return ActionRequest(player_id=player.id, type=ActionType.CONFIRM)
        if game.phase == GamePhase.SHERIFF_VOTE:
            candidates = list(game.sheriff_candidate_ids)
            target_id = candidates[0] if candidates else 0
            return ActionRequest(player_id=player.id, type=ActionType.VOTE, target_id=target_id)
        if game.phase == GamePhase.NIGHT_WOLF_VOTE:
            target_id = random.choice(wolf_targets).id if wolf_targets else game.players[0].id
            return ActionRequest(player_id=player.id, type=ActionType.KILL, target_id=target_id)
        if game.phase == GamePhase.NIGHT_SEER:
            targets = other_alive_players or alive_players
            target_id = random.choice(targets).id if targets else None
            return ActionRequest(player_id=player.id, type=ActionType.CHECK, target_id=target_id)
        if game.phase == GamePhase.NIGHT_WITCH:
            if game.wolf_kill_target and not player.antidote_used:
                return ActionRequest(player_id=player.id, type=ActionType.SAVE)
            if not player.poison_used:
                targets = other_alive_players or alive_players
                if targets:
                    return ActionRequest(player_id=player.id, type=ActionType.POISON, target_id=random.choice(targets).id)
            return ActionRequest(player_id=player.id, type=ActionType.PASS)
        if game.phase == GamePhase.NIGHT_GUARD:
            targets = [p for p in alive_players if p.id != game.last_guarded_player]
            target_id = random.choice(targets).id if targets else None
            if target_id is not None:
                return ActionRequest(player_id=player.id, type=ActionType.GUARD, target_id=target_id)
            return ActionRequest(player_id=player.id, type=ActionType.PASS)
        if game.phase in (GamePhase.DAY_VOTE, GamePhase.DAY_PK_VOTE):
            vote_targets = [
                p for p in alive_players
                if game.phase != GamePhase.DAY_PK_VOTE or p.id in game.pk_candidates
            ]
            if game.phase == GamePhase.DAY_PK_VOTE and player.id in game.pk_candidates:
                return ActionRequest(player_id=player.id, type=ActionType.CONFIRM)
            target_id = random.choice(vote_targets).id if vote_targets else 0
            return ActionRequest(player_id=player.id, type=ActionType.VOTE, target_id=target_id)
        if game.phase == GamePhase.HUNTER_SKILL:
            targets = other_alive_players or alive_players
            target_id = random.choice(targets).id if targets else None
            if target_id is not None:
                return ActionRequest(player_id=player.id, type=ActionType.SHOOT, target_id=target_id)
        return ActionRequest(player_id=player.id, type=ActionType.PASS)

    def _persist_game_snapshot(self, game: GameState) -> bool:
        if not self.persistence_enabled():
            return False

        player_token = self.player_tokens.get(game.session_id)
        if not player_token:
            return False

        self._get_snapshot_store().save(
            game,
            player_token,
            updated_at=datetime.now(timezone.utc),
            last_activity_at=self.game_timestamps.get(game.session_id, time.time()),
            domain_events=self.get_domain_events(game.session_id),
        )
        return True

    def _record_player_action_metric(self, action: ActionRequest, source: str, result: str) -> None:
        runtime_metrics.record_business_counter(
            "player_actions_total",
            labels={
                "action_type": action.type.value,
                "source": source,
                "result": result,
            },
            help_text="Total number of processed player actions by outcome",
        )


game_manager = GameManager()
