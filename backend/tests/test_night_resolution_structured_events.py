from app.core.handlers.hunter_skill import HunterSkillHandler
from app.core.handlers.night_resolve import NightResolveHandler
from app.config import GameRulesConfig
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, DeathCause, GamePhase, GameState, Player, Role


def _find_event_log(game: GameState, event: str):
    for log in reversed(game.game_logs):
        if log.data and log.data.get("event") == event:
            return log
    raise AssertionError(f"event log not found: {event}")


def test_poisoned_sheriff_house_rule_config_defaults_off(monkeypatch):
    monkeypatch.delenv("POISONED_SHERIFF_LOSES_BADGE", raising=False)
    assert GameRulesConfig.from_env().poisoned_sheriff_loses_badge is False

    monkeypatch.setenv("POISONED_SHERIFF_LOSES_BADGE", "true")
    assert GameRulesConfig.from_env().poisoned_sheriff_loses_badge is True


def test_night_resolve_logs_death_records_and_opens_shoot_window():
    hunter = Player(id=1, name="Hunter", role=Role.HUNTER, portrait="")
    villager = Player(id=2, name="Villager", role=Role.VILLAGER, portrait="")
    wolf = Player(id=3, name="Wolf", role=Role.WOLF, portrait="")
    seer = Player(id=4, name="Seer", role=Role.SEER, portrait="")
    game = GameState(
        session_id="night-resolve",
        day=1,
        phase=GamePhase.NIGHT_RESOLVE,
        players=[hunter, villager, wolf, seer],
        wolf_kill_target=1,
    )
    hunter.killed_by_wolf = True

    handler = NightResolveHandler(None, game)
    handler.on_enter()

    summary_log = _find_event_log(game, "night_resolve_completed")
    assert summary_log.data["resolved_day"] == 1
    assert summary_log.data["next_day"] == 2
    assert summary_log.data["dead_player_ids"] == [1]
    assert summary_log.data["eligible_shooter_ids"] == [1]
    assert summary_log.data["death_records"][0]["player_id"] == 1
    assert summary_log.data["death_records"][0]["death_cause"] == "wolf_kill"

    assert handler.try_advance() == GamePhase.HUNTER_SKILL
    window_log = _find_event_log(game, "death_skill_window_opened")
    assert window_log.data["shooter_id"] == 1
    assert window_log.data["shooter_role"] == Role.HUNTER.value
    assert window_log.data["next_phase"] == GamePhase.HUNTER_SKILL.value


def test_poisoned_sheriff_transfers_badge_by_default():
    poisoned_sheriff = Player(id=1, name="Sheriff", role=Role.VILLAGER, portrait="", is_sheriff=True)
    other = Player(id=2, name="Other", role=Role.VILLAGER, portrait="")
    wolf = Player(id=5, name="Wolf", role=Role.WOLF, portrait="")
    seer = Player(id=6, name="Seer", role=Role.SEER, portrait="")
    poison_game = GameState(
        session_id="badge-loss",
        day=1,
        phase=GamePhase.NIGHT_RESOLVE,
        players=[poisoned_sheriff, other, wolf, seer],
        sheriff_id=1,
    )
    poisoned_sheriff.poisoned_by_witch = True

    poison_handler = NightResolveHandler(None, poison_game)
    poison_handler.on_enter()
    assert poison_game.sheriff_id == poisoned_sheriff.id
    assert poisoned_sheriff.is_sheriff is True
    assert poison_handler.try_advance() == GamePhase.SHERIFF_TRANSFER
    transfer_log = _find_event_log(poison_game, "sheriff_transfer_pending")
    assert transfer_log.data["sheriff_id"] == poisoned_sheriff.id


def test_poisoned_sheriff_badge_loss_house_rule(monkeypatch):
    monkeypatch.setattr(
        "app.core.handlers.night_resolve.get_rules",
        lambda: type("RulesConfig", (), {"poisoned_sheriff_loses_badge": True})(),
    )
    sheriff = Player(id=1, name="Sheriff", role=Role.VILLAGER, portrait="", is_sheriff=True)
    players = [
        sheriff,
        Player(id=2, name="Other", role=Role.VILLAGER, portrait=""),
        Player(id=3, name="Wolf", role=Role.WOLF, portrait=""),
        Player(id=4, name="Seer", role=Role.SEER, portrait=""),
    ]
    game = GameState(
        session_id="poison-badge-house-rule",
        day=1,
        phase=GamePhase.NIGHT_RESOLVE,
        players=players,
        sheriff_id=sheriff.id,
    )
    sheriff.poisoned_by_witch = True

    handler = NightResolveHandler(None, game)
    handler.on_enter()

    badge_log = _find_event_log(game, "sheriff_badge_lost")
    assert badge_log.data["sheriff_id"] == sheriff.id
    assert game.sheriff_id is None
    assert handler.try_advance() == GamePhase.DAY_START


def test_night_resolve_logs_sheriff_transfer_pending():

    sheriff = Player(id=3, name="Sheriff2", role=Role.VILLAGER, portrait="", is_sheriff=True)
    villager = Player(id=4, name="Other2", role=Role.VILLAGER, portrait="")
    transfer_wolf = Player(id=5, name="Wolf2", role=Role.WOLF, portrait="")
    transfer_seer = Player(id=6, name="Seer2", role=Role.SEER, portrait="")
    transfer_game = GameState(
        session_id="badge-transfer",
        day=2,
        phase=GamePhase.NIGHT_RESOLVE,
        players=[sheriff, villager, transfer_wolf, transfer_seer],
        sheriff_id=3,
        wolf_kill_target=3,
    )
    sheriff.killed_by_wolf = True

    transfer_handler = NightResolveHandler(None, transfer_game)
    transfer_handler.on_enter()
    assert transfer_handler.try_advance() == GamePhase.SHERIFF_TRANSFER
    transfer_log = _find_event_log(transfer_game, "sheriff_transfer_pending")
    assert transfer_log.data["sheriff_id"] == 3
    assert transfer_log.data["next_phase"] == GamePhase.SHERIFF_TRANSFER.value


def test_hunter_skill_logs_shoot_pass_and_target_elimination():
    hunter = Player(
        id=1,
        name="Hunter",
        role=Role.HUNTER,
        portrait="",
        is_alive=False,
    )
    hunter.death_cause = DeathCause.WOLF_KILL
    target = Player(id=2, name="Target", role=Role.VILLAGER, portrait="")
    spare_villager = Player(id=3, name="Spare", role=Role.VILLAGER, portrait="")
    alive_wolf = Player(id=4, name="Wolf", role=Role.WOLF, portrait="")
    seer = Player(id=5, name="Seer", role=Role.SEER, portrait="")
    game = GameState(
        session_id="hunter-skill",
        day=2,
        phase=GamePhase.HUNTER_SKILL,
        players=[hunter, target, spare_villager, alive_wolf, seer],
        dead_players=[1],
        next_phase_after_skill=GamePhase.DAY_START,
    )

    handler = HunterSkillHandler(None, game)
    handler.on_enter()
    prompt_log = _find_event_log(game, "death_skill_prompted")
    assert prompt_log.data["shooter_id"] == 1
    assert prompt_log.data["return_phase"] == GamePhase.DAY_START.value

    assert handler.process_action(ActionRequest(player_id=1, type=ActionType.SHOOT, target_id=2)) is True
    public_log = _find_event_log(game, "death_skill_target_eliminated")
    assert public_log.data["target_id"] == 2
    assert public_log.data["eliminated_by"] == "shot"

    detail_log = _find_event_log(game, "death_skill_shot_fired")
    assert detail_log.data["shooter_id"] == 1
    assert detail_log.data["target_id"] == 2
    assert detail_log.data["target_death_cause"] == "hunter_shoot"

    assert handler.try_advance() == GamePhase.DAY_START

    wolf_king = Player(
        id=3,
        name="WolfKing",
        role=Role.WOLF_KING,
        portrait="",
        is_alive=False,
    )
    wolf_king.death_cause = DeathCause.WOLF_KILL
    alive_wolf = Player(id=5, name="AliveWolf", role=Role.WOLF, portrait="")
    spare = Player(id=4, name="Spare", role=Role.VILLAGER, portrait="")
    pass_game = GameState(
        session_id="wolf-king-skill",
        day=3,
        phase=GamePhase.HUNTER_SKILL,
        players=[wolf_king, spare, alive_wolf],
        dead_players=[3],
    )

    pass_handler = HunterSkillHandler(None, pass_game)
    pass_handler.on_enter()
    assert pass_handler.process_action(ActionRequest(player_id=3, type=ActionType.PASS)) is True
    pass_log = _find_event_log(pass_game, "death_skill_passed")
    assert pass_log.data["shooter_id"] == 3
    assert pass_log.data["shooter_role"] == Role.WOLF_KING.value
