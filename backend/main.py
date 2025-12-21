import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import game, player, sse, config

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Werewolf VN Backend")

# CORS configuration - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=False,  # Cannot use credentials with wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("CORS: Allowing all origins for development")

from fastapi import Request
from fastapi.responses import JSONResponse
import traceback

@app.middleware("http")
async def global_exception_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Global exception: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "error": str(e)}
        )

# Include routers
app.include_router(game.router, prefix="/api/game", tags=["game"])
app.include_router(player.router, prefix="/api/player", tags=["player"])
app.include_router(sse.router, prefix="/api/sse", tags=["sse"])
app.include_router(config.router, prefix="/api/config", tags=["config"])

@app.on_event("startup")
async def startup_event():
    logger.info("AI Werewolf VN Backend starting up...")
    logger.info(f"Log level: {log_level}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("AI Werewolf VN Backend shutting down...")

@app.get("/")
async def root():
    return {
        "message": "AI Werewolf VN Backend is running",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
