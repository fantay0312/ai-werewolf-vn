from app.core.phase_handler import PhaseHandler
from app.config import get_rules
from app.models.game_state import DeathCause, GamePhase, Role
from app.models.action_model import ActionRequest
from app.core.rules import Rules


class NightResolveHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_RESOLVE

    def on_enter(self):
        resolved_day = self.game.day
        self._resolved_day = resolved_day
        dead_player_ids = Rules.resolve_night_deaths(self.game)
        self._poisoned_ids = [
            pid for pid in dead_player_ids
            if self.game.wolf_kill_target != pid
        ]
        self._death_records = []

        # 可选房规：被毒警长强制流失警徽；标准规则允许移交。
        self.sheriff_poisoned = False
        self.sheriff_badge_lost = False
        sheriff_id_before = self.game.sheriff_id
        if self.game.sheriff_id:
            sheriff = self.find_player(self.game.sheriff_id)
            if sheriff and sheriff.poisoned_by_witch:
                self.sheriff_poisoned = True
                if get_rules().poisoned_sheriff_loses_badge:
                    self.sheriff_badge_lost = True
                    sheriff.is_sheriff = False
                    self.game.sheriff_id = None
                    self.add_log(
                        "警长被毒杀，警徽流失！",
                        log_type="broadcast",
                        data=self.build_event_data(
                            "sheriff_badge_lost",
                            resolved_day=resolved_day,
                            sheriff_id=sheriff.id,
                            cause=DeathCause.WITCH_POISON.value,
                            badge_action="lost",
                        ),
                    )

        # Update player status
        for pid in dead_player_ids:
            player = self.find_player(pid)
            if player:
                death_cause = (
                    DeathCause.WITCH_POISON if player.poisoned_by_witch else DeathCause.WOLF_KILL
                )
                self.record_death(player, death_cause)
                self._death_records.append(
                    {
                        "player_id": player.id,
                        "role": player.role.value,
                        "death_cause": death_cause.value,
                        "killed_by_wolf": player.killed_by_wolf,
                        "poisoned_by_witch": player.poisoned_by_witch,
                        "saved_by_witch": player.saved_by_witch,
                        "protected_by_guard": player.protected_by_guard,
                        "is_sheriff": player.is_sheriff,
                    }
                )

        self.game.dead_players = dead_player_ids
        self.game.last_resolved_night = resolved_day
        self.evaluate_win_condition()
        alive_wolves = self.alive_wolf_count()
        self._eligible_shooters = [
            player.id
            for player in self.game.players
            if (
                player.id in dead_player_ids
                and player.role in (Role.HUNTER, Role.WOLF_KING)
                and not player.gun_used
                and Rules.can_shoot(player, player.death_cause, alive_wolves=alive_wolves)
            )
        ]

        # Reset night status for all players
        for p in self.game.players:
            p.protected_by_guard = False
            p.killed_by_wolf = False
            p.poisoned_by_witch = False
            p.saved_by_witch = False
            p.checked_by_seer = False
            p.has_acted = False

        resolve_data = self.build_event_data(
            "night_resolve_completed",
            resolved_day=resolved_day,
            next_day=resolved_day + 1,
            wolf_kill_target=self.game.wolf_kill_target,
            dead_player_ids=dead_player_ids,
            death_records=self._death_records,
            poisoned_player_ids=list(self._poisoned_ids),
            eligible_shooter_ids=list(self._eligible_shooters),
            sheriff_id_before=sheriff_id_before,
            sheriff_id_after=self.game.sheriff_id,
            sheriff_poisoned=self.sheriff_poisoned,
        )
        self.game.day += 1

        self.add_log(
            f"夜晚结算完成，死亡玩家: {dead_player_ids}",
            is_public=False,
            log_type="action",
            data=resolve_data,
        )

    def process_action(self, action: ActionRequest) -> bool:
        return False

    def try_advance(self) -> GamePhase:
        dead_ids = self.game.dead_players
        resolved_day = getattr(self, "_resolved_day", self.game.day - 1)

        if self.game.winner:
            return GamePhase.GAME_END

        # Check for shooters (Hunter/Wolf King not poisoned)
        for pid in dead_ids:
            player = self.find_player(pid)
            if (
                player
                and player.role in (Role.HUNTER, Role.WOLF_KING)
                and not player.gun_used
                and Rules.can_shoot(player, player.death_cause, alive_wolves=self.alive_wolf_count())
            ):
                self.game.next_phase_after_skill = GamePhase.DAY_START
                self.add_log(
                    "夜晚结算检测到开枪窗口。",
                    is_public=False,
                    log_type="action",
                    data=self.build_event_data(
                        "death_skill_window_opened",
                        resolved_day=resolved_day,
                        shooter_id=player.id,
                        shooter_role=player.role.value,
                        death_cause=self._cause_value(player.death_cause),
                        return_phase=GamePhase.DAY_START.value,
                        next_phase=GamePhase.HUNTER_SKILL.value,
                    ),
                )
                return GamePhase.HUNTER_SKILL

        # 房规启用时，被毒警长不进入移交阶段。
        if self.sheriff_badge_lost:
            self.add_log(
                "夜晚结算后直接进入白天阶段。",
                is_public=False,
                log_type="action",
                data=self.build_event_data(
                    "night_resolve_transition",
                    resolved_day=resolved_day,
                    reason="sheriff_badge_lost",
                    next_phase=GamePhase.DAY_START.value,
                ),
            )
            return GamePhase.DAY_START

        # 警长死亡（非毒杀）：需要转移警徽
        for pid in dead_ids:
            player = self.find_player(pid)
            if player and player.is_sheriff:
                self.game.next_phase_after_skill = GamePhase.DAY_START
                self.add_log(
                    "夜晚结算检测到警徽移交窗口。",
                    is_public=False,
                    log_type="action",
                    data=self.build_event_data(
                        "sheriff_transfer_pending",
                        resolved_day=resolved_day,
                        sheriff_id=player.id,
                        death_cause=self._cause_value(player.death_cause),
                        next_phase=GamePhase.SHERIFF_TRANSFER.value,
                        return_phase=GamePhase.DAY_START.value,
                    ),
                )
                return GamePhase.SHERIFF_TRANSFER

        self.add_log(
            "夜晚结算后直接进入白天阶段。",
            is_public=False,
            log_type="action",
            data=self.build_event_data(
                "night_resolve_transition",
                resolved_day=resolved_day,
                reason="no_pending_skill",
                next_phase=GamePhase.DAY_START.value,
            ),
        )
        return GamePhase.DAY_START

    def _cause_value(self, cause):
        if isinstance(cause, DeathCause):
            return cause.value
        return cause
