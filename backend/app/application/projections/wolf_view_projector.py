from __future__ import annotations

from app.application.projections.private_view_projector import PrivateViewProjector
from app.models.game_state import GameState, Player


class WolfViewProjector(PrivateViewProjector):
    def project(self, game: GameState, viewer: Player):
        return super().project(game, viewer)
