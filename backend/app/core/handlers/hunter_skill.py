from app.core.phase_handler import PhaseHandler
from app.models.game_state import DeathCause, GamePhase, ActionType, Role
from app.models.action_model import ActionRequest
from app.core.rules import Rules


class HunterSkillHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.HUNTER_SKILL

    def on_enter(self):
        shooter = self._find_shooter()
        if shooter:
            role_name = "猎人" if shooter.role == Role.HUNTER else "狼王"
            self.add_log(
                f"你已出局，是否发动{role_name}技能开枪带人？",
                player_id=shooter.id,
                is_public=False,
                log_type="action",
                data=self.build_event_data(
                    "death_skill_prompted",
                    shooter_id=shooter.id,
                    shooter_role=shooter.role.value,
                    death_cause=self._cause_value(shooter.death_cause),
                    return_phase=(
                        self.game.next_phase_after_skill.value
                        if getattr(self.game, "next_phase_after_skill", None)
                        else None
                    ),
                ),
            )
            shooter.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_player(action.player_id)
        if not player:
            return False

        shooter = self._find_shooter()
        if not shooter or player.id != shooter.id:
            return False

        if action.type == ActionType.SHOOT:
            target = self.find_alive_player(action.target_id)
            if not target:
                return False
            target.is_alive = False
            target_death_cause = (
                DeathCause.HUNTER_SHOOT if player.role == Role.HUNTER else DeathCause.WOLF_KING_SHOOT
            )
            target.death_cause = target_death_cause
            if target.id not in self.game.dead_players:
                self.game.dead_players.append(target.id)
            player.gun_used = True
            player.has_acted = True
            self.add_log(
                f"枪声响起，{target.id}号玩家出局。",
                log_type="action",
                data=self.build_event_data(
                    "death_skill_target_eliminated",
                    target_id=target.id,
                    eliminated_by="shot",
                    source_phase=GamePhase.HUNTER_SKILL.value,
                ),
            )
            self.add_log(
                f"{player.id}号发动死亡技能带走了{target.id}号。",
                player_id=player.id,
                is_public=False,
                log_type="action",
                data=self.build_event_data(
                    "death_skill_shot_fired",
                    shooter_id=player.id,
                    shooter_role=player.role.value,
                    shooter_death_cause=self._cause_value(player.death_cause),
                    target_id=target.id,
                    target_role=target.role.value,
                    target_death_cause=self._cause_value(target_death_cause),
                    dead_player_ids=list(self.game.dead_players),
                ),
            )
            return True

        if action.type == ActionType.PASS:
            player.gun_used = True
            player.has_acted = True
            self.add_log(
                "枪声未响起。",
                is_public=False,
                player_id=player.id,
                log_type="action",
                data=self.build_event_data(
                    "death_skill_passed",
                    shooter_id=player.id,
                    shooter_role=player.role.value,
                    shooter_death_cause=self._cause_value(player.death_cause),
                ),
            )
            return True

        return False

    def try_advance(self) -> GamePhase:
        shooter = self._find_shooter()
        if shooter:
            return None

        # Check for Sheriff Transfer
        dead_sheriff = next(
            (p for p in self.game.players if not p.is_alive and p.is_sheriff), None
        )
        if dead_sheriff:
            self.add_log(
                "死亡技能结算后进入警徽移交。",
                is_public=False,
                log_type="action",
                data=self.build_event_data(
                    "death_skill_transition",
                    next_phase=GamePhase.SHERIFF_TRANSFER.value,
                    sheriff_id=dead_sheriff.id,
                ),
            )
            return GamePhase.SHERIFF_TRANSFER

        if hasattr(self.game, 'next_phase_after_skill') and self.game.next_phase_after_skill:
            self.add_log(
                "死亡技能结算后返回主流程。",
                is_public=False,
                log_type="action",
                data=self.build_event_data(
                    "death_skill_transition",
                    next_phase=self.game.next_phase_after_skill.value,
                ),
            )
            return self.game.next_phase_after_skill

        self.add_log(
            "死亡技能结算后进入白天讨论。",
            is_public=False,
            log_type="action",
            data=self.build_event_data(
                "death_skill_transition",
                next_phase=GamePhase.DAY_DISCUSS.value,
            ),
        )
        return GamePhase.DAY_DISCUSS

    def _find_shooter(self):
        for p in self.game.players:
            if (not p.is_alive
                    and p.role in (Role.HUNTER, Role.WOLF_KING)
                    and not p.gun_used
                    and Rules.can_shoot(p, p.death_cause, alive_wolves=self.alive_wolf_count())):
                return p
        return None

    def _cause_value(self, cause):
        if isinstance(cause, DeathCause):
            return cause.value
        return cause
