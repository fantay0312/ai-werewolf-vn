import ipaddress
import os
import secrets
from typing import Optional
from urllib.parse import urlparse

from fastapi import Header, HTTPException

from app.config import Environment, get_config
from app.interfaces.presenters.game_presenter import GamePresenter
from app.models.api_models import CreateGameResponse, GameStateView
from app.models.game_state import GameState

PLAYER_TOKEN_HEADER = "X-Player-Token"
ADMIN_TOKEN_HEADER = "X-Admin-Token"
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
