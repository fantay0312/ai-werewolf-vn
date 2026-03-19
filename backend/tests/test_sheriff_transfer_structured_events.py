from app.core.handlers.sheriff_transfer import SheriffTransferHandler
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GamePhase, GameState, Player, Role


def _player(
    player_id: int,
    role: Role,
    *,
    alive: bool = True,
    sheriff: bool = False,
) -> Player:
    return Player(
        id=player_id,
        name=f"{player_id}号玩家",
        role=role,
        portrait="",
        is_alive=alive,
        is_sheriff=sheriff,
    )


def _find_event_log(game: GameState, event_name: str):
    for log in reversed(game.game_logs):
        if log.data and log.data.get("event") == event_name:
            return log
    raise AssertionError(f"event log not found: {event_name}")


def test_sheriff_transfer_logs_started_and_transfer_metadata():
    dead_sheriff = _player(1, Role.VILLAGER, alive=False, sheriff=True)
    receiver = _player(2, Role.SEER)
    other = _player(3, Role.VILLAGER)
    game = GameState(
        session_id="sheriff-transfer",
        day=2,
        phase=GamePhase.SHERIFF_TRANSFER,
        players=[dead_sheriff, receiver, other],
        sheriff_id=1,
        next_phase_after_skill=GamePhase.DAY_START,
    )

    handler = SheriffTransferHandler(None, game)
    handler.on_enter()

    start_log = _find_event_log(game, "sheriff_transfer_started")
    assert start_log.player_id == 1
    assert start_log.type == "action"
    assert start_log.data["sheriff_id"] == 1
    assert start_log.data["eligible_recipient_ids"] == [2, 3]
    assert start_log.data["next_phase"] == GamePhase.DAY_START.value

    assert handler.process_action(ActionRequest(player_id=1, type=ActionType.VOTE, target_id=2)) is True
    transfer_log = _find_event_log(game, "sheriff_badge_transferred")
    assert transfer_log.player_id == 1
    assert transfer_log.data["action"] == "transfer_badge"
    assert transfer_log.data["previous_sheriff_id"] == 1
    assert transfer_log.data["target_id"] == 2
    assert transfer_log.data["next_sheriff_id"] == 2
    assert transfer_log.data["next_phase"] == GamePhase.DAY_START.value
    assert game.sheriff_id == 2
    assert receiver.is_sheriff is True
    assert handler.try_advance() == GamePhase.DAY_START


def test_sheriff_transfer_logs_badge_tear_metadata():
    dead_sheriff = _player(4, Role.VILLAGER, alive=False, sheriff=True)
    other = _player(5, Role.WITCH)
    game = GameState(
        session_id="sheriff-tear",
        day=3,
        phase=GamePhase.SHERIFF_TRANSFER,
        players=[dead_sheriff, other],
        sheriff_id=4,
    )

    handler = SheriffTransferHandler(None, game)
    handler.on_enter()

    assert handler.process_action(ActionRequest(player_id=4, type=ActionType.VOTE, target_id=0)) is True
    tear_log = _find_event_log(game, "sheriff_badge_torn")
    assert tear_log.player_id == 4
    assert tear_log.data["action"] == "tear_badge"
    assert tear_log.data["previous_sheriff_id"] == 4
    assert tear_log.data["next_sheriff_id"] is None
    assert tear_log.data["next_phase"] == GamePhase.DAY_DISCUSS.value
    assert game.sheriff_id is None
    assert dead_sheriff.is_sheriff is False
    assert handler.try_advance() == GamePhase.DAY_DISCUSS
