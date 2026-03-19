from __future__ import annotations

from enum import Enum

from app.application.projections.admin_view_projector import AdminViewProjector
from app.application.projections.private_view_projector import PrivateViewProjector
from app.application.projections.public_view_projector import PublicViewProjector
from app.application.projections.wolf_view_projector import WolfViewProjector
from app.models.api_models import GameStateView
from app.models.game_state import GameState, Player, Role


class ProjectionAudience(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    WOLF = "wolf"
    ADMIN = "admin"


class ProjectionService:
    def __init__(self):
        self.public = PublicViewProjector()
        self.private = PrivateViewProjector()
        self.wolf = WolfViewProjector()
        self.admin = AdminViewProjector()

    def project_for_viewer(self, game: GameState, viewer: Player | None = None) -> GameStateView:
        if viewer is None:
            return self.public.project(game)
        if viewer.role in (Role.WOLF, Role.WOLF_KING):
            return self.wolf.project(game, viewer)
        return self.private.project(game, viewer)

    def project_admin(self, game: GameState) -> GameStateView:
        return self.admin.project(game)

    def project_game_state(
        self,
        game: GameState,
        audience: ProjectionAudience | str = ProjectionAudience.PUBLIC,
        viewer: Player | None = None,
    ) -> GameStateView:
        normalized = self._normalize_audience(audience)
        if normalized == ProjectionAudience.ADMIN:
            return self.project_admin(game)
        if normalized == ProjectionAudience.PUBLIC:
            return self.public.project(game)
        if viewer is None:
            return self.public.project(game)
        if normalized == ProjectionAudience.WOLF:
            return self.wolf.project(game, viewer)
        return self.private.project(game, viewer)

    def project_payload(
        self,
        game: GameState,
        audience: ProjectionAudience | str = ProjectionAudience.PUBLIC,
        viewer: Player | None = None,
    ) -> dict[str, object]:
        return self.project_game_state(game, audience=audience, viewer=viewer).model_dump()

    def _normalize_audience(self, audience: ProjectionAudience | str) -> ProjectionAudience:
        if isinstance(audience, ProjectionAudience):
            return audience

        aliases = {
            "public": ProjectionAudience.PUBLIC,
            "spectator": ProjectionAudience.PUBLIC,
            "private": ProjectionAudience.PRIVATE,
            "player": ProjectionAudience.PRIVATE,
            "self": ProjectionAudience.PRIVATE,
            "wolf": ProjectionAudience.WOLF,
            "wolves": ProjectionAudience.WOLF,
            "admin": ProjectionAudience.ADMIN,
            "internal": ProjectionAudience.ADMIN,
        }
        normalized = str(audience).strip().lower()
        if normalized not in aliases:
            raise ValueError(f"Unsupported projection audience: {audience}")
        return aliases[normalized]


projection_service = ProjectionService()
