import asyncio

from app.application.ai.action_guard import ActionGuard
from app.core.game_manager import GameManager
from app.domain.events.base import DomainEvent, VisibilityScope
from app.domain.events.gameplay import game_log_recorded
from app.eval.metrics import EvalMetricsService
from app.eval.replay_service import ReplayService
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GameLog, GamePhase, GameState, Player, Role


def _make_player(player_id: int, role: Role, *, is_human: bool = False) -> Player:
    return Player(
        id=player_id,
        name=f"{player_id}号玩家",
        role=role,
        portrait="/images/portrait.png",
        is_human=is_human,
    )


def test_action_guard_rejects_phase_illegal_action():
    game = GameState(
        session_id="guard-test",
        day=1,
        phase=GamePhase.DAY_DISCUSS,
        players=[
            _make_player(1, Role.VILLAGER),
            _make_player(2, Role.WOLF),
        ],
    )
    actor = game.players[0]
    guard = ActionGuard()

    result = guard.validate(
        game,
        actor,
        ActionRequest(player_id=actor.id, type=ActionType.KILL, target_id=2),
    )

    assert result.allowed is False
    assert any("does not allow action kill" in issue for issue in result.issues)


def test_replay_and_eval_services_build_timeline():
    events = [
        DomainEvent(
            name="game_created",
            game_id="eval-session",
            day=1,
            phase=GamePhase.GAME_START,
            payload={"player_count": 12},
            visibility=VisibilityScope.ADMIN,
        ),
        DomainEvent(
            name="phase_entered",
            game_id="eval-session",
            day=1,
            phase=GamePhase.SHERIFF_ELECTION,
            payload={"current_phase": GamePhase.SHERIFF_ELECTION.value},
        ),
        DomainEvent(
            name="ai_decision_recorded",
            game_id="eval-session",
            day=1,
            phase=GamePhase.SHERIFF_ELECTION,
            payload={
                "model": "test-model",
                "action_type": ActionType.RUN_FOR_SHERIFF.value,
                "fallback_used": True,
                "issues": ["bad_target"],
            },
            actor_id=3,
            visibility=VisibilityScope.ADMIN,
        ),
    ]

    timeline = ReplayService().build_timeline("eval-session", events)
    report = EvalMetricsService().build_report("eval-session", events)

    assert [frame.event_name for frame in timeline.frames] == [
        "game_created",
        "phase_entered",
        "ai_decision_recorded",
    ]
    assert timeline.frames[1].summary == f"进入阶段 {GamePhase.SHERIFF_ELECTION.value}"
    assert report.ai_decisions == 1
    assert report.fallback_decisions == 1
    assert report.illegal_action_rate == 1.0


def test_replay_and_eval_services_handle_empty_event_stream():
    timeline = ReplayService().build_timeline("empty-session", [])
    report = EvalMetricsService().build_report("empty-session", [])

    assert timeline.game_id == "empty-session"
    assert timeline.frames == []
    assert report.game_id == "empty-session"
    assert report.total_events == 0
    assert report.ai_decisions == 0
    assert report.fallback_decisions == 0
    assert report.illegal_action_rate == 0.0
    assert report.fallback_rate == 0.0


def test_game_manager_records_domain_events_and_replay():
    manager = GameManager()
    game = manager.create_game()
    human = next(player for player in game.players if player.is_human)

    success, error = asyncio.run(
        manager.process_action(
            game.session_id,
            ActionRequest(player_id=human.id, type=ActionType.CONFIRM),
        )
    )

    assert success is True, error
    events = manager.get_domain_events(game.session_id)
    names = [event.name for event in events]

    assert names[0] == "game_created"
    assert "player_action_received" in names
    assert "phase_entered" in names

    replay = manager.get_replay_timeline(game.session_id)
    assert replay.frames[0].event_name == "game_created"
    assert any(frame.event_name == "phase_entered" for frame in replay.frames)


def test_game_log_recorded_uses_admin_visibility_for_private_system_logs():
    game = GameState(
        session_id="private-system-log",
        day=2,
        phase=GamePhase.NIGHT_RESOLVE,
        players=[
            _make_player(1, Role.HUNTER),
            _make_player(2, Role.VILLAGER),
        ],
    )
    log = GameLog(
        id="log-1",
        day=2,
        phase=GamePhase.NIGHT_RESOLVE,
        player_id=None,
        content="夜晚结算完成",
        type="action",
        is_public=False,
        data={"event": "night_resolve_completed"},
    )

    event = game_log_recorded(game, log)

    assert event.visibility == VisibilityScope.ADMIN
    assert event.payload["data"]["event"] == "night_resolve_completed"
    assert "viewer_ids" not in event.payload


def test_game_log_recorded_keeps_wolf_team_visibility_for_wolf_private_logs():
    game = GameState(
        session_id="wolf-private-log",
        day=1,
        phase=GamePhase.NIGHT_WOLF_DISCUSS,
        players=[
            _make_player(1, Role.WOLF),
            _make_player(2, Role.WOLF_KING),
            _make_player(3, Role.VILLAGER),
        ],
    )
    log = GameLog(
        id="log-2",
        day=1,
        phase=GamePhase.NIGHT_WOLF_DISCUSS,
        player_id=1,
        content="狼队讨论",
        type="action",
        is_public=False,
        data={"event": "wolf_discussion_message"},
    )

    event = game_log_recorded(game, log)

    assert event.visibility == VisibilityScope.WOLF_TEAM
    assert event.payload["wolf_ids"] == [1, 2]


def test_replay_service_prefers_structured_log_event_name_for_summary():
    event = DomainEvent(
        name="game_log_recorded",
        game_id="replay-structured-log",
        day=2,
        phase=GamePhase.DAY_VOTE_RESULT,
        visibility=VisibilityScope.ADMIN,
        payload={
            "content": "2号玩家以3票被放逐。",
            "data": {"event": "day_vote_exile_result", "banished_id": 2},
        },
    )

    timeline = ReplayService().build_timeline("replay-structured-log", [event])

    assert timeline.frames[0].summary == "day_vote_exile_result"


def test_dead_sheriff_can_transfer_badge_via_game_manager():
    manager = GameManager()
    sheriff = _make_player(1, Role.VILLAGER)
    sheriff.is_alive = False
    sheriff.is_sheriff = True
    successor = _make_player(2, Role.VILLAGER)
    game = GameState(
        session_id="dead-sheriff-transfer",
        day=2,
        phase=GamePhase.SHERIFF_TRANSFER,
        players=[sheriff, successor],
        sheriff_id=1,
        next_phase_after_skill=GamePhase.DAY_START,
    )
    manager.games[game.session_id] = game

    success, error = asyncio.run(
        manager.process_action(
            game.session_id,
            ActionRequest(player_id=1, type=ActionType.VOTE, target_id=2),
        )
    )

    assert success is True, error
    assert game.sheriff_id == 2
    assert sheriff.is_sheriff is False
    assert successor.is_sheriff is True


def test_pending_ai_players_include_dead_sheriff_during_transfer():
    manager = GameManager()
    sheriff = _make_player(1, Role.VILLAGER)
    sheriff.is_alive = False
    sheriff.is_sheriff = True
    sheriff.is_human = False
    successor = _make_player(2, Role.VILLAGER)
    game = GameState(
        session_id="dead-sheriff-ai-transfer",
        day=2,
        phase=GamePhase.SHERIFF_TRANSFER,
        players=[sheriff, successor],
        sheriff_id=1,
    )

    pending = manager._get_pending_ai_players(game)

    assert [player.id for player in pending] == [1]


def test_pending_ai_players_include_non_pk_ai_voters_during_pk_vote():
    manager = GameManager()
    pk_candidate = _make_player(1, Role.WOLF)
    other_ai = _make_player(2, Role.SEER)
    other_ai.is_human = False
    other_human = _make_player(3, Role.VILLAGER, is_human=True)
    game = GameState(
        session_id="pk-ai-voters",
        day=2,
        phase=GamePhase.DAY_PK_VOTE,
        players=[pk_candidate, other_ai, other_human],
        pk_candidates=[1],
    )

    pending = manager._get_pending_ai_players(game)

    assert [player.id for player in pending] == [2]
