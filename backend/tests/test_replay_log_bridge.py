from app.core.handlers.day_last_words import DayLastWordsHandler
from app.core.handlers.day_pk_result import DayPKResultHandler
from app.core.handlers.day_pk_speech import DayPKSpeechHandler
from app.core.handlers.day_pk_vote import DayPKVoteHandler
from app.core.handlers.day_vote import DayVoteHandler
from app.core.handlers.day_vote_result import DayVoteResultHandler
from app.core.handlers.hunter_skill import HunterSkillHandler
from app.core.handlers.night_guard import NightGuardHandler
from app.core.handlers.night_resolve import NightResolveHandler
from app.core.handlers.night_witch import NightWitchHandler
from app.core.handlers.sheriff_transfer import SheriffTransferHandler
from app.domain.events.base import VisibilityScope
from app.domain.events.gameplay import game_log_recorded
from app.eval.replay_service import ReplayService
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, DeathCause, GamePhase, GameState, Player, Role


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


def _build_timeline(game: GameState, *logs):
    events = [game_log_recorded(game, log) for log in logs]
    return ReplayService().build_timeline(game.session_id, events)


def test_replay_timeline_keeps_vote_log_summaries_and_public_visibility():
    game = GameState(
        session_id="replay-vote",
        day=2,
        phase=GamePhase.DAY_VOTE,
        players=[
            _player(1, Role.VILLAGER),
            _player(2, Role.VILLAGER),
            _player(3, Role.SEER),
        ],
    )
    handler = DayVoteHandler(None, game)
    handler.on_enter()

    voter_id = 1
    target_id = 2
    assert handler.process_action(ActionRequest(player_id=voter_id, type=ActionType.VOTE, target_id=target_id)) is True

    start_log = _find_event_log(game, "day_vote_started")
    cast_log = _find_event_log(game, "day_vote_cast")
    timeline = _build_timeline(game, start_log, cast_log)

    assert [frame.summary for frame in timeline.frames] == [
        "day_vote_started",
        "day_vote_cast",
    ]
    assert [frame.payload["visibility"] for frame in timeline.frames] == [
        VisibilityScope.PUBLIC.value,
        VisibilityScope.PUBLIC.value,
    ]
    assert timeline.frames[0].payload["data"]["eligible_voter_ids"] == [1, 2, 3]
    assert timeline.frames[1].payload["data"]["voter_id"] == voter_id
    assert timeline.frames[1].payload["data"]["target_id"] == target_id
    assert timeline.frames[1].payload["data"]["vote_counts"] == {target_id: 1}


def test_replay_timeline_keeps_vote_result_summary_and_public_visibility():
    game = GameState(
        session_id="replay-vote-result",
        day=2,
        phase=GamePhase.DAY_VOTE_RESULT,
        players=[
            _player(1, Role.VILLAGER, sheriff=True),
            _player(2, Role.VILLAGER),
            _player(3, Role.SEER),
            _player(4, Role.WITCH),
            _player(5, Role.WOLF),
        ],
        sheriff_id=1,
        votes={1: 2, 3: 2, 4: 5},
    )
    handler = DayVoteResultHandler(None, game)
    handler.on_enter()

    tally_log = _find_event_log(game, "day_vote_tallied")
    result_log = _find_event_log(game, "day_vote_exiled")
    timeline = _build_timeline(game, tally_log, result_log)

    assert [frame.summary for frame in timeline.frames] == [
        "day_vote_tallied",
        "day_vote_exiled",
    ]
    assert [frame.payload["visibility"] for frame in timeline.frames] == [
        VisibilityScope.PUBLIC.value,
        VisibilityScope.PUBLIC.value,
    ]
    assert timeline.frames[0].payload["data"]["vote_counts"] == {2: 3, 5: 1}
    assert timeline.frames[1].payload["data"]["banished_id"] == 2
    assert timeline.frames[1].payload["data"]["dead_player_ids"] == [2]
    assert timeline.frames[1].payload["data"]["outcome"] == "exiled"


def test_replay_timeline_keeps_pk_entry_summary_and_public_visibility():
    game = GameState(
        session_id="replay-pk-entry",
        day=2,
        phase=GamePhase.DAY_VOTE_RESULT,
        players=[
            _player(1, Role.VILLAGER),
            _player(2, Role.VILLAGER),
            _player(3, Role.SEER),
            _player(4, Role.WITCH),
            _player(5, Role.WOLF),
            _player(6, Role.GUARD),
        ],
        votes={1: 2, 3: 2, 4: 5, 6: 5},
    )
    handler = DayVoteResultHandler(None, game)
    handler.on_enter()

    tie_log = _find_event_log(game, "day_vote_tied")
    timeline = _build_timeline(game, tie_log)
    frame = timeline.frames[0]

    assert frame.summary == "day_vote_tied"
    assert frame.payload["visibility"] == VisibilityScope.PUBLIC.value
    assert frame.payload["data"]["pk_candidate_ids"] == [2, 5]
    assert frame.payload["data"]["pk_round"] == 1
    assert frame.payload["data"]["next_phase"] == GamePhase.DAY_PK_SPEECH.value


def test_replay_timeline_keeps_day_last_words_summary_and_public_visibility():
    game = GameState(
        session_id="replay-last-words",
        day=2,
        phase=GamePhase.DAY_LAST_WORDS,
        players=[
            _player(1, Role.VILLAGER, alive=False),
            _player(2, Role.SEER, alive=False),
            _player(3, Role.WITCH),
        ],
        dead_players=[2, 1],
    )
    handler = DayLastWordsHandler(None, game)
    handler.on_enter()
    assert handler.process_action(ActionRequest(player_id=1, type=ActionType.SPEECH, content="遗言")) is True

    start_log = _find_event_log(game, "day_last_words_started")
    speech_log = _find_event_log(game, "day_last_words_speech")
    timeline = _build_timeline(game, start_log, speech_log)

    assert [frame.summary for frame in timeline.frames] == [
        "day_last_words_started",
        "day_last_words_speech",
    ]
    assert [frame.payload["visibility"] for frame in timeline.frames] == [
        VisibilityScope.PUBLIC.value,
        VisibilityScope.PUBLIC.value,
    ]
    assert timeline.frames[0].payload["data"]["speaking_order"] == [1, 2]
    assert timeline.frames[1].payload["data"]["speaker_id"] == 1
    assert timeline.frames[1].payload["data"]["next_phase_hint"] == GamePhase.SHERIFF_ELECTION.value


def test_replay_timeline_keeps_day_pk_speech_summary_and_public_visibility():
    game = GameState(
        session_id="replay-pk-speech",
        day=3,
        phase=GamePhase.DAY_PK_SPEECH,
        players=[
            _player(1, Role.VILLAGER),
            _player(2, Role.WOLF),
            _player(3, Role.SEER),
        ],
        pk_candidates=[2, 1],
        pk_round=1,
    )
    handler = DayPKSpeechHandler(None, game)
    handler.on_enter()
    assert handler.process_action(ActionRequest(player_id=1, type=ActionType.SPEECH, content="PK发言")) is True

    start_log = _find_event_log(game, "day_pk_speech_started")
    speech_log = _find_event_log(game, "day_pk_speech")
    timeline = _build_timeline(game, start_log, speech_log)

    assert [frame.summary for frame in timeline.frames] == [
        "day_pk_speech_started",
        "day_pk_speech",
    ]
    assert [frame.payload["visibility"] for frame in timeline.frames] == [
        VisibilityScope.PUBLIC.value,
        VisibilityScope.PUBLIC.value,
    ]
    assert timeline.frames[0].payload["data"]["pk_candidate_ids"] == [1, 2]
    assert timeline.frames[1].payload["data"]["speaker_id"] == 1
    assert timeline.frames[1].payload["data"]["next_phase_hint"] == GamePhase.DAY_PK_VOTE.value


def test_replay_timeline_keeps_private_night_resolution_visibility_and_summary():
    hunter = _player(1, Role.HUNTER)
    villager = _player(2, Role.VILLAGER)
    game = GameState(
        session_id="replay-night",
        day=1,
        phase=GamePhase.NIGHT_RESOLVE,
        players=[hunter, villager],
        wolf_kill_target=1,
    )
    hunter.killed_by_wolf = True

    handler = NightResolveHandler(None, game)
    handler.on_enter()

    summary_log = _find_event_log(game, "night_resolve_completed")
    timeline = _build_timeline(game, summary_log)
    frame = timeline.frames[0]

    assert frame.summary == "night_resolve_completed"
    assert frame.payload["visibility"] == VisibilityScope.ADMIN.value
    assert frame.payload["data"]["dead_player_ids"] == [1]
    assert frame.payload["data"]["eligible_shooter_ids"] == [1]
    assert "viewer_ids" not in frame.payload


def test_replay_timeline_keeps_death_skill_visibility_boundaries():
    hunter = _player(1, Role.HUNTER, alive=False)
    hunter.death_cause = DeathCause.WOLF_KILL
    target = _player(2, Role.VILLAGER)
    game = GameState(
        session_id="replay-death-skill",
        day=2,
        phase=GamePhase.HUNTER_SKILL,
        players=[hunter, target],
        dead_players=[1],
        next_phase_after_skill=GamePhase.DAY_START,
    )

    handler = HunterSkillHandler(None, game)
    handler.on_enter()
    assert handler.process_action(ActionRequest(player_id=1, type=ActionType.SHOOT, target_id=2)) is True

    prompt_log = _find_event_log(game, "death_skill_prompted")
    public_log = _find_event_log(game, "death_skill_target_eliminated")
    detail_log = _find_event_log(game, "death_skill_shot_fired")
    timeline = _build_timeline(game, prompt_log, public_log, detail_log)

    assert [frame.summary for frame in timeline.frames] == [
        "death_skill_prompted",
        "death_skill_target_eliminated",
        "death_skill_shot_fired",
    ]
    assert [frame.payload["visibility"] for frame in timeline.frames] == [
        VisibilityScope.PRIVATE.value,
        VisibilityScope.PUBLIC.value,
        VisibilityScope.PRIVATE.value,
    ]
    assert timeline.frames[0].payload["viewer_ids"] == [1]
    assert "viewer_ids" not in timeline.frames[1].payload
    assert timeline.frames[2].payload["viewer_ids"] == [1]
    assert timeline.frames[2].payload["data"]["target_id"] == 2
    assert timeline.frames[2].payload["data"]["target_death_cause"] == DeathCause.HUNTER_SHOOT.value


def test_replay_timeline_keeps_pk_vote_and_result_visibility():
    game = GameState(
        session_id="replay-pk-vote",
        day=2,
        phase=GamePhase.DAY_PK_VOTE,
        players=[
            _player(1, Role.VILLAGER),
            _player(2, Role.VILLAGER),
            _player(3, Role.SEER),
        ],
        pk_candidates=[1, 2],
        pk_round=1,
    )
    vote_handler = DayPKVoteHandler(None, game)
    vote_handler.on_enter()
    assert vote_handler.process_action(ActionRequest(player_id=3, type=ActionType.VOTE, target_id=1)) is True

    start_log = _find_event_log(game, "day_pk_vote_started")
    cast_log = _find_event_log(game, "day_pk_vote_cast")
    vote_timeline = _build_timeline(game, start_log, cast_log)

    assert [frame.summary for frame in vote_timeline.frames] == [
        "day_pk_vote_started",
        "day_pk_vote_cast",
    ]
    assert [frame.payload["visibility"] for frame in vote_timeline.frames] == [
        VisibilityScope.PUBLIC.value,
        VisibilityScope.PRIVATE.value,
    ]
    assert vote_timeline.frames[1].payload["viewer_ids"] == [3]

    game.phase = GamePhase.DAY_PK_RESULT
    result_handler = DayPKResultHandler(None, game)
    result_handler.on_enter()

    tally_log = _find_event_log(game, "day_pk_vote_tallied")
    result_log = _find_event_log(game, "day_pk_vote_exiled")
    result_timeline = _build_timeline(game, tally_log, result_log)

    assert [frame.summary for frame in result_timeline.frames] == [
        "day_pk_vote_tallied",
        "day_pk_vote_exiled",
    ]
    assert [frame.payload["visibility"] for frame in result_timeline.frames] == [
        VisibilityScope.PUBLIC.value,
        VisibilityScope.PUBLIC.value,
    ]
    assert result_timeline.frames[1].payload["data"]["banished_id"] == 1


def test_replay_timeline_keeps_witch_and_guard_private_visibility():
    witch = _player(1, Role.WITCH)
    victim = _player(2, Role.VILLAGER)
    guard = _player(3, Role.GUARD)
    other = _player(4, Role.VILLAGER)

    witch_game = GameState(
        session_id="replay-witch",
        day=1,
        phase=GamePhase.NIGHT_WITCH,
        players=[witch, victim],
        wolf_kill_target=2,
    )
    witch_handler = NightWitchHandler(None, witch_game)
    witch_handler.on_enter()
    assert witch_handler.process_action(ActionRequest(player_id=1, type=ActionType.SAVE)) is True

    witch_prompt_log = _find_event_log(witch_game, "witch_prompted")
    witch_save_log = _find_event_log(witch_game, "witch_saved")
    witch_timeline = _build_timeline(witch_game, witch_prompt_log, witch_save_log)

    assert [frame.summary for frame in witch_timeline.frames] == [
        "witch_prompted",
        "witch_saved",
    ]
    assert [frame.payload["visibility"] for frame in witch_timeline.frames] == [
        VisibilityScope.PRIVATE.value,
        VisibilityScope.PRIVATE.value,
    ]
    assert witch_timeline.frames[0].payload["viewer_ids"] == [1]
    assert witch_timeline.frames[1].payload["viewer_ids"] == [1]

    guard_game = GameState(
        session_id="replay-guard",
        day=1,
        phase=GamePhase.NIGHT_GUARD,
        players=[guard, victim, other],
        last_guarded_player=2,
    )
    guard_handler = NightGuardHandler(None, guard_game)
    guard_handler.on_enter()
    assert guard_handler.process_action(ActionRequest(player_id=3, type=ActionType.GUARD, target_id=4)) is True

    guard_prompt_log = _find_event_log(guard_game, "guard_prompted")
    guard_action_log = _find_event_log(guard_game, "guard_protected")
    guard_timeline = _build_timeline(guard_game, guard_prompt_log, guard_action_log)

    assert [frame.summary for frame in guard_timeline.frames] == [
        "guard_prompted",
        "guard_protected",
    ]
    assert [frame.payload["visibility"] for frame in guard_timeline.frames] == [
        VisibilityScope.PRIVATE.value,
        VisibilityScope.PRIVATE.value,
    ]
    assert guard_timeline.frames[0].payload["viewer_ids"] == [3]
    assert guard_timeline.frames[1].payload["viewer_ids"] == [3]


def test_replay_timeline_keeps_sheriff_transfer_public_visibility():
    sheriff = _player(1, Role.VILLAGER, alive=False, sheriff=True)
    successor = _player(2, Role.VILLAGER)
    game = GameState(
        session_id="replay-sheriff-transfer",
        day=2,
        phase=GamePhase.SHERIFF_TRANSFER,
        players=[sheriff, successor],
        sheriff_id=1,
        next_phase_after_skill=GamePhase.DAY_START,
    )

    handler = SheriffTransferHandler(None, game)
    handler.on_enter()
    assert handler.process_action(ActionRequest(player_id=1, type=ActionType.VOTE, target_id=2)) is True

    start_log = _find_event_log(game, "sheriff_transfer_started")
    transfer_log = _find_event_log(game, "sheriff_badge_transferred")
    timeline = _build_timeline(game, start_log, transfer_log)

    assert [frame.summary for frame in timeline.frames] == [
        "sheriff_transfer_started",
        "sheriff_badge_transferred",
    ]
    assert [frame.payload["visibility"] for frame in timeline.frames] == [
        VisibilityScope.PUBLIC.value,
        VisibilityScope.PUBLIC.value,
    ]
    assert timeline.frames[1].payload["data"]["next_sheriff_id"] == 2


def test_replay_timeline_keeps_sheriff_transfer_public_events():
    dead_sheriff = _player(1, Role.VILLAGER, alive=False, sheriff=True)
    receiver = _player(2, Role.SEER)
    game = GameState(
        session_id="replay-sheriff-transfer",
        day=3,
        phase=GamePhase.SHERIFF_TRANSFER,
        players=[dead_sheriff, receiver],
        sheriff_id=1,
        next_phase_after_skill=GamePhase.DAY_START,
    )
    handler = SheriffTransferHandler(None, game)
    handler.on_enter()
    assert handler.process_action(ActionRequest(player_id=1, type=ActionType.VOTE, target_id=2)) is True

    start_log = _find_event_log(game, "sheriff_transfer_started")
    transfer_log = _find_event_log(game, "sheriff_badge_transferred")
    timeline = _build_timeline(game, start_log, transfer_log)

    assert [frame.summary for frame in timeline.frames] == [
        "sheriff_transfer_started",
        "sheriff_badge_transferred",
    ]
    assert [frame.payload["visibility"] for frame in timeline.frames] == [
        VisibilityScope.PUBLIC.value,
        VisibilityScope.PUBLIC.value,
    ]
    assert timeline.frames[0].payload["data"]["eligible_recipient_ids"] == [2]
    assert timeline.frames[1].payload["data"]["target_id"] == 2
    assert timeline.frames[1].payload["data"]["next_sheriff_id"] == 2


def test_replay_timeline_uses_action_summary_for_witch_and_guard_private_logs():
    witch = _player(7, Role.WITCH)
    victim = _player(8, Role.VILLAGER)
    witch_game = GameState(
        session_id="replay-witch",
        day=1,
        phase=GamePhase.NIGHT_WITCH,
        players=[witch, victim],
        wolf_kill_target=8,
    )
    witch_handler = NightWitchHandler(None, witch_game)
    assert witch_handler.process_action(ActionRequest(player_id=7, type=ActionType.SAVE)) is True
    witch_log = witch_game.game_logs[-1]

    guard = _player(9, Role.GUARD)
    protected = _player(10, Role.VILLAGER)
    guard_game = GameState(
        session_id="replay-guard",
        day=1,
        phase=GamePhase.NIGHT_GUARD,
        players=[guard, protected],
    )
    guard_handler = NightGuardHandler(None, guard_game)
    assert guard_handler.process_action(ActionRequest(player_id=9, type=ActionType.GUARD, target_id=10)) is True
    guard_log = guard_game.game_logs[-1]

    witch_timeline = _build_timeline(witch_game, witch_log)
    guard_timeline = _build_timeline(guard_game, guard_log)

    assert witch_timeline.frames[0].summary == "witch_saved"
    assert witch_timeline.frames[0].payload["visibility"] == VisibilityScope.PRIVATE.value
    assert witch_timeline.frames[0].payload["viewer_ids"] == [7]
    assert witch_timeline.frames[0].payload["data"]["action"] == "witch_save"
    assert witch_timeline.frames[0].payload["data"]["target_id"] == 8

    assert guard_timeline.frames[0].summary == "guard_protected"
    assert guard_timeline.frames[0].payload["visibility"] == VisibilityScope.PRIVATE.value
    assert guard_timeline.frames[0].payload["viewer_ids"] == [9]
    assert guard_timeline.frames[0].payload["data"]["action"] == "guard_protect"
    assert guard_timeline.frames[0].payload["data"]["target_id"] == 10
