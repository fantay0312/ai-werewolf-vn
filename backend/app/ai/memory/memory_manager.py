import logging
from typing import Dict, Optional, Any
from app.models.game_state import GameState, GamePhase, Role, Player
from app.ai.memory.fact_layer import FactLayer, SkillStatus, DeathRecord, CheckResult
from app.ai.memory.summary_layer import SummaryLayer, PlayerProfile, DailySummary
from app.ai.memory.recent_layer import RecentLayer, DialogueEntry
from app.core.rules import Rules
from app.ai.utils.token_utils import count_tokens, truncate_to_token_limit
from app.ai.memory.metadata_layer import MetadataLayer, SessionContext, GameConfig
import datetime

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self, player: Player):
        self.player_id = player.id
        self.metadata_layer: Optional[MetadataLayer] = None
        self.fact_layer: Optional[FactLayer] = None
        self.summary_layer = SummaryLayer()
        self.recent_layer = RecentLayer()
        self.last_log_index = 0
        
        # Load memory if exists
        if player.ai_memory:
            try:
                if "metadata_layer" in player.ai_memory:
                    self.metadata_layer = MetadataLayer(**player.ai_memory["metadata_layer"])
                self.summary_layer = SummaryLayer(**player.ai_memory.get("summary_layer", {}))
                self.recent_layer = RecentLayer(**player.ai_memory.get("recent_layer", {}))
                self.last_log_index = player.ai_memory.get("last_log_index", 0)
                logger.info(f"Loaded memory for player {self.player_id}")
            except Exception as e:
                logger.error(f"Failed to load memory for player {self.player_id}: {e}")
                
    def init_metadata(self, session_id: str, game_config: dict):
        """Initialize metadata layer (Layer 1)"""
        self.metadata_layer = MetadataLayer(
            session_context=SessionContext(
                session_id=session_id,
                start_time=datetime.datetime.now().isoformat(),
                game_config=GameConfig(**game_config)
            )
        )
        
    def save_to_player(self, player: Player):
        """Persist current memory state to player object"""
        player.ai_memory = {
            "metadata_layer": self.metadata_layer.model_dump() if self.metadata_layer else None,
            "summary_layer": self.summary_layer.model_dump() if hasattr(self.summary_layer, 'model_dump') else self.summary_layer.dict(),
            "recent_layer": self.recent_layer.model_dump() if hasattr(self.recent_layer, 'model_dump') else self.recent_layer.dict(),
            "last_log_index": self.last_log_index
        }

    def update_facts(self, game_state: GameState):
        """Re-generate FactLayer from GameState every time"""
        my_player = next(p for p in game_state.players if p.id == self.player_id)
        
        # Confirmed Info
        confirmed_actions = []
        for log in game_state.game_logs:
            if log.data and "action" in log.data:
                # Filter what is confirmed/public or known to me
                # For now, let's include all structured actions that are public or my own
                is_public = log.is_public
                is_mine = log.player_id == self.player_id
                
                if is_public or is_mine:
                    from app.ai.memory.fact_layer import ConfirmedAction
                    confirmed_actions.append(ConfirmedAction(
                        day=log.day,
                        phase=log.phase,
                        action_type=log.data["action"],
                        actor_id=log.player_id if log.player_id else 0,
                        target_id=log.data.get("target_id"),
                        result=log.data.get("result")
                    ))

        # Determine camp
        my_camp = "wolf" if my_player.role in [Role.WOLF, Role.WOLF_KING] else "good"
        
        # Wolf teammates
        wolf_teammates = []
        if my_camp == "wolf":
            wolf_teammates = [p.id for p in game_state.players if p.role in [Role.WOLF, Role.WOLF_KING] and p.id != self.player_id]
            
        # Track full alive/dead lists so prompts don't talk about eliminated players
        alive_players = sorted([p.id for p in game_state.players if p.is_alive])
        dead_records = []
        for player in game_state.players:
            if not player.is_alive:
                dead_records.append(DeathRecord(
                    player_id=player.id,
                    day=game_state.day,
                    phase=game_state.phase,
                    cause="unknown"
                ))
             
        # Skill Status
        skill_status = SkillStatus()
        if my_player.role == Role.WITCH:
            skill_status.has_antidote = not my_player.antidote_used
            skill_status.has_poison = not my_player.poison_used
        elif my_player.role == Role.GUARD:
            skill_status.last_guard_target = game_state.last_guarded_player
        elif my_player.role == Role.SEER:
            # Load check results from logs
            for log in game_state.game_logs:
                if log.phase == GamePhase.NIGHT_SEER and log.data and log.data.get("action") == "seer_check":
                    # Only include if it's my check (though log.player_id should match)
                    if log.player_id == self.player_id:
                        skill_status.check_results.append(CheckResult(
                            day=log.day,
                            target_id=log.data["target_id"],
                            result=log.data["result"]
                        ))
        elif my_player.role in [Role.HUNTER, Role.WOLF_KING]:
            skill_status.can_shoot = Rules.can_shoot(my_player, "unknown")
            
        self.fact_layer = FactLayer(
            game_id=game_state.session_id,
            current_day=game_state.day,
            current_phase=game_state.phase,
            my_player_id=self.player_id,
            my_role=my_player.role,
            my_camp=my_camp,
            wolf_teammates=wolf_teammates,
            alive_players=alive_players,
            dead_players=dead_records,
            sheriff_id=game_state.sheriff_id,
            sheriff_candidates=game_state.sheriff_candidate_ids,
            skill_status=skill_status,
            confirmed_actions=confirmed_actions
        )
        
        # Initialize profiles if empty
        if not self.summary_layer.player_profiles:
            for p in game_state.players:
                if p.id != self.player_id:
                    self.summary_layer.player_profiles.append(PlayerProfile(player_id=p.id))
                    
        # Save state back to player (to persist updates)
        self.save_to_player(my_player)
        
        # Process new logs for analysis
        self._process_new_logs(game_state)

    def _process_new_logs(self, game_state: GameState):
        """Process new logs to update player profiles"""
        start_index = self.last_log_index
        new_logs = game_state.game_logs[start_index:]
        
        for log in new_logs:
            # Update voting patterns
            if log.phase == GamePhase.DAY_VOTE_RESULT and log.data and "votes" in log.data:
                votes = log.data["votes"]
                for voter_id_str, target_id in votes.items():
                    voter_id = int(voter_id_str)
                    
                    # Find profile
                    profile = next((p for p in self.summary_layer.player_profiles if p.player_id == voter_id), None)
                    if profile:
                        # Add vote record
                        from app.ai.memory.summary_layer import VoteRecord
                        profile.voting_pattern.append(VoteRecord(
                            day=log.day,
                            voted_for=target_id if target_id != 0 else None
                        ))
                        logger.info(f"Recorded vote for player {voter_id} in memory of {self.player_id}")

            # Update Recent Dialogue
            if log.player_id and log.player_id != 0 and log.content:
                # Check visibility: public or wolf chat (if I am wolf)
                is_visible = log.is_public
                if not is_visible:
                    # Check if it's wolf chat
                    if log.phase in [GamePhase.NIGHT_WOLF_DISCUSS, GamePhase.NIGHT_WOLF_VOTE] and self.fact_layer.my_camp == "wolf":
                        is_visible = True
                    # Check if it's my own private log (e.g. seer result) - usually not dialogue
                    if log.player_id == self.player_id:
                        is_visible = True # My own words/thoughts
                
                if is_visible:
                    # Add to recent layer
                    speaker_name = next((p.name for p in game_state.players if p.id == log.player_id), str(log.player_id))
                    
                    # 对于狼人讨论消息，提取实际内容（去掉"X号(狼人): "前缀）
                    content = log.content
                    if log.phase == GamePhase.NIGHT_WOLF_DISCUSS and log.type == "speech":
                        # 消息格式是 "{player_id}号(狼人): {content}"
                        # 提取实际内容部分
                        match = content.split(":", 1)
                        if len(match) == 2:
                            content = match[1].strip()
                    
                    entry = DialogueEntry(
                        speaker_id=log.player_id,
                        speaker_name=speaker_name,
                        content=content,
                        timestamp=0,
                        phase=log.phase,
                        day=log.day
                    )
                    self.add_dialogue(entry)

        self.last_log_index = len(game_state.game_logs)
        
        # Save again after processing
        my_player = next(p for p in game_state.players if p.id == self.player_id)
        self.save_to_player(my_player)

    def add_dialogue(self, entry: DialogueEntry):
        self.recent_layer.current_phase_dialogue.append(entry)
        self._check_token_limit()

    def end_phase(self):
        """Move current dialogue to previous, summarize if needed"""
        # Move current to previous
        if self.recent_layer.current_phase_dialogue:
            self.recent_layer.previous_phase_dialogue = self.recent_layer.current_phase_dialogue
            self.recent_layer.current_phase_dialogue = []
        
        # Trigger compression/summarization
        self._compress_memory()

    async def maintain_memory(self, client: Any, model: str):
        """Check memory status and perform LLM-based maintenance if needed"""
        # Check if we have previous dialogue to summarize
        if self.recent_layer.previous_phase_dialogue:
            text = "".join([f"{d.speaker_id}:{d.content}\n" for d in self.recent_layer.previous_phase_dialogue])
            if count_tokens(text) > 500: # Threshold for summarization
                await self._generate_summary(client, model, self.recent_layer.previous_phase_dialogue)
                self.recent_layer.previous_phase_dialogue = [] # Clear after summary
                
    async def _generate_summary(self, client: Any, model: str, dialogues: list[DialogueEntry]):
        """Generate summary using LLM"""
        if not dialogues:
            return

        try:
            # Construct prompt
            text = "\n".join([f"{d.speaker_id}号({d.speaker_name}): {d.content}" for d in dialogues])
            phase = dialogues[0].phase
            day = dialogues[0].day
            
            prompt = f"""
            你是狼人杀游戏的记录员。请将以下{phase}阶段的对话压缩成简洁的摘要。
            
            【对话内容】
            {text}
            
            【要求】
            1. 生成一个简短的【标题】(Headline)，概括本阶段核心事件（如"3号跳预言家查杀5号"）。
            2. 提取3-5条【关键片段】(Snippets)，保留原话的重要部分。
            3. 生成一段【摘要】(Summary)，连贯地描述发生的事情。
            
            请以JSON格式输出：
            {{
                "headline": "标题",
                "snippets": ["片段1", "片段2"],
                "summary": "摘要内容"
            }}
            """
            
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            import json
            result = json.loads(response.choices[0].message.content)
            
            # Store summary
            daily = next((s for s in self.summary_layer.daily_summaries if s.day == day), None)
            if not daily:
                daily = DailySummary(day=day)
                self.summary_layer.daily_summaries.append(daily)
            
            daily.headline = result.get("headline", "")
            daily.snippets.extend(result.get("snippets", []))
            
            formatted_summary = f"[{phase}] {result.get('summary', '')}"
            if "NIGHT" in phase:
                daily.night_summary += formatted_summary + "\n"
            else:
                daily.day_summary += formatted_summary + "\n"
                
            logger.info(f"Generated summary for player {self.player_id}: {daily.headline}")
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            # Fallback to truncation
            pass

    def _check_token_limit(self):
        """Check if recent layer exceeds token limit (e.g. 2000 chars approx)"""
        # Simple heuristic limit
        LIMIT = 2000
        
        # Calculate size
        text = "".join([d.content for d in self.recent_layer.current_phase_dialogue])
        if count_tokens(text) > LIMIT:
            # If current is too long, we might need to truncate oldest
            # For now, just warn or drop oldest
            pass

    def _compress_memory(self):
        """Compress recent memory into summary"""
        # This is now handled by maintain_memory with LLM
        # But we keep this for non-LLM fallback or immediate cleanup
        pass
