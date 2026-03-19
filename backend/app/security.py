import ipaddress
import os
import secrets
from typing import Optional
from urllib.parse import urlparse

from fastapi import Header, HTTPException

from app.config import Environment, get_config
from app.interfaces.presenters.game_presenter import GamePresenter
from app.models.api_models import (
    CreateGameResponse,
    GameLogView,
    GameStateView,
    PlayerView,
    WolfDiscussMessageView,
)
from app.models.game_state import GameLog, GamePhase, GameState, Player, Role, WolfDiscussMessage

PLAYER_TOKEN_HEADER = "X-Player-Token"
ADMIN_TOKEN_HEADER = "X-Admin-Token"
HIDDEN_ROLE = "unknown"
game_presenter = GamePresenter()


def generate_access_token() -> str:
    return secrets.token_urlsafe(32)


def get_admin_token() -> str:
    return os.getenv("BACKEND_ADMIN_TOKEN", "").strip()


def should_require_admin_token() -> bool:
    token = get_admin_token()
    if token:
        return True
    return get_config().env == Environment.PRODUCTION


def require_admin_access(
    x_admin_token: str | None = Header(default=None, alias=ADMIN_TOKEN_HEADER),
) -> None:
    expected_token = get_admin_token()
    if not expected_token:
        if get_config().env == Environment.PRODUCTION:
            raise HTTPException(status_code=503, detail="管理员令牌未配置")
        return

    if x_admin_token != expected_token:
        raise HTTPException(status_code=403, detail="管理员认证失败")


def validate_llm_api_base(api_base: str | None) -> str | None:
    if api_base is None:
        return None

    normalized = api_base.strip().rstrip("/")
    if not normalized:
        return None

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("api_base 仅支持 http 或 https")
    if not parsed.netloc or not parsed.hostname:
        raise ValueError("api_base 缺少有效主机名")
    if parsed.username or parsed.password:
        raise ValueError("api_base 不允许内嵌认证信息")

    allow_private = (
        os.getenv("ALLOW_PRIVATE_LLM_API_BASE", "false").lower() == "true"
        or get_config().env == Environment.DEVELOPMENT
    )
    if not allow_private and _is_private_host(parsed.hostname):
        raise ValueError("当前环境禁止使用私有网络或本地地址作为 api_base")

    return normalized


def build_game_create_response(game: GameState, viewer_id: int, player_token: str) -> CreateGameResponse:
    viewer = next((player for player in game.players if player.id == viewer_id), None)
    if viewer is None:
        raise ValueError(f"Viewer {viewer_id} not found")
    return game_presenter.present_created_game(game, viewer, player_token)


def build_game_state_view(game: GameState, viewer_id: int | None = None) -> GameStateView:
    viewer = next((player for player in game.players if player.id == viewer_id), None)
    return game_presenter.present_state(game, viewer)


def _build_player_view(player: Player, viewer: Player | None) -> PlayerView:
    is_self = viewer is not None and viewer.id == player.id
    visible_role = _resolve_visible_role(player, viewer)

    return PlayerView(
        id=player.id,
        name=player.name,
        role=visible_role,
        portrait=player.portrait,
        is_human=is_self,
        is_alive=player.is_alive,
        is_sheriff=player.is_sheriff,
        has_acted=player.has_acted,
        poison_used=player.poison_used,
        antidote_used=player.antidote_used,
        gun_used=player.gun_used,
    )


def _resolve_visible_role(player: Player, viewer: Player | None) -> Role | str:
    if viewer is not None:
        if viewer.id == player.id:
            return player.role
        if viewer.role in (Role.WOLF, Role.WOLF_KING) and player.role in (Role.WOLF, Role.WOLF_KING):
            return player.role
    if not player.is_alive:
        return player.role
    return HIDDEN_ROLE


def _build_log_view(log: GameLog) -> GameLogView:
    return GameLogView(
        id=log.id,
        day=log.day,
        phase=log.phase,
        content=log.content,
        player_id=log.player_id,
        is_public=log.is_public,
        type=log.type,
        data=log.data,
    )


def _can_view_log(log: GameLog, viewer: Player | None) -> bool:
    if log.is_public:
        return True
    if viewer is None:
        return False
    return log.player_id == viewer.id


def _build_wolf_messages(
    messages: list[WolfDiscussMessage],
    viewer: Player | None,
) -> list[WolfDiscussMessageView]:
    if viewer is None or viewer.role not in (Role.WOLF, Role.WOLF_KING):
        return []

    return [
        WolfDiscussMessageView(
            id=message.id,
            speaker_id=message.speaker_id,
            content=message.content,
            round=message.round,
        )
        for message in messages
    ]


def _visible_votes(game: GameState, viewer: Player | None) -> dict[int, int]:
    public_vote_phases = {
        GamePhase.DAY_VOTE,
        GamePhase.DAY_VOTE_RESULT,
        GamePhase.SHERIFF_VOTE,
        GamePhase.SHERIFF_TRANSFER,
    }
    if game.phase in public_vote_phases:
        return game.votes
    return {}


def _visible_pk_votes(game: GameState) -> dict[int, int]:
    if game.phase in {GamePhase.DAY_PK_VOTE, GamePhase.DAY_PK_RESULT}:
        return game.pk_votes
    return {}


def _visible_wolf_kill_target(game: GameState, viewer: Player | None) -> int | None:
    if (
        viewer is not None
        and viewer.role == Role.WITCH
        and viewer.is_alive
        and game.phase == GamePhase.NIGHT_WITCH
    ):
        return game.wolf_kill_target
    return None


def _is_private_host(hostname: str) -> bool:
    lowered = hostname.lower()
    if lowered in {"localhost", "localhost.localdomain"}:
        return True
    try:
        address = ipaddress.ip_address(lowered)
    except ValueError:
        return lowered.endswith(".local")

    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    )
