import uuid
import random
import time
import logging
import asyncio
from typing import List, Dict, Optional
from app.models.game_state import GameState, GamePhase, Player, Role, GameLog, ActionType
from app.models.action_model import ActionRequest

# Handlers
from app.core.phase_handler import PhaseHandler
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

from app.core.judge import JudgeSystem
from app.core.event_manager import event_manager
from app.models.events import PhaseChangeEvent, JudgeBroadcastEvent, GameEndEvent

class GameManager:
    def __init__(self):
        self.games: Dict[str, GameState] = {}
        self.game_timestamps: Dict[str, float] = {}  # Track game creation time
        self.max_games = 100  # Maximum number of concurrent games
        self.game_ttl = 3600 * 24  # Games expire after 24 hours
        self.judge_system = JudgeSystem()
        
        # Initialize handlers map
        self.handlers: Dict[GamePhase, type] = {
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

    def _get_handler(self, game: GameState) -> Optional[PhaseHandler]:
        handler_cls = self.handlers.get(game.phase)
        if handler_cls:
            return handler_cls(self, game)
        return None

    def create_game(self) -> GameState:
        # Clean up old games before creating new one
        self._cleanup_old_games()

        session_id = str(uuid.uuid4())
        
        # Initialize 12 players
        players = self._init_players(session_id)
        
        game_state = GameState(
            session_id=session_id,
            day=1,
            phase=GamePhase.GAME_START,
            players=players,
            time_remaining=60
        )
        
        self.games[session_id] = game_state
        self.game_timestamps[session_id] = time.time()
        
        # Trigger initial phase logic
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
            Role.SEER, Role.WITCH, Role.GUARD, Role.HUNTER
        ]
        random.shuffle(roles)
        
        players = []
        for i, role in enumerate(roles):
            # Player 1 is human for now
            is_human = (i == 0)
            
            # Determine portrait filename (匹配前端资源)
            portrait_map = {
                Role.VILLAGER: "/images/portraits/村民.jpg",
                Role.WOLF: "/images/portraits/狼人.png",
                Role.WOLF_KING: "/images/portraits/狼王.png",
                Role.SEER: "/images/portraits/预言家.jpg",
                Role.WITCH: "/images/portraits/女巫.png",
                Role.GUARD: "/images/portraits/守卫.png",
                Role.HUNTER: "/images/portraits/猎人.png"
            }
            portrait = portrait_map.get(role, "/images/portraits/村民.jpg")
            
            player = Player(
                id=i + 1,
                name=f"{i + 1}号玩家",
                role=role,
                portrait=portrait,
                is_human=is_human
            )
            
            # Initialize AI memory with metadata if it's an AI
            if not is_human:
                # We need to create a temporary MemoryManager to init metadata and save it to player
                # This is a bit hacky but ensures persistence from the start
                from app.ai.memory.memory_manager import MemoryManager
                mm = MemoryManager(player)
                mm.init_metadata(
                    session_id=session_id,
                    game_config={
                        "player_count": 12,
                        "wolf_count": 4,
                        "roles": [r.value for r in roles]
                    }
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

        # Validate player_id
        player = next((p for p in game.players if p.id == action.player_id), None)
        if not player:
            logger.warning(f"Invalid player_id {action.player_id} in game {session_id}")
            return False, "无效的玩家"

        # Validate player is alive (for most actions)
        # 特殊情况：HUNTER_SKILL阶段允许死亡的猎人/狼王开枪
        if not player.is_alive:
            if game.phase == GamePhase.HUNTER_SKILL and action.type in [ActionType.SHOOT, ActionType.PASS]:
                # 允许死亡的猎人/狼王在技能阶段行动
                pass
            elif action.type == ActionType.PASS:
                # PASS action is always allowed
                pass
            else:
                logger.warning(f"Dead player {action.player_id} attempted action {action.type}")
                return False, "你已死亡，无法执行此操作"

        # Delegate to handler
        handler = self._get_handler(game)
        if not handler:
            logger.error(f"No handler found for phase {game.phase}")
            return False, "当前阶段无法处理操作"

        success = handler.process_action(action)
        if not success:
            phase_name = self._get_phase_display_name(game.phase)
            action_name = self._get_action_display_name(action.type)
            logger.warning(f"Handler {handler.__class__.__name__} rejected action {action.type} from player {action.player_id} in phase {game.phase}")
            return False, f"当前是{phase_name}，无法执行{action_name}操作"

        # 操作成功，检查是否需要推进阶段
        next_phase = handler.try_advance()
        if next_phase:
            await self._advance_phase(game, next_phase)
        else:
            # 阶段未变化，触发下一个AI行动（后台异步执行，不阻塞响应）
            asyncio.create_task(self.trigger_ai_actions(session_id))

        return True, ""

    def _get_phase_display_name(self, phase: GamePhase) -> str:
        mapping = {
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
        return mapping.get(phase, str(phase))

    def _get_action_display_name(self, action_type: ActionType) -> str:
        mapping = {
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
        return mapping.get(action_type, str(action_type))

    async def _advance_phase(self, game: GameState, next_phase: GamePhase):
        logger.info(f"Advancing phase from {game.phase} to {next_phase}")
        
        game.phase = next_phase
        game.time_remaining = self.judge_system.get_time_limit(next_phase)
        
        # Trigger new phase logic
        handler = self._get_handler(game)
        if handler:
            # Generate broadcast
            broadcast_type = self._get_broadcast_type(next_phase)
            if broadcast_type:
                broadcast_content = self.judge_system.generate_broadcast(broadcast_type)
                # Log broadcast
                game.game_logs.append(GameLog(
                    id=str(uuid.uuid4()),
                    day=game.day,
                    phase=game.phase,
                    player_id=0, # System
                    content=broadcast_content,
                    type="broadcast"
                ))
                
                # Publish Judge Broadcast Event
                await event_manager.publish(JudgeBroadcastEvent(content=broadcast_content, type=broadcast_type))
            
            # Publish Phase Change Event
            await event_manager.publish(PhaseChangeEvent(phase=next_phase, day=game.day))
            
            handler.on_enter()
            
            # Check if we should immediately advance again
            auto_next = handler.try_advance()
            if auto_next:
                await self._advance_phase(game, auto_next)
            else:
                # New phase started, trigger AI（后台异步执行，不阻塞响应）
                asyncio.create_task(self.trigger_ai_actions(game.session_id))

    def _get_broadcast_type(self, phase: GamePhase) -> Optional[str]:
        mapping = {
            GamePhase.NIGHT_START: "night_start",
            GamePhase.DAY_START: "day_start",
            GamePhase.SHERIFF_ELECTION: "sheriff_election",
            GamePhase.DAY_VOTE: "vote_start",
        }
        return mapping.get(phase)

    def _cleanup_old_games(self):
        """Remove expired games and enforce max game limit"""
        current_time = time.time()
        expired_games = []

        # Find expired games
        for session_id, created_time in self.game_timestamps.items():
            if current_time - created_time > self.game_ttl:
                expired_games.append(session_id)

        # Remove expired games
        for session_id in expired_games:
            del self.games[session_id]
            del self.game_timestamps[session_id]
            logger.info(f"Cleaned up expired game {session_id}")

        # If still over limit, remove oldest games
        if len(self.games) >= self.max_games:
            # Sort by creation time and remove oldest
            sorted_games = sorted(self.game_timestamps.items(), key=lambda x: x[1])
            games_to_remove = len(self.games) - self.max_games + 1

            for session_id, _ in sorted_games[:games_to_remove]:
                del self.games[session_id]
                del self.game_timestamps[session_id]
                logger.warning(f"Removed game {session_id} due to max games limit")

    async def trigger_ai_actions(self, session_id: str):
        """
        Check if any AI players need to act in the current phase and trigger them.
        This should be called after phase transitions or actions.
        """
        game = self.games.get(session_id)
        if not game:
            return

        # 1. Identify who needs to act
        # This logic depends on the phase. 
        # Ideally, PhaseHandler should tell us "who is pending action".
        # For now, we iterate and check basic conditions.
        
        pending_ais = []
        for p in game.players:
            # 遗言阶段特殊处理：只有死亡的AI玩家可以发言
            if game.phase == GamePhase.DAY_LAST_WORDS:
                if p.is_human:
                    continue
                if p.id not in game.dead_players:
                    continue
                if p.has_acted:
                    continue
                pending_ais.append(p)
                continue

            # 猎人/狼王技能阶段特殊处理：死亡的猎人/狼王可以开枪
            if game.phase == GamePhase.HUNTER_SKILL:
                if p.is_human:
                    continue
                if p.is_alive:  # 只有死亡的玩家可以在此阶段行动
                    continue
                if p.role not in [Role.HUNTER, Role.WOLF_KING]:
                    continue
                if p.gun_used or p.poisoned_by_witch:  # 已经用过枪或被毒死无法开枪
                    continue
                if p.has_acted:
                    continue
                pending_ais.append(p)
                continue

            # 其他阶段：只有活着的AI玩家可以行动
            if p.is_human or not p.is_alive:
                continue

            # Check if they have already acted
            if p.has_acted:
                continue

            # Check if it's their turn based on phase
            should_act = False
            if game.phase == GamePhase.NIGHT_WOLF_DISCUSS and p.role in [Role.WOLF, Role.WOLF_KING]:
                should_act = True
            elif game.phase == GamePhase.NIGHT_WOLF_VOTE and p.role in [Role.WOLF, Role.WOLF_KING]:
                should_act = True
            elif game.phase == GamePhase.NIGHT_SEER and p.role == Role.SEER:
                should_act = True
            elif game.phase == GamePhase.NIGHT_WITCH and p.role == Role.WITCH:
                should_act = True
            elif game.phase == GamePhase.NIGHT_GUARD and p.role == Role.GUARD:
                should_act = True
            elif game.phase == GamePhase.DAY_DISCUSS:
                # In discuss, we might want to limit concurrent speakers or order them
                # For MVP, let's just pick one random pending AI to avoid chaos
                should_act = True
            elif game.phase == GamePhase.DAY_VOTE:
                should_act = True
            elif game.phase == GamePhase.SHERIFF_ELECTION:
                should_act = True
            elif game.phase == GamePhase.SHERIFF_SPEECH:
                should_act = p.id in game.sheriff_candidate_ids
            elif game.phase == GamePhase.SHERIFF_VOTE:
                should_act = True
            elif game.phase == GamePhase.GAME_START:
                should_act = True # To confirm

            if should_act:
                pending_ais.append(p)

        if not pending_ais:
            return

        # 2. Execute AI actions
        # For sequential phases (like Day Discuss), pick one. For parallel (Vote), maybe all?
        # To keep it simple and safe, we'll process one AI at a time for now, 
        # or maybe a small batch.
        
        # Let's pick the first one for now to avoid race conditions in state updates
        ai_player = pending_ais[0]
        
        # Import here to avoid circular dependency if possible, or move AIAgent import to top if safe
        from app.ai.agent import AIAgent
        
        agent = AIAgent(ai_player)
        logger.info(f"Triggering AI {ai_player.id} ({ai_player.role}) for phase {game.phase}")
        
        try:
            action_request = await agent.decide_action(game)
            logger.info(f"AI {ai_player.id} decided: {action_request}")

            # Submit action back to GameManager
            success, _ = await self.process_action(session_id, action_request)
            
        except Exception as e:
            logger.error(f"Error executing AI {ai_player.id}: {e}")
            fallback = self._get_fallback_action(game, ai_player)
            success, _ = await self.process_action(session_id, fallback)
            if not success:
                ai_player.has_acted = True

    def _get_fallback_action(self, game: GameState, player: Player) -> ActionRequest:
        if game.phase == GamePhase.NIGHT_WOLF_VOTE:
            targets = [p for p in game.players if p.is_alive and p.role not in [Role.WOLF, Role.WOLF_KING]]
            target_id = random.choice(targets).id if targets else game.players[0].id
            return ActionRequest(player_id=player.id, type=ActionType.KILL, target_id=target_id)
        return ActionRequest(player_id=player.id, type=ActionType.PASS)

game_manager = GameManager()
