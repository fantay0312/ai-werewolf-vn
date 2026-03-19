from __future__ import annotations

from app.domain.commands.player_commands import PlayerCommand
from app.domain.kernel.snapshot import GameSnapshot
from app.models.game_state import ActionType, GamePhase


PHASE_ACTIONS: dict[GamePhase, set[ActionType]] = {
    GamePhase.GAME_START: {ActionType.CONFIRM, ActionType.PASS},
    GamePhase.NIGHT_WOLF_DISCUSS: {ActionType.SPEECH, ActionType.PASS},
    GamePhase.NIGHT_WOLF_VOTE: {ActionType.KILL},
    GamePhase.NIGHT_SEER: {ActionType.CHECK},
    GamePhase.NIGHT_WITCH: {ActionType.SAVE, ActionType.POISON, ActionType.PASS},
    GamePhase.NIGHT_GUARD: {ActionType.GUARD, ActionType.PASS},
    GamePhase.DAY_START: {ActionType.CONFIRM, ActionType.PASS},
    GamePhase.DAY_LAST_WORDS: {ActionType.SPEECH, ActionType.PASS},
    GamePhase.DAY_DISCUSS: {ActionType.SPEECH, ActionType.PASS, ActionType.CONFIRM},
    GamePhase.DAY_VOTE: {ActionType.VOTE},
    GamePhase.DAY_VOTE_RESULT: {ActionType.CONFIRM, ActionType.PASS},
    GamePhase.DAY_PK_SPEECH: {ActionType.SPEECH, ActionType.PASS},
    GamePhase.DAY_PK_VOTE: {ActionType.VOTE},
    GamePhase.DAY_PK_RESULT: {ActionType.CONFIRM, ActionType.PASS},
    GamePhase.SHERIFF_ELECTION: {ActionType.RUN_FOR_SHERIFF, ActionType.PASS},
    GamePhase.SHERIFF_SPEECH: {ActionType.SPEECH, ActionType.WITHDRAW, ActionType.SELF_EXPLODE},
    GamePhase.SHERIFF_VOTE: {ActionType.VOTE},
    GamePhase.HUNTER_SKILL: {ActionType.SHOOT, ActionType.PASS},
    GamePhase.SHERIFF_TRANSFER: {ActionType.VOTE},
}


class CommandValidator:
    def validate(self, snapshot: GameSnapshot, command: PlayerCommand) -> list[str]:
        issues: list[str] = []

        if command.phase != snapshot.phase:
            issues.append("命令阶段与当前游戏阶段不一致")

        allowed_actions = PHASE_ACTIONS.get(snapshot.phase)
        if allowed_actions and command.action_type not in allowed_actions:
            issues.append(f"{snapshot.phase.value} 阶段不允许 {command.action_type.value} 操作")

        if command.actor_id not in snapshot.alive_player_ids:
            death_action_phases = {
                GamePhase.HUNTER_SKILL,
                GamePhase.DAY_LAST_WORDS,
                GamePhase.SHERIFF_TRANSFER,
            }
            if snapshot.phase not in death_action_phases:
                issues.append("死亡玩家不能在当前阶段行动")

        if command.target_id is not None and command.target_id != 0:
            if command.target_id not in snapshot.alive_player_ids:
                issues.append(f"目标 {command.target_id} 当前不存活")

        if (
            snapshot.phase == GamePhase.NIGHT_WOLF_VOTE
            and snapshot.wolf_revote_resolver_id is not None
            and command.actor_id != snapshot.wolf_revote_resolver_id
        ):
            issues.append("当前只有被指定的狼人可以重新决定击杀目标")

        if (
            snapshot.phase in {GamePhase.DAY_DISCUSS, GamePhase.SHERIFF_SPEECH, GamePhase.DAY_PK_SPEECH}
            and snapshot.current_speaker_id is not None
            and command.actor_id != snapshot.current_speaker_id
        ):
            issues.append(f"当前轮到 {snapshot.current_speaker_id} 号玩家行动")

        return issues
