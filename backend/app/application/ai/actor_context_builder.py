from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from app.application.ai.action_guard import ActionGuard
from app.application.ai.prompt_contract import ActionWindow, PhasePromptContract, get_phase_prompt_contract
from app.application.ai.wolf_team_runtime import WolfTeamBlackboard, WolfTeamRuntime
from app.models.game_state import GameLog, GamePhase, GameState, Player, Role


@dataclass(frozen=True)
class StructuredActorState:
    session_id: str
    day: int
    phase: GamePhase
    actor_id: int
    actor_role: Role
    actor_alive: bool
    sheriff_id: Optional[int]
    sheriff_candidate_ids: Tuple[int, ...]
    alive_player_ids: Tuple[int, ...]
    dead_player_ids: Tuple[int, ...]
    current_speaker_id: Optional[int]
    wolf_kill_target: Optional[int]


@dataclass(frozen=True)
class PublicNarrativeEntry:
    log_id: str
    day: int
    phase: GamePhase
    player_id: Optional[int]
    content: str
    log_type: str


@dataclass(frozen=True)
class PublicNarrativeFrame:
    entries: Tuple[PublicNarrativeEntry, ...] = ()


@dataclass(frozen=True)
class PrivateObservationFrame:
    direct_messages: Tuple[str, ...] = ()
    phase_notes: Tuple[str, ...] = ()
    legacy_memory_keys: Tuple[str, ...] = ()


@dataclass(frozen=True)
class TeamContextFrame:
    wolf_blackboard: Optional[WolfTeamBlackboard] = None


@dataclass(frozen=True)
class ActorDecisionContext:
    facts: StructuredActorState
    prompt_contract: PhasePromptContract
    action_window: ActionWindow
    public_frame: PublicNarrativeFrame
    private_frame: PrivateObservationFrame
    team_frame: TeamContextFrame


class ActorContextBuilder:
    def __init__(
        self,
        *,
        action_guard: Optional[ActionGuard] = None,
        wolf_team_runtime: Optional[WolfTeamRuntime] = None,
        public_log_limit: int = 20,
    ):
        self.action_guard = action_guard or ActionGuard()
        self.wolf_team_runtime = wolf_team_runtime or WolfTeamRuntime()
        self.public_log_limit = public_log_limit

    def build(self, game_state: GameState, actor: Player) -> ActorDecisionContext:
        contract = get_phase_prompt_contract(game_state.phase)
        action_window = self.action_guard.build_action_window(game_state, actor)
        public_frame = self._build_public_frame(game_state)
        private_frame = self._build_private_frame(game_state, actor)
        team_frame = self._build_team_frame(game_state, actor)

        return ActorDecisionContext(
            facts=self._build_facts(game_state, actor),
            prompt_contract=contract,
            action_window=action_window,
            public_frame=public_frame,
            private_frame=private_frame,
            team_frame=team_frame,
        )

    def _build_facts(self, game_state: GameState, actor: Player) -> StructuredActorState:
        current_speaker_id = None
        if game_state.speaking_order and game_state.current_speaker_index < len(game_state.speaking_order):
            current_speaker_id = game_state.speaking_order[game_state.current_speaker_index]

        return StructuredActorState(
            session_id=game_state.session_id,
            day=game_state.day,
            phase=game_state.phase,
            actor_id=actor.id,
            actor_role=actor.role,
            actor_alive=actor.is_alive,
            sheriff_id=game_state.sheriff_id,
            sheriff_candidate_ids=tuple(sorted(game_state.sheriff_candidate_ids)),
            alive_player_ids=tuple(sorted(player.id for player in game_state.players if player.is_alive)),
            dead_player_ids=tuple(sorted(game_state.dead_players)),
            current_speaker_id=current_speaker_id,
            wolf_kill_target=game_state.wolf_kill_target,
        )

    def _build_public_frame(self, game_state: GameState) -> PublicNarrativeFrame:
        visible_logs = [log for log in game_state.game_logs if log.is_public]
        entries = tuple(
            self._to_public_entry(log)
            for log in visible_logs[-self.public_log_limit :]
        )
        return PublicNarrativeFrame(entries=entries)

    def _build_private_frame(self, game_state: GameState, actor: Player) -> PrivateObservationFrame:
        direct_messages = tuple(
            log.content
            for log in game_state.game_logs
            if not log.is_public and log.player_id == actor.id
        )
        phase_notes = tuple(self._build_phase_notes(game_state, actor))
        legacy_memory_keys = tuple(sorted((actor.ai_memory or {}).keys()))
        return PrivateObservationFrame(
            direct_messages=direct_messages[-10:],
            phase_notes=phase_notes,
            legacy_memory_keys=legacy_memory_keys,
        )

    def _build_team_frame(self, game_state: GameState, actor: Player) -> TeamContextFrame:
        blackboard = self.wolf_team_runtime.build_blackboard(game_state, actor)
        return TeamContextFrame(wolf_blackboard=blackboard)

    def _to_public_entry(self, log: GameLog) -> PublicNarrativeEntry:
        return PublicNarrativeEntry(
            log_id=log.id,
            day=log.day,
            phase=log.phase,
            player_id=log.player_id,
            content=log.content,
            log_type=log.type,
        )

    def _build_phase_notes(self, game_state: GameState, actor: Player) -> list[str]:
        notes: list[str] = []
        if actor.role in (Role.WOLF, Role.WOLF_KING):
            teammates = sorted(
                player.id
                for player in game_state.players
                if player.role in (Role.WOLF, Role.WOLF_KING) and player.id != actor.id
            )
            notes.append(f"wolf teammates: {teammates}")
        if actor.role == Role.WITCH and game_state.phase == GamePhase.NIGHT_WITCH:
            notes.append(f"wolf kill target: {game_state.wolf_kill_target}")
            notes.append(f"antidote available: {not actor.antidote_used}")
            notes.append(f"poison available: {not actor.poison_used}")
        if actor.role == Role.GUARD and game_state.last_guarded_player is not None:
            notes.append(f"cannot repeat guard on: {game_state.last_guarded_player}")
        if actor.role == Role.SEER:
            checked_targets = sorted(
                log.data.get("target_id")
                for log in game_state.game_logs
                if log.data
                and log.player_id == actor.id
                and log.data.get("action") == "seer_check"
                and log.data.get("target_id") is not None
            )
            if checked_targets:
                notes.append(f"seer checks: {checked_targets}")
        if game_state.phase == GamePhase.HUNTER_SKILL:
            notes.append("death skill window is open")
        return notes
