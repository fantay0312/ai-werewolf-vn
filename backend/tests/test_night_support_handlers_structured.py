from app.core.handlers.night_guard import NightGuardHandler
from app.core.handlers.night_witch import NightWitchHandler
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GamePhase, GameState, Player, Role


def _latest_event(game: GameState, event: str):
    for log in reversed(game.game_logs):
        if log.data and log.data.get("event") == event:
            return log
    raise AssertionError(f"missing event log: {event}")


def test_witch_structured_prompt_save_poison_and_pass():
    witch = Player(id=1, name="Witch", role=Role.WITCH, portrait="")
    victim = Player(id=2, name="Victim", role=Role.VILLAGER, portrait="")
    poison_target = Player(id=3, name="PoisonTarget", role=Role.VILLAGER, portrait="")

    game = GameState(
        session_id="witch-test",
        day=1,
        phase=GamePhase.NIGHT_WITCH,
        players=[witch, victim, poison_target],
        wolf_kill_target=2,
    )
    handler = NightWitchHandler(None, game)

    handler.on_enter()
    prompt_log = _latest_event(game, "witch_prompted")
    assert prompt_log.data["witch_id"] == 1
    assert prompt_log.data["wolf_kill_target"] == 2
    assert prompt_log.data["can_save_target_id"] == 2
    assert prompt_log.data["allowed_poison_target_ids"] == [1, 2, 3]
    assert prompt_log.data["next_phase_hint"] == GamePhase.NIGHT_GUARD.value

    assert handler.process_action(ActionRequest(player_id=1, type=ActionType.SAVE)) is True
    save_log = _latest_event(game, "witch_saved")
    assert save_log.data["action"] == "witch_save"
    assert save_log.data["target_id"] == 2
    assert save_log.data["target_source"] == "wolf_kill_target"
    assert save_log.data["antidote_available_after"] is False

    pass_game = GameState(
        session_id="witch-pass",
        day=1,
        phase=GamePhase.NIGHT_WITCH,
        players=[Player(id=4, name="WitchPass", role=Role.WITCH, portrait=""), victim],
        wolf_kill_target=2,
    )
    pass_handler = NightWitchHandler(None, pass_game)
    pass_handler.on_enter()
    assert pass_handler.process_action(ActionRequest(player_id=4, type=ActionType.PASS)) is True
    pass_log = _latest_event(pass_game, "witch_passed")
    assert pass_log.data["action"] == "pass"
    assert pass_log.data["can_save_target_id"] == 2
    assert pass_log.data["next_phase_hint"] == GamePhase.NIGHT_GUARD.value

    poison_game = GameState(
        session_id="witch-poison",
        day=2,
        phase=GamePhase.NIGHT_WITCH,
        players=[Player(id=5, name="WitchPoison", role=Role.WITCH, portrait=""), poison_target],
    )
    poison_handler = NightWitchHandler(None, poison_game)
    poison_handler.on_enter()
    assert poison_handler.process_action(ActionRequest(player_id=5, type=ActionType.POISON, target_id=3)) is True
    poison_log = _latest_event(poison_game, "witch_poisoned")
    assert poison_log.data["action"] == "witch_poison"
    assert poison_log.data["target_id"] == 3
    assert poison_log.data["poison_available_after"] is False


def test_guard_structured_prompt_guard_and_pass():
    guard = Player(id=1, name="Guard", role=Role.GUARD, portrait="")
    target = Player(id=2, name="Target", role=Role.VILLAGER, portrait="")
    other = Player(id=3, name="Other", role=Role.VILLAGER, portrait="")
    game = GameState(
        session_id="guard-test",
        day=1,
        phase=GamePhase.NIGHT_GUARD,
        players=[guard, target, other],
        last_guarded_player=2,
    )
    handler = NightGuardHandler(None, game)

    handler.on_enter()
    prompt_log = _latest_event(game, "guard_prompted")
    assert prompt_log.data["guard_id"] == 1
    assert prompt_log.data["blocked_target_id"] == 2
    assert prompt_log.data["allowed_target_ids"] == [1, 3]
    assert prompt_log.data["next_phase_hint"] == GamePhase.NIGHT_RESOLVE.value

    assert handler.process_action(ActionRequest(player_id=1, type=ActionType.GUARD, target_id=3)) is True
    guard_log = _latest_event(game, "guard_protected")
    assert guard_log.data["action"] == "guard_protect"
    assert guard_log.data["target_id"] == 3
    assert guard_log.data["blocked_target_id_before"] == 2
    assert guard_log.data["blocked_target_id_after"] == 3

    pass_game = GameState(
        session_id="guard-pass",
        day=2,
        phase=GamePhase.NIGHT_GUARD,
        players=[Player(id=4, name="GuardPass", role=Role.GUARD, portrait=""), target],
        last_guarded_player=2,
    )
    pass_handler = NightGuardHandler(None, pass_game)
    pass_handler.on_enter()
    assert pass_handler.process_action(ActionRequest(player_id=4, type=ActionType.PASS)) is True
    pass_log = _latest_event(pass_game, "guard_passed")
    assert pass_log.data["action"] == "pass"
    assert pass_log.data["blocked_target_id_before"] == 2
    assert pass_log.data["blocked_target_id_after"] is None
