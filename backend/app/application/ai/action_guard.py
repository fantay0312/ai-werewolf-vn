from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from app.application.ai.prompt_contract import ActionWindow, PhasePromptContract, get_phase_prompt_contract
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GamePhase, GameState, Player, Role


@dataclass(frozen=True)
class ActionGuardResult:
    allowed: bool
    issues: Tuple[str, ...] = ()
    normalized_action: Optional[ActionRequest] = None
    contract: Optional[PhasePromptContract] = None
    window: Optional[ActionWindow] = None


class ActionGuard:
    def contract_for(self, phase: GamePhase) -> PhasePromptContract:
        return get_phase_prompt_contract(phase)

    def build_action_window(self, game_state: GameState, actor: Player) -> ActionWindow:
        contract = self.contract_for(game_state.phase)
        allowed_targets = self._resolve_allowed_targets(game_state, actor)
        notes = self._build_dynamic_notes(game_state, actor)
        return contract.to_action_window(allowed_target_ids=allowed_targets, notes=notes)

    def validate(
        self,
        game_state: GameState,
        actor: Player,
        action: ActionRequest,
        *,
        window: Optional[ActionWindow] = None,
    ) -> ActionGuardResult:
        contract = self.contract_for(game_state.phase)
        active_window = window or self.build_action_window(game_state, actor)
        issues: list[str] = []

        if action.player_id != actor.id:
            issues.append("action.player_id does not match actor")

        issues.extend(contract.validate_shape(action.type, action.target_id, action.content))

        if not contract.supports_action(action.type):
            return ActionGuardResult(
                allowed=False,
                issues=tuple(dict.fromkeys(issues)),
                contract=contract,
                window=active_window,
            )

        if action.target_id is not None and active_window.allowed_target_ids:
            allowed_targets = set(active_window.allowed_target_ids)
            if action.target_id not in allowed_targets and not self._is_special_target(
                action.type, action.target_id, contract
            ):
                issues.append(
                    f"target {action.target_id} is outside phase window for {game_state.phase.value}"
                )

        if (
            game_state.phase in {GamePhase.DAY_DISCUSS, GamePhase.SHERIFF_SPEECH, GamePhase.DAY_PK_SPEECH}
            and game_state.speaking_order
            and game_state.current_speaker_index < len(game_state.speaking_order)
        ):
            current_speaker = game_state.speaking_order[game_state.current_speaker_index]
            if actor.id != current_speaker:
                issues.append(f"current speaker is {current_speaker}, not {actor.id}")

        normalized_action = ActionRequest(
            player_id=actor.id,
            type=action.type,
            target_id=action.target_id,
            content=(action.content or "").strip() or None,
        )

        return ActionGuardResult(
            allowed=not issues,
            issues=tuple(dict.fromkeys(issues)),
            normalized_action=normalized_action,
            contract=contract,
            window=active_window,
        )

    def _resolve_allowed_targets(self, game_state: GameState, actor: Player) -> Tuple[int, ...]:
        phase = game_state.phase
        alive_ids = tuple(sorted(player.id for player in game_state.players if player.is_alive))

        if phase == GamePhase.SHERIFF_VOTE:
            return tuple(sorted(game_state.sheriff_candidate_ids))
        if phase == GamePhase.DAY_PK_VOTE:
            return tuple(sorted(game_state.pk_candidates))
        if phase == GamePhase.SHERIFF_TRANSFER:
            return tuple(
                sorted(player.id for player in game_state.players if player.is_alive and player.id != actor.id)
            )
        if phase == GamePhase.NIGHT_WITCH:
            if actor.role == Role.WITCH and game_state.wolf_kill_target is not None:
                return tuple(sorted(set(alive_ids) | {game_state.wolf_kill_target}))
            return alive_ids
        return alive_ids

    def _build_dynamic_notes(self, game_state: GameState, actor: Player) -> Tuple[str, ...]:
        notes: list[str] = []
        if game_state.speaking_order and game_state.current_speaker_index < len(game_state.speaking_order):
            current_speaker = game_state.speaking_order[game_state.current_speaker_index]
            notes.append(f"current speaker: {current_speaker}")
        if game_state.phase == GamePhase.NIGHT_WOLF_VOTE and game_state.wolf_revote_resolver_id is not None:
            notes.append(f"wolf revote resolver: {game_state.wolf_revote_resolver_id}")
        if actor.role == Role.GUARD and game_state.last_guarded_player is not None:
            notes.append(f"last guarded player: {game_state.last_guarded_player}")
        return tuple(notes)

    def _is_special_target(
        self,
        action_type: ActionType,
        target_id: int,
        contract: PhasePromptContract,
    ) -> bool:
        if action_type in contract.nullable_target_actions and target_id == 0:
            return True
        return False
