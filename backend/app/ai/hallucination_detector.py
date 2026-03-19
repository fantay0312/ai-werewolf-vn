import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.models.game_state import GameState, Role, GamePhase
from app.ai.memory.fact_layer import FactLayer

logger = logging.getLogger(__name__)

class DetectionResult(BaseModel):
    has_hallucination: bool
    issues: List[str] = []
    suggested_fix: Optional[str] = None

class HallucinationDetector:
    def detect(self, response_content: str, fact_layer: FactLayer, game_state: GameState) -> DetectionResult:
        """
        Detect hallucinations in AI response.
        """
        issues = []
        
        # 1. JSON Format Check
        try:
            data = json.loads(response_content)
        except json.JSONDecodeError:
            return DetectionResult(has_hallucination=True, issues=["Invalid JSON format"])
            
        if not isinstance(data, dict):
             return DetectionResult(has_hallucination=True, issues=["Root must be a JSON object"])

        if "action" not in data:
             return DetectionResult(has_hallucination=True, issues=["Missing 'action' field"])
             
        action = data["action"]
        if not isinstance(action, dict):
             return DetectionResult(has_hallucination=True, issues=["'action' field must be an object"])
             
        action_type = action.get("type")
        target = action.get("target")
        content = action.get("content")

        # 2. Target Validity Check
        if target is not None:
            if not isinstance(target, int):
                 issues.append(f"Target must be an integer, got {type(target)}")
            elif target not in fact_layer.alive_players and target != 0: 
                 # Check if it's a valid dead target (e.g. for Witch saving?)
                 # Usually actions are on alive players.
                 # Exception: Witch saving a just-killed player (who might be in dead_players list if updated instantly, or not)
                 # But FactLayer.alive_players usually reflects current alive.
                 # Let's assume strict alive check for now unless specific phases.
                 issues.append(f"Target {target} is not alive")

        # 3. Permission/Logic Check (Basic)
        if action_type == "kill":
            if fact_layer.my_role not in [Role.WOLF, Role.WOLF_KING]:
                issues.append(f"Role {fact_layer.my_role} cannot perform kill")
                
        elif action_type == "check":
            if fact_layer.my_role != Role.SEER:
                issues.append(f"Role {fact_layer.my_role} cannot perform check")
            # Check if already checked
            for res in fact_layer.skill_status.check_results:
                if res.target_id == target:
                    issues.append(f"Already checked player {target}")

        elif action_type == "save":
            if fact_layer.my_role != Role.WITCH:
                issues.append(f"Role {fact_layer.my_role} cannot perform save")
            if not fact_layer.skill_status.has_antidote:
                issues.append("Antidote already used")

        elif action_type == "poison":
            if fact_layer.my_role != Role.WITCH:
                issues.append(f"Role {fact_layer.my_role} cannot perform poison")
            if not fact_layer.skill_status.has_poison:
                issues.append("Poison already used")
                
        elif action_type == "guard":
            if fact_layer.my_role != Role.GUARD:
                issues.append(f"Role {fact_layer.my_role} cannot perform guard")
            if fact_layer.skill_status.last_guard_target == target and target is not None:
                issues.append(f"Cannot guard {target} consecutively")

        elif action_type == "shoot":
            if fact_layer.my_role not in [Role.HUNTER, Role.WOLF_KING]:
                issues.append(f"Role {fact_layer.my_role} cannot perform shoot")
            if not fact_layer.skill_status.can_shoot:
                issues.append("Cannot shoot (maybe poisoned or not dead yet)")

        # 4. Content Consistency Check (Dead Player References)
        if content:
            # Simple heuristic: check if numbers of dead players are mentioned
            # This is tricky because "1号" might be mentioned in past tense.
            # For now, we skip strict NLP check but could add regex for "X号" and check if X is dead.
            pass

        return DetectionResult(
            has_hallucination=len(issues) > 0,
            issues=issues
        )
