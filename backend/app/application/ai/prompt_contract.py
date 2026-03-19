from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, Optional, Tuple
import json

from app.models.game_state import ActionType, GamePhase


@dataclass(frozen=True)
class PromptContextSpec:
    include_public_narrative: bool = True
    include_private_observations: bool = True
    include_team_blackboard: bool = False
    include_memory_summary: bool = True


@dataclass(frozen=True)
class ActionWindow:
    phase: GamePhase
    allowed_actions: Tuple[ActionType, ...]
    allowed_target_ids: Tuple[int, ...] = ()
    nullable_target_actions: Tuple[ActionType, ...] = ()
    required_content_actions: Tuple[ActionType, ...] = ()
    notes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class PhasePromptContract:
    phase: GamePhase
    allowed_actions: Tuple[ActionType, ...]
    target_required_actions: Tuple[ActionType, ...] = ()
    target_optional_actions: Tuple[ActionType, ...] = ()
    nullable_target_actions: Tuple[ActionType, ...] = ()
    content_required_actions: Tuple[ActionType, ...] = ()
    context: PromptContextSpec = field(default_factory=PromptContextSpec)
    notes: Tuple[str, ...] = ()

    def supports_action(self, action_type: ActionType) -> bool:
        return action_type in self.allowed_actions

    def requires_target(self, action_type: ActionType) -> bool:
        return action_type in self.target_required_actions

    def allows_targetless(self, action_type: ActionType) -> bool:
        return (
            action_type in self.target_optional_actions
            or action_type in self.nullable_target_actions
        )

    def requires_content(self, action_type: ActionType) -> bool:
        return action_type in self.content_required_actions

    def validate_shape(
        self,
        action_type: ActionType,
        target_id: Optional[int],
        content: Optional[str],
    ) -> list[str]:
        issues: list[str] = []
        if not self.supports_action(action_type):
            issues.append(f"phase {self.phase.value} does not allow action {action_type.value}")
            return issues

        allows_nullable = action_type in self.nullable_target_actions
        if self.requires_target(action_type) and target_id is None and not allows_nullable:
            issues.append(f"action {action_type.value} requires target")

        if (
            target_id is None
            and not self.requires_target(action_type)
            and not self.allows_targetless(action_type)
            and (
                action_type in self.target_required_actions
                or action_type in self.target_optional_actions
            )
        ):
            issues.append(f"action {action_type.value} expects explicit target or abstain marker")

        if self.requires_content(action_type) and not (content or "").strip():
            issues.append(f"action {action_type.value} requires non-empty content")

        return issues

    def to_action_window(
        self,
        allowed_target_ids: Tuple[int, ...] = (),
        notes: Tuple[str, ...] = (),
    ) -> ActionWindow:
        merged_notes = tuple(dict.fromkeys((*self.notes, *notes)))
        return ActionWindow(
            phase=self.phase,
            allowed_actions=self.allowed_actions,
            allowed_target_ids=allowed_target_ids,
            nullable_target_actions=self.nullable_target_actions,
            required_content_actions=self.content_required_actions,
            notes=merged_notes,
        )


def _contract(
    phase: GamePhase,
    *,
    allowed: Tuple[ActionType, ...],
    target_required: Tuple[ActionType, ...] = (),
    target_optional: Tuple[ActionType, ...] = (),
    nullable_target: Tuple[ActionType, ...] = (),
    content_required: Tuple[ActionType, ...] = (),
    context: Optional[PromptContextSpec] = None,
    notes: Tuple[str, ...] = (),
) -> PhasePromptContract:
    return PhasePromptContract(
        phase=phase,
        allowed_actions=allowed,
        target_required_actions=target_required,
        target_optional_actions=target_optional,
        nullable_target_actions=nullable_target,
        content_required_actions=content_required,
        context=context or PromptContextSpec(),
        notes=notes,
    )


PHASE_PROMPT_CONTRACTS: Dict[GamePhase, PhasePromptContract] = {
    GamePhase.GAME_START: _contract(
        GamePhase.GAME_START,
        allowed=(ActionType.CONFIRM, ActionType.PASS),
        notes=("identity acknowledgement only",),
    ),
    GamePhase.NIGHT_START: _contract(
        GamePhase.NIGHT_START,
        allowed=(),
        notes=("transition phase",),
    ),
    GamePhase.NIGHT_WOLF_DISCUSS: _contract(
        GamePhase.NIGHT_WOLF_DISCUSS,
        allowed=(ActionType.SPEECH, ActionType.PASS),
        content_required=(ActionType.SPEECH,),
        context=PromptContextSpec(include_team_blackboard=True),
        notes=("wolf coordination window",),
    ),
    GamePhase.NIGHT_WOLF_VOTE: _contract(
        GamePhase.NIGHT_WOLF_VOTE,
        allowed=(ActionType.KILL,),
        target_required=(ActionType.KILL,),
        context=PromptContextSpec(include_team_blackboard=True),
    ),
    GamePhase.NIGHT_SEER: _contract(
        GamePhase.NIGHT_SEER,
        allowed=(ActionType.CHECK, ActionType.PASS),
        target_required=(ActionType.CHECK,),
    ),
    GamePhase.NIGHT_WITCH: _contract(
        GamePhase.NIGHT_WITCH,
        allowed=(ActionType.SAVE, ActionType.POISON, ActionType.PASS),
        target_required=(ActionType.POISON,),
        target_optional=(ActionType.SAVE,),
        nullable_target=(ActionType.SAVE,),
    ),
    GamePhase.NIGHT_GUARD: _contract(
        GamePhase.NIGHT_GUARD,
        allowed=(ActionType.GUARD, ActionType.PASS),
        target_required=(ActionType.GUARD,),
    ),
    GamePhase.NIGHT_RESOLVE: _contract(
        GamePhase.NIGHT_RESOLVE,
        allowed=(),
        notes=("engine-only resolution phase",),
    ),
    GamePhase.DAY_START: _contract(
        GamePhase.DAY_START,
        allowed=(ActionType.CONFIRM, ActionType.PASS),
        notes=("day reveal acknowledgement",),
    ),
    GamePhase.DAY_LAST_WORDS: _contract(
        GamePhase.DAY_LAST_WORDS,
        allowed=(ActionType.SPEECH, ActionType.PASS, ActionType.CONFIRM),
        content_required=(ActionType.SPEECH,),
    ),
    GamePhase.SHERIFF_ELECTION: _contract(
        GamePhase.SHERIFF_ELECTION,
        allowed=(ActionType.RUN_FOR_SHERIFF, ActionType.PASS),
    ),
    GamePhase.SHERIFF_SPEECH: _contract(
        GamePhase.SHERIFF_SPEECH,
        allowed=(ActionType.SPEECH, ActionType.WITHDRAW, ActionType.SELF_EXPLODE),
        content_required=(ActionType.SPEECH,),
    ),
    GamePhase.SHERIFF_VOTE: _contract(
        GamePhase.SHERIFF_VOTE,
        allowed=(ActionType.VOTE,),
        target_required=(ActionType.VOTE,),
        nullable_target=(ActionType.VOTE,),
    ),
    GamePhase.DAY_DISCUSS: _contract(
        GamePhase.DAY_DISCUSS,
        allowed=(ActionType.SPEECH, ActionType.PASS, ActionType.CONFIRM),
        content_required=(ActionType.SPEECH,),
    ),
    GamePhase.DAY_VOTE: _contract(
        GamePhase.DAY_VOTE,
        allowed=(ActionType.VOTE,),
        target_required=(ActionType.VOTE,),
        nullable_target=(ActionType.VOTE,),
    ),
    GamePhase.DAY_VOTE_RESULT: _contract(
        GamePhase.DAY_VOTE_RESULT,
        allowed=(),
        notes=("engine-only tally phase",),
    ),
    GamePhase.DAY_PK_SPEECH: _contract(
        GamePhase.DAY_PK_SPEECH,
        allowed=(ActionType.SPEECH, ActionType.CONFIRM, ActionType.PASS),
        content_required=(ActionType.SPEECH,),
    ),
    GamePhase.DAY_PK_VOTE: _contract(
        GamePhase.DAY_PK_VOTE,
        allowed=(ActionType.VOTE,),
        target_required=(ActionType.VOTE,),
    ),
    GamePhase.DAY_PK_RESULT: _contract(
        GamePhase.DAY_PK_RESULT,
        allowed=(),
        notes=("engine-only PK tally phase",),
    ),
    GamePhase.HUNTER_SKILL: _contract(
        GamePhase.HUNTER_SKILL,
        allowed=(ActionType.SHOOT, ActionType.PASS),
        target_required=(ActionType.SHOOT,),
    ),
    GamePhase.SHERIFF_TRANSFER: _contract(
        GamePhase.SHERIFF_TRANSFER,
        allowed=(ActionType.VOTE,),
        target_optional=(ActionType.VOTE,),
        nullable_target=(ActionType.VOTE,),
        notes=("target 0 or null means tear badge",),
    ),
    GamePhase.GAME_END: _contract(
        GamePhase.GAME_END,
        allowed=(),
        notes=("terminal phase",),
    ),
}


def get_phase_prompt_contract(phase: GamePhase) -> PhasePromptContract:
    return PHASE_PROMPT_CONTRACTS.get(
        phase,
        _contract(phase, allowed=(), notes=("unknown phase contract",)),
    )


def render_structured_context(context: Any) -> str:
    if is_dataclass(context):
        payload = _to_jsonable(asdict(context))
    else:
        payload = _to_jsonable(context)
    return "=== STRUCTURED_DECISION_CONTEXT ===\n" + json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value
