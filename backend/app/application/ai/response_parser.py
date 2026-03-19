from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

from app.application.ai.prompt_contract import get_phase_prompt_contract
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GamePhase


@dataclass(frozen=True)
class ParsedAction:
    action_type: Optional[ActionType]
    target_id: Optional[int]
    content: Optional[str]
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_action_request(self, player_id: int) -> Optional[ActionRequest]:
        if self.action_type is None:
            return None
        return ActionRequest(
            player_id=player_id,
            type=self.action_type,
            target_id=self.target_id,
            content=self.content,
        )


@dataclass(frozen=True)
class ParsedAgentResponse:
    raw_text: str
    payload: Optional[Mapping[str, Any]]
    action: Optional[ParsedAction]
    issues: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        return self.action is not None and not self.issues


class ResponseParser:
    def parse(
        self,
        raw_response: str | Mapping[str, Any],
        *,
        phase: Optional[GamePhase] = None,
    ) -> ParsedAgentResponse:
        payload, raw_text, issues = self._coerce_payload(raw_response)
        if payload is None:
            return ParsedAgentResponse(raw_text=raw_text, payload=None, action=None, issues=tuple(issues))

        action_payload = payload.get("action", payload)
        if not isinstance(action_payload, Mapping):
            issues.append("field 'action' must be an object")
            return ParsedAgentResponse(raw_text=raw_text, payload=payload, action=None, issues=tuple(issues))

        parsed_action, action_issues = self._parse_action(action_payload)
        issues.extend(action_issues)

        if phase is not None and parsed_action and parsed_action.action_type is not None:
            contract = get_phase_prompt_contract(phase)
            issues.extend(
                contract.validate_shape(
                    parsed_action.action_type,
                    parsed_action.target_id,
                    parsed_action.content,
                )
            )

        return ParsedAgentResponse(
            raw_text=raw_text,
            payload=payload,
            action=parsed_action,
            issues=tuple(issues),
        )

    def _coerce_payload(
        self,
        raw_response: str | Mapping[str, Any],
    ) -> tuple[Optional[Mapping[str, Any]], str, list[str]]:
        if isinstance(raw_response, Mapping):
            return raw_response, json.dumps(raw_response, ensure_ascii=False), []

        raw_text = raw_response
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            return None, raw_text, [f"invalid JSON: {exc.msg}"]

        if not isinstance(payload, Mapping):
            return None, raw_text, ["root response must be an object"]

        return payload, raw_text, []

    def _parse_action(
        self,
        action_payload: Mapping[str, Any],
    ) -> tuple[Optional[ParsedAction], list[str]]:
        issues: list[str] = []
        action_type = self._coerce_action_type(action_payload.get("type"))
        if action_type is None:
            issues.append("missing or invalid action.type")

        target_id = self._coerce_target_id(action_payload.get("target"))
        if "target" in action_payload and action_payload.get("target") is not None and target_id is None:
            issues.append("action.target must be integer-like or null")

        content = action_payload.get("content")
        if content is not None and not isinstance(content, str):
            issues.append("action.content must be a string")
            content = None

        extras = {
            key: value
            for key, value in action_payload.items()
            if key not in {"type", "target", "content"}
        }

        return (
            ParsedAction(
                action_type=action_type,
                target_id=target_id,
                content=content,
                extras=extras,
            ),
            issues,
        )

    def _coerce_action_type(self, raw_value: Any) -> Optional[ActionType]:
        if isinstance(raw_value, ActionType):
            return raw_value
        if not isinstance(raw_value, str):
            return None
        try:
            return ActionType(raw_value)
        except ValueError:
            return None

    def _coerce_target_id(self, raw_value: Any) -> Optional[int]:
        if raw_value is None:
            return None
        if isinstance(raw_value, bool):
            return None
        if isinstance(raw_value, int):
            return raw_value
        if isinstance(raw_value, str) and raw_value.strip():
            try:
                return int(raw_value.strip())
            except ValueError:
                return None
        return None
