from __future__ import annotations

from datetime import datetime, timezone

from app.domain.events.base import DomainEvent, VisibilityScope
from app.infrastructure.game_snapshot_store import (
    GameSnapshotRecord,
    GameSnapshotStore,
)
from app.models.game_state import (
    ActionType,
    DeathCause,
    GameLog,
    GamePhase,
    GameState,
    Player,
    Role,
    WolfDiscussMessage,
)


def build_game_state(session_id: str) -> GameState:
    return GameState(
        session_id=session_id,
        day=3,
        phase=GamePhase.DAY_DISCUSS,
        players=[
            Player(
                id=1,
                name="1号玩家",
                role=Role.VILLAGER,
                portrait="/images/portraits/村民.jpg",
                is_human=True,
                ai_memory={"notes": "keep this"},
            ),
            Player(
                id=2,
                name="2号玩家",
                role=Role.WOLF_KING,
                portrait="/images/portraits/狼王.png",
                is_alive=False,
                death_cause=DeathCause.WOLF_KING_SHOOT,
                poison_used=True,
            ),
        ],
        game_logs=[
            GameLog(
                id="log-1",
                day=3,
                phase=GamePhase.DAY_START,
                content="day starts",
                type="broadcast",
                data={"event": "day_start"},
            ),
            GameLog(
                id="log-2",
                day=3,
                phase=GamePhase.DAY_DISCUSS,
                content="player speaks",
                player_id=1,
                is_public=False,
                type="speech",
                data={"action": ActionType.SPEECH.value},
            ),
        ],
        time_remaining=42,
        winner=None,
        votes={1: 2},
        wolf_kill_target=2,
        dead_players=[2],
        sheriff_candidate_ids=[1, 2],
        sheriff_id=1,
        election_explode_count=1,
        pending_sheriff_election=True,
        election_cancelled=False,
        election_wolf_candidates=[2],
        pk_candidates=[1, 2],
        pk_round=1,
        pk_votes={1: 2},
        last_guarded_player=1,
        next_phase_after_skill=GamePhase.DAY_VOTE,
        wolf_discuss_round=2,
        wolf_discuss_messages=[
            WolfDiscussMessage(
                id="msg-1",
                speaker_id=2,
                content="target 1",
                round=2,
            )
        ],
        wolf_revote_resolver_id=2,
        speaking_order=[1, 2],
        current_speaker_index=0,
    )


def test_save_and_load_round_trip_preserves_snapshot(tmp_path):
    store = GameSnapshotStore(tmp_path)
    game_state = build_game_state("session-round-trip")
    created_at = datetime(2026, 3, 19, 12, 0, tzinfo=timezone.utc)
    updated_at = datetime(2026, 3, 19, 12, 5, tzinfo=timezone.utc)

    saved = store.save(
        game_state,
        "token-123",
        created_at=created_at,
        updated_at=updated_at,
    )

    loaded = store.load(game_state.session_id)

    assert loaded is not None
    assert isinstance(saved, GameSnapshotRecord)
    assert loaded.model_dump(mode="json") == saved.model_dump(mode="json")
    assert loaded.player_token == "token-123"
    assert loaded.created_at == created_at
    assert loaded.updated_at == updated_at
    assert loaded.game_state.model_dump(mode="json") == game_state.model_dump(mode="json")
    assert not any(path.suffix == ".tmp" for path in tmp_path.iterdir())


def test_load_all_returns_only_valid_snapshots(tmp_path):
    store = GameSnapshotStore(tmp_path)
    first = build_game_state("session-alpha")
    second = build_game_state("session-beta")

    store.save(first, "token-a")
    store.save(second, "token-b")

    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "invalid.json").write_text(
        '{"session_id":"invalid","player_token":"token","created_at":"2026-03-19T12:00:00Z","updated_at":"2026-03-19T12:01:00Z","game_state":{"session_id":"invalid"}}',
        encoding="utf-8",
    )

    loaded = store.load_all()

    assert {record.session_id for record in loaded} == {"session-alpha", "session-beta"}
    assert {record.player_token for record in loaded} == {"token-a", "token-b"}
    assert all(isinstance(record, GameSnapshotRecord) for record in loaded)


def test_delete_removes_snapshot_and_is_idempotent(tmp_path):
    store = GameSnapshotStore(tmp_path)
    game_state = build_game_state("session-delete")

    store.save(game_state, "token-delete")

    assert store.load(game_state.session_id) is not None
    assert store.delete(game_state.session_id) is True
    assert store.load(game_state.session_id) is None
    assert store.delete(game_state.session_id) is False


def test_load_all_skips_bad_files_without_raising(tmp_path):
    store = GameSnapshotStore(tmp_path)
    valid = build_game_state("session-valid")
    store.save(valid, "token-valid")

    (tmp_path / "corrupted.json").write_text("{\"broken\": true", encoding="utf-8")
    (tmp_path / "missing-fields.json").write_text(
        "{\"session_id\": \"bad\", \"player_token\": \"x\", \"created_at\": \"2026-03-19T12:00:00Z\"}",
        encoding="utf-8",
    )

    loaded = store.load_all()

    assert len(loaded) == 1
    assert loaded[0].session_id == "session-valid"
    assert loaded[0].player_token == "token-valid"


def test_save_and_load_round_trip_preserves_domain_events(tmp_path):
    store = GameSnapshotStore(tmp_path)
    game_state = build_game_state("session-events")
    domain_events = [
        DomainEvent(
            name="game_created",
            game_id=game_state.session_id,
            day=game_state.day,
            phase=game_state.phase,
            payload={"human_player_id": 1},
            visibility=VisibilityScope.ADMIN,
            actor_id=1,
        ),
        DomainEvent(
            name="phase_entered",
            game_id=game_state.session_id,
            day=game_state.day,
            phase=GamePhase.NIGHT_START,
            payload={"current_phase": GamePhase.NIGHT_START.value},
            visibility=VisibilityScope.PUBLIC,
        ),
    ]

    store.save(
        game_state,
        "token-events",
        last_activity_at=1234.5,
        domain_events=domain_events,
    )

    loaded = store.load(game_state.session_id)

    assert loaded is not None
    assert loaded.last_activity_at == 1234.5
    restored = loaded.to_domain_events()
    assert [event.name for event in restored] == ["game_created", "phase_entered"]
    assert restored[0].visibility == VisibilityScope.ADMIN
    assert restored[1].phase == GamePhase.NIGHT_START
    assert restored[1].payload["current_phase"] == GamePhase.NIGHT_START.value
