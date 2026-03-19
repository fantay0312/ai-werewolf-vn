import asyncio
import os
import logging
import re
import traceback
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from app.config import Environment, get_config
from app.core.game_manager import game_manager
from app.infrastructure.rate_limiter import RateLimiter
from app.infrastructure.runtime_metrics import runtime_metrics
from app.routes import game, player, sse, config
from app.security import (
    ADMIN_TOKEN_HEADER,
    PLAYER_TOKEN_HEADER,
    get_admin_token,
    require_admin_access,
    should_require_admin_token,
)

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
REQUEST_ID_HEADER = "X-Request-ID"
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
rate_limiter = RateLimiter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.started_at = time.time()
    app.state.version = APP_VERSION
    logger.info("AI Werewolf VN Backend starting up...")
    logger.info(f"Log level: {log_level}")
    restored_games = game_manager.restore_persisted_games()
    game_manager.run_maintenance()
    logger.info("Restored %s persisted games", restored_games)
    maintenance_task = asyncio.create_task(_maintenance_loop(), name="game-runtime-maintenance")
    app.state.maintenance_task = maintenance_task
    yield
    maintenance_task.cancel()
    try:
        await maintenance_task
    except asyncio.CancelledError:
        pass
    game_manager.persist_all_games()
    logger.info("AI Werewolf VN Backend shutting down...")


app_config = get_config()
server_config = app_config.server
docs_enabled = (
    app_config.env != Environment.PRODUCTION
    or os.getenv("ENABLE_API_DOCS", "false").lower() == "true"
)

app = FastAPI(
    title="AI Werewolf VN Backend",
    lifespan=lifespan,
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
)

# CORS configuration from config
allowed_origins = server_config.allowed_origins

if app_config.env == Environment.DEVELOPMENT and os.getenv("ALLOW_ALL_CORS", "false").lower() == "true":
    allowed_origins = ["*"]
    logger.warning("CORS: Allowing all origins due to ALLOW_ALL_CORS=true")
else:
    logger.info(f"CORS: Allowing origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False if "*" in allowed_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = _resolve_request_id(request)
    request.state.request_id = request_id
    started_at = time.perf_counter()
    normalized_path = _normalize_request_path(request.url.path)

    limited_response = _build_rate_limit_response(request, request_id)
    if limited_response is not None:
        response = limited_response
    else:
        try:
            response = await call_next(request)
        except Exception:
            duration_seconds = time.perf_counter() - started_at
            runtime_metrics.record_http_request(
                request.method,
                normalized_path,
                500,
                duration_seconds,
            )
            raise

    duration_seconds = time.perf_counter() - started_at
    duration_ms = round(duration_seconds * 1000, 2)
    runtime_metrics.record_http_request(
        request.method,
        normalized_path,
        response.status_code,
        duration_seconds,
    )
    for header_name, header_value in getattr(request.state, "rate_limit_headers", {}).items():
        response.headers.setdefault(header_name, header_value)
    response.headers[REQUEST_ID_HEADER] = request_id
    response.headers["Cache-Control"] = response.headers.get("Cache-Control", "no-store")
    logger.info(
        "request_completed request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", _resolve_request_id(request))
    headers = dict(exc.headers or {})
    headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": request_id},
        headers=headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", _resolve_request_id(request))
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation Error",
            "errors": exc.errors(),
            "request_id": request_id,
        },
        headers={REQUEST_ID_HEADER: request_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", _resolve_request_id(request))
    logger.error("Unhandled exception request_id=%s error=%s", request_id, exc)
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "request_id": request_id},
        headers={REQUEST_ID_HEADER: request_id},
    )


# Include routers
app.include_router(game.router, prefix="/api/game", tags=["game"])
app.include_router(player.router, prefix="/api/player", tags=["player"])
app.include_router(sse.router, prefix="/api/sse", tags=["sse"])
app.include_router(config.router, prefix="/api/config", tags=["config"])


@app.get("/")
async def root():
    return {
        "message": "AI Werewolf VN Backend is running",
        "version": getattr(app.state, "version", APP_VERSION),
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": getattr(app.state, "version", APP_VERSION),
        "env": get_config().env.value,
        "uptime_seconds": _uptime_seconds(),
        "active_games": len(game_manager.games),
    }


@app.get("/ready")
async def readiness_check():
    config = get_config()
    requires_admin = should_require_admin_token()
    admin_token_configured = bool(get_admin_token())

    checks = {
        "config_loaded": True,
        "game_manager_available": True,
        "admin_token_ready": (not requires_admin) or admin_token_configured,
        "persistence_ready": game_manager.persistence_ready(),
        "metrics_ready": True,
        "rate_limit_ready": True,
    }
    ready = all(checks.values())

    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "degraded",
            "env": config.env.value,
            "version": getattr(app.state, "version", APP_VERSION),
            "checks": checks,
        },
    )


@app.get("/metrics")
async def metrics_endpoint(
    x_admin_token: str | None = Header(default=None, alias=ADMIN_TOKEN_HEADER),
):
    server_config = get_config().server
    if not server_config.metrics_enabled:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    if server_config.metrics_require_admin:
        require_admin_access(x_admin_token)

    runtime_metrics.set_gauge(
        "active_games",
        len(game_manager.games),
        help_text="Current number of active games in memory",
    )
    return PlainTextResponse(
        runtime_metrics.to_prometheus_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


def _resolve_request_id(request: Request) -> str:
    inbound = request.headers.get(REQUEST_ID_HEADER)
    if inbound:
        candidate = inbound.strip()
        if 8 <= len(candidate) <= 128:
            return candidate
    return str(uuid.uuid4())


def _uptime_seconds() -> float:
    started_at = getattr(app.state, "started_at", time.time())
    return round(max(0.0, time.time() - started_at), 3)


async def _maintenance_loop() -> None:
    while True:
        interval = max(1, get_config().server.game_cleanup_interval)
        await asyncio.sleep(interval)
        try:
            game_manager.run_maintenance()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Maintenance loop failed: %s", exc, exc_info=True)


def _build_rate_limit_response(request: Request, request_id: str) -> JSONResponse | None:
    rule = _resolve_rate_limit_rule(request)
    if rule is None:
        return None

    bucket, key, window_seconds, limit = rule
    allowed = rate_limiter.allow(bucket, key, window_seconds, limit)
    stats = rate_limiter.snapshot(bucket, key, window_seconds, limit)
    if stats:
        request.state.rate_limit_headers = {
            "X-RateLimit-Limit": str(stats[0].limit),
            "X-RateLimit-Remaining": str(stats[0].remaining),
            "X-RateLimit-Window": str(int(stats[0].window_seconds)),
        }
    if allowed:
        return None

    retry_after_seconds = max(1, int(rate_limiter.retry_after(bucket, key, window_seconds, limit) or window_seconds))
    runtime_metrics.record_business_counter(
        "rate_limit_rejections_total",
        labels={"bucket": bucket},
        help_text="Total number of rate-limited requests by bucket",
    )
    return JSONResponse(
        status_code=429,
        content={"detail": "Too Many Requests", "request_id": request_id},
        headers={
            REQUEST_ID_HEADER: request_id,
            "Retry-After": str(retry_after_seconds),
            **getattr(request.state, "rate_limit_headers", {}),
        },
    )


def _resolve_rate_limit_rule(request: Request) -> tuple[str, str, int, int] | None:
    server_config = get_config().server
    if not server_config.rate_limit_enabled:
        return None

    path = request.url.path
    method = request.method.upper()
    key = _rate_limit_key(request)
    window_seconds = max(1, server_config.rate_limit_window_seconds)

    if method == "POST" and path == "/api/game/create":
        return ("create_game", key, window_seconds, max(1, server_config.rate_limit_create_game))

    if method == "POST" and re.fullmatch(r"/api/player/[^/]+/action", path):
        return ("player_action", key, window_seconds, max(1, server_config.rate_limit_player_action))

    if path.startswith("/api/config"):
        return ("admin_api", key, window_seconds, max(1, server_config.rate_limit_admin))

    return None


def _rate_limit_key(request: Request) -> str:
    player_token = request.headers.get(PLAYER_TOKEN_HEADER)
    if player_token:
        return f"player:{player_token}"

    admin_token = request.headers.get(ADMIN_TOKEN_HEADER)
    if admin_token:
        return f"admin:{admin_token}"

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return f"ip:{client_ip}"

    client_host = request.client.host if request.client else "anonymous"
    return f"ip:{client_host}"


def _normalize_request_path(path: str) -> str:
    if path == "/api/game/create":
        return "/api/game/create"
    if re.fullmatch(r"/api/game/[^/]+/replay", path):
        return "/api/game/:session_id/replay"
    if re.fullmatch(r"/api/game/[^/]+/eval", path):
        return "/api/game/:session_id/eval"
    if re.fullmatch(r"/api/game/[^/]+", path):
        return "/api/game/:session_id"
    if re.fullmatch(r"/api/player/[^/]+/action", path):
        return "/api/player/:session_id/action"
    return path
