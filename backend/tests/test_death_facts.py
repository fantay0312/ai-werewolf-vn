from app.ai.memory.memory_manager import MemoryManager
from app.ai.prompt_builder import prompt_builder
from app.core.handlers.day_pk_result import DayPKResultHandler
from app.core.handlers.day_vote_result import DayVoteResultHandler
from app.core.handlers.hunter_skill import HunterSkillHandler
from app.core.handlers.night_resolve import NightResolveHandler
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, DeathCause, GamePhase, GameState, Player, Role


def _player(player_id: int, role: Role, *, alive: bool = True) -> Player:
    return Player(
        id=player_id,
        name=f"{player_id}号玩家",
        role=role,
        portrait="",
        is_alive=alive,
    )


def _assert_death_fact(player: Player, day: int, phase: GamePhase, cause: DeathCause):
    assert player.death_day == day
    assert player.death_phase == phase
    assert player.death_cause == cause


def test_night_resolution_records_actual_death_fact():
    victim = _player(1, Role.VILLAGER)
    victim.killed_by_wolf = True
    game = GameState(
        session_id="night-death-fact",
        day=1,
        phase=GamePhase.NIGHT_RESOLVE,
        players=[victim, _player(2, Role.WOLF), _player(3, Role.SEER)],
        wolf_kill_target=victim.id,
    )

    NightResolveHandler(None, game).on_enter()

    _assert_death_fact(victim, 1, GamePhase.NIGHT_RESOLVE, DeathCause.WOLF_KILL)


def test_day_vote_and_pk_record_actual_death_facts():
    vote_target = _player(2, Role.VILLAGER)
    vote_game = GameState(
        session_id="vote-death-fact",
        day=3,
        phase=GamePhase.DAY_VOTE_RESULT,
        players=[_player(1, Role.WOLF), vote_target, _player(3, Role.SEER)],
        votes={1: vote_target.id, 3: vote_target.id},
    )
    pk_target = _player(5, Role.WOLF)
    pk_game = GameState(
        session_id="pk-death-fact",
        day=4,
        phase=GamePhase.DAY_PK_RESULT,
        players=[_player(4, Role.VILLAGER), pk_target, _player(6, Role.SEER)],
        pk_candidates=[pk_target.id],
        pk_round=1,
        pk_votes={4: pk_target.id, 6: pk_target.id},
    )

    DayVoteResultHandler(None, vote_game).on_enter()
    DayPKResultHandler(None, pk_game).on_enter()

    _assert_death_fact(vote_target, 3, GamePhase.DAY_VOTE_RESULT, DeathCause.VOTE_EXILE)
    _assert_death_fact(pk_target, 4, GamePhase.DAY_PK_RESULT, DeathCause.VOTE_EXILE)


def test_shot_records_fact_and_memory_consumes_original_death_metadata():
    hunter = _player(1, Role.HUNTER, alive=False)
    hunter.death_cause = DeathCause.WOLF_KILL
    target = _player(2, Role.WOLF)
    observer = _player(3, Role.VILLAGER)
    game = GameState(
        session_id="shot-death-fact",
        day=2,
        phase=GamePhase.HUNTER_SKILL,
        players=[hunter, target, observer, _player(4, Role.SEER)],
        dead_players=[hunter.id],
    )
    handler = HunterSkillHandler(None, game)

    assert handler.process_action(ActionRequest(
        player_id=hunter.id,
        type=ActionType.SHOOT,
        target_id=target.id,
    )) is True
    _assert_death_fact(target, 2, GamePhase.HUNTER_SKILL, DeathCause.HUNTER_SHOOT)

    game.day = 5
    game.phase = GamePhase.DAY_DISCUSS
    memory = MemoryManager(observer)
    memory.update_facts(game)
    target_fact = next(record for record in memory.fact_layer.dead_players if record.player_id == target.id)
    assert target_fact.day == 2
    assert target_fact.phase == GamePhase.HUNTER_SKILL
    assert target_fact.cause == DeathCause.HUNTER_SHOOT.value
    absolute_facts = prompt_builder.build_absolute_facts(memory.fact_layer)
    assert "第2天HUNTER_SKILL死亡" in absolute_facts
    assert f"死因：{DeathCause.HUNTER_SHOOT.value}" in absolute_facts
