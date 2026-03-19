from __future__ import annotations

from app.application.projections.projection_service import ProjectionService
from app.models.api_models import CreateGameResponse, GameStateView
from app.models.game_state import GameState, Player


class GamePresenter:
    def __init__(self, projection_service: ProjectionService | None = None):
        self.projection_service = projection_service or ProjectionService()

    def present_state(self, game: GameState, viewer: Player | None = None) -> GameStateView:
        return self.projection_service.project_for_viewer(game, viewer)

    def present_created_game(
        self,
        game: GameState,
        viewer: Player,
        player_token: str,
    ) -> CreateGameResponse:
        return CreateGameResponse(
            player_token=player_token,
            state=self.present_state(game, viewer),
        )
