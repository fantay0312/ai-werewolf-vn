from fastapi import APIRouter, HTTPException
from app.core.game_manager import game_manager
from app.models.game_state import GameState

router = APIRouter()

@router.post("/create", response_model=GameState)
async def create_game():
    return game_manager.create_game()

@router.get("/{session_id}", response_model=GameState)
async def get_game_state(session_id: str):
    game = game_manager.get_game(session_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game
