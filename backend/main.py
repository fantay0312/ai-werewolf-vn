import os
import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_config
from app.routes import game, player, sse, config

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Werewolf VN Backend starting up...")
    logger.info(f"Log level: {log_level}")
    yield
    logger.info("AI Werewolf VN Backend shutting down...")


app = FastAPI(title="AI Werewolf VN Backend", lifespan=lifespan)

# CORS configuration from config
server_config = get_config().server
allowed_origins = server_config.allowed_origins

if os.getenv("ENV", "development") == "development":
    # In development, allow all origins for convenience
    allowed_origins = ["*"]
    logger.info("CORS: Allowing all origins (development mode)")
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
async def global_exception_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Global exception: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
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
        "version": "1.0.0",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
