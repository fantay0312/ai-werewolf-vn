from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from app.models.game_state import GameState, Player, Role, WolfDiscussMessage

PLAYER_ID_PATTERN = re.compile(r"(\d+)号")


@dataclass(frozen=True)
class WolfSignal:
    speaker_id: int
    round: int
    content: str
    mentioned_player_ids: Tuple[int, ...] = ()
    kind: str = "free_text"


@dataclass(frozen=True)
class WolfTargetAssessment:
    target_id: int
    score: int
    proposed_by: Tuple[int, ...] = ()
    reasons: Tuple[str, ...] = ()


@dataclass(frozen=True)
class WolfTeamBlackboard:
    actor_id: int
    teammate_ids: Tuple[int, ...]
    resolver_id: Optional[int]
    current_round: int
    transcript: Tuple[WolfSignal, ...] = ()
    candidate_targets: Tuple[WolfTargetAssessment, ...] = ()
    cover_story_hints: Tuple[str, ...] = ()


class WolfTeamRuntime:
    def build_blackboard(
        self,
        game_state: GameState,
        actor: Player,
    ) -> Optional[WolfTeamBlackboard]:
        if actor.role not in (Role.WOLF, Role.WOLF_KING):
            return None

        teammate_ids = tuple(
            sorted(
                player.id
                for player in game_state.players
                if player.role in (Role.WOLF, Role.WOLF_KING) and player.id != actor.id
            )
        )
        transcript = tuple(self._to_signal(message) for message in game_state.wolf_discuss_messages)
        candidate_targets = self._build_candidate_targets(game_state, transcript, teammate_ids)
        cover_story_hints = self._extract_cover_story_hints(transcript)
        current_round = game_state.wolf_discuss_round or 0

        return WolfTeamBlackboard(
            actor_id=actor.id,
            teammate_ids=teammate_ids,
            resolver_id=game_state.wolf_revote_resolver_id,
            current_round=current_round,
            transcript=transcript,
            candidate_targets=candidate_targets,
            cover_story_hints=cover_story_hints,
        )

    def _to_signal(self, message: WolfDiscussMessage) -> WolfSignal:
        mentioned_ids = tuple(dict.fromkeys(int(match) for match in PLAYER_ID_PATTERN.findall(message.content)))
        kind = "target_proposal" if mentioned_ids else "free_text"
        return WolfSignal(
            speaker_id=message.speaker_id,
            round=message.round,
            content=message.content,
            mentioned_player_ids=mentioned_ids,
            kind=kind,
        )

    def _build_candidate_targets(
        self,
        game_state: GameState,
        transcript: Tuple[WolfSignal, ...],
        teammate_ids: Tuple[int, ...],
    ) -> Tuple[WolfTargetAssessment, ...]:
        alive_non_wolves = {
            player.id
            for player in game_state.players
            if player.is_alive and player.role not in (Role.WOLF, Role.WOLF_KING)
        }
        proposed_by_target: Dict[int, set[int]] = {}
        reasons_by_target: Dict[int, list[str]] = {}
        score_by_target: Dict[int, int] = {}

        for signal in transcript:
            for player_id in signal.mentioned_player_ids:
                if player_id not in alive_non_wolves:
                    continue
                proposed_by_target.setdefault(player_id, set()).add(signal.speaker_id)
                reasons_by_target.setdefault(player_id, []).append(signal.content)
                score_by_target[player_id] = score_by_target.get(player_id, 0) + 1

        if not score_by_target:
            for player_id in sorted(alive_non_wolves):
                score_by_target[player_id] = 0
                proposed_by_target[player_id] = set()
                reasons_by_target[player_id] = []

        ranked = sorted(
            score_by_target.items(),
            key=lambda item: (-item[1], item[0]),
        )

        return tuple(
            WolfTargetAssessment(
                target_id=target_id,
                score=score,
                proposed_by=tuple(sorted(proposed_by_target.get(target_id, ()))),
                reasons=tuple(reasons_by_target.get(target_id, ())[:3]),
            )
            for target_id, score in ranked
        )

    def _extract_cover_story_hints(self, transcript: Tuple[WolfSignal, ...]) -> Tuple[str, ...]:
        hints: list[str] = []
        for signal in transcript:
            lowered = signal.content.lower()
            if any(keyword in lowered for keyword in ("跳", "站边", "发言", "白天")):
                hints.append(signal.content)
        return tuple(hints[-3:])
