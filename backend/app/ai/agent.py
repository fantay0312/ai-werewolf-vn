import os
import json
import logging
from typing import Optional, Dict, Any
from openai import AsyncOpenAI
from app.application.ai.action_guard import ActionGuard
from app.application.ai.actor_context_builder import ActorContextBuilder
from app.application.ai.prompt_contract import render_structured_context
from app.application.ai.response_parser import ResponseParser
from app.models.game_state import GameState, Player, Role, ActionType
from app.models.action_model import ActionRequest
from app.ai.memory.memory_manager import MemoryManager
from app.ai.prompt_builder import prompt_builder
from app.ai.personalities import get_personality, get_personality_prompt, get_role_personality_modifier
from app.config import get_llm_config

logger = logging.getLogger(__name__)


class AIAgent:
    def __init__(self, player: Player):
        self.player = player
        self.memory_manager = MemoryManager(player)
        self.context_builder = ActorContextBuilder()
        self.response_parser = ResponseParser()
        self.action_guard = ActionGuard()
        self.last_decision_trace: Dict[str, Any] = {}

        # 从配置获取LLM设置
        llm_config = get_llm_config()

        if not llm_config.api_key:
            logger.warning("LLM_API_KEY not set, AI agent will use fallback actions")
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=llm_config.api_key,
                base_url=llm_config.api_base
            )

        self.model = llm_config.model

        # Load personality based on player ID
        self.personality_config = get_personality(player.id)
        self.personality = self.personality_config.name

    async def decide_action(self, game_state: GameState) -> ActionRequest:
        # Update memory
        self.memory_manager.update_facts(game_state)
        
        # Maintain memory (summarize if needed)
        if self.client:
            await self.memory_manager.maintain_memory(self.client, self.model)
        
        # Build prompt
        structured_context = self.context_builder.build(game_state, self.player)
        system_prompt = prompt_builder.build_system_prompt()
        metadata_block = prompt_builder.build_metadata_block(self.memory_manager.metadata_layer)
        char_block = prompt_builder.build_character_block(self.player.id, self.player.role, self.personality)
        facts_block = prompt_builder.build_absolute_facts(self.memory_manager.fact_layer)
        summary_block = prompt_builder.build_history_summary(self.memory_manager.summary_layer)
        recent_block = prompt_builder.build_recent_dialogue(self.memory_manager.recent_layer)
        task_block = prompt_builder.build_current_task_block(self.memory_manager.fact_layer)
        contract_block = render_structured_context(structured_context)

        # Add personality traits
        personality_block = get_personality_prompt(self.personality_config)
        role_modifier = get_role_personality_modifier(self.player.role.value, self.personality_config)

        # Construct full prompt with personality
        full_user_prompt = f"{metadata_block}\n{char_block}\n{personality_block}\n{role_modifier}\n{facts_block}\n{summary_block}\n{recent_block}\n{task_block}\n{contract_block}\n请根据当前情况和你的性格特点做出决策。"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_user_prompt}
        ]

        # If client is not initialized, return fallback action
        if not self.client:
            logger.warning(f"AI client not initialized for player {self.player.id}, using fallback action")
            self.last_decision_trace = {
                "model": self.model,
                "action_type": ActionType.PASS.value,
                "issues": ["llm_client_not_initialized"],
                "fallback_used": True,
                "raw_response": None,
            }
            return ActionRequest(
                player_id=self.player.id,
                type=ActionType.PASS
            )

        # Initialize detector
        from app.ai.hallucination_detector import HallucinationDetector
        detector = HallucinationDetector()
        
        # Retry loop for hallucination handling
        max_retries = 3
        current_try = 0
        
        while current_try < max_retries:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"}
                )
    
                content = response.choices[0].message.content
                
                # Validate with detector
                detection = detector.detect(content, self.memory_manager.fact_layer, game_state)
                
                if detection.has_hallucination:
                    logger.warning(f"Hallucination detected for player {self.player.id}: {detection.issues}")
                    current_try += 1
                    self.last_decision_trace = {
                        "model": self.model,
                        "action_type": "invalid",
                        "issues": list(detection.issues),
                        "fallback_used": False,
                        "raw_response": content,
                    }
                    # Add feedback to prompt and retry
                    feedback = f"System: Your previous response had errors: {'; '.join(detection.issues)}. Please correct them and try again."
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": feedback})
                    continue

                parsed = self.response_parser.parse(content, phase=game_state.phase)
                if not parsed.is_valid or not parsed.action:
                    current_try += 1
                    issues = list(parsed.issues) or ["invalid_action_payload"]
                    self.last_decision_trace = {
                        "model": self.model,
                        "action_type": "invalid",
                        "issues": issues,
                        "fallback_used": False,
                        "raw_response": content,
                    }
                    feedback = f"System: Your previous response violated the structured response contract: {'; '.join(issues)}. Please output a corrected JSON action."
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": feedback})
                    continue

                action_request = parsed.action.to_action_request(self.player.id)
                guard_result = self.action_guard.validate(game_state, self.player, action_request)
                if not guard_result.allowed or guard_result.normalized_action is None:
                    current_try += 1
                    issues = list(guard_result.issues) or ["action_guard_rejected"]
                    self.last_decision_trace = {
                        "model": self.model,
                        "action_type": action_request.type.value,
                        "issues": issues,
                        "fallback_used": False,
                        "raw_response": content,
                    }
                    feedback = f"System: The proposed action violates the current action window: {'; '.join(issues)}. Please correct it."
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": feedback})
                    continue

                self.last_decision_trace = {
                    "model": self.model,
                    "action_type": guard_result.normalized_action.type.value,
                    "issues": [],
                    "fallback_used": False,
                    "raw_response": content,
                }
                return guard_result.normalized_action
    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response for player {self.player.id}: {e}")
                current_try += 1
                messages.append({"role": "user", "content": "System: Invalid JSON format. Please output valid JSON."})
                
            except Exception as e:
                logger.error(f"AI decision error for player {self.player.id}: {e}", exc_info=True)
                break
                
        # Fallback action if retries exhausted
        logger.error(f"AI failed to produce valid action after {max_retries} retries for player {self.player.id}")
        self.last_decision_trace = {
            "model": self.model,
            "action_type": ActionType.PASS.value,
            "issues": ["retries_exhausted"],
            "fallback_used": True,
            "raw_response": None,
        }
        return ActionRequest(
            player_id=self.player.id,
            type=ActionType.PASS
        )
