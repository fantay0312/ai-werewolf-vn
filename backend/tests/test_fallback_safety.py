from app.core.game_manager import GameManager
from app.models.game_state import ActionType, GamePhase, GameState, Player, Role


def _player(player_id: int, role: Role, *, alive: bool = True) -> Player:
    return Player(
        id=player_id,
        name=f"{player_id}号玩家",
        role=role,
        portrait="",
        is_alive=alive,
    )


def test_witch_fallback_saves_when_possible_and_never_poisons():
    manager = GameManager()
    witch = _player(1, Role.WITCH)
    victim = _player(2, Role.VILLAGER)
    game = GameState(
        session_id="witch-fallback",
        day=1,
        phase=GamePhase.NIGHT_WITCH,
        players=[witch, victim],
        wolf_kill_target=victim.id,
    )

    save_action = manager._get_fallback_action(game, witch)
    game.wolf_kill_target = None
    pass_action = manager._get_fallback_action(game, witch)

    assert save_action.type == ActionType.SAVE
    assert pass_action.type == ActionType.PASS


def test_wolf_fallback_prefers_non_wolf_target():
    manager = GameManager()
    wolf = _player(1, Role.WOLF)
    teammate = _player(2, Role.WOLF_KING)
    villager = _player(3, Role.VILLAGER)
    game = GameState(
        session_id="wolf-fallback",
        day=1,
        phase=GamePhase.NIGHT_WOLF_VOTE,
        players=[wolf, teammate, villager],
    )

    action = manager._get_fallback_action(game, wolf)

    assert action.type == ActionType.KILL
    assert action.target_id == villager.id


def test_wolf_fallback_uses_alive_wolf_only_when_no_other_target_exists():
    manager = GameManager()
    wolf = _player(1, Role.WOLF)
    teammate = _player(2, Role.WOLF_KING)
    game = GameState(
        session_id="wolf-only-fallback",
        day=1,
        phase=GamePhase.NIGHT_WOLF_VOTE,
        players=[wolf, teammate],
    )

    action = manager._get_fallback_action(game, wolf)

    assert action.target_id in {wolf.id, teammate.id}


def test_hunter_fallback_always_passes():
    manager = GameManager()
    hunter = _player(1, Role.HUNTER, alive=False)
    game = GameState(
        session_id="hunter-fallback",
        day=2,
        phase=GamePhase.HUNTER_SKILL,
        players=[hunter, _player(2, Role.VILLAGER)],
    )

    action = manager._get_fallback_action(game, hunter)

    assert action.type == ActionType.PASS
    assert action.target_id is None
