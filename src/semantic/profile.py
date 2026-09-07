"""Safe declarative profiles that bind grammar nodes to registered actions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any


class ProfileError(ValueError):
    """Report an invalid or incompatible semantic profile."""


@dataclass(frozen=True, slots=True)
class ChildSelector:
    """Select safe data from the current node or one of its children.

    Supported kinds are ``child``, ``children``, ``token``, ``text`` and
    ``position``. A child selector reads the already evaluated semantic value;
    a token selector finds a direct terminal by token type.
    """

    kind: str
    index: int | None = None
    token: str | None = None

    def __post_init__(self) -> None:
        allowed = {"child", "children", "token", "text", "position"}
        if self.kind not in allowed:
            raise ProfileError(f"invalid selector kind: {self.kind!r}")
        if self.kind == "child":
            if not isinstance(self.index, int) or self.index < 0:
                raise ProfileError("child selector requires a non-negative index")
        elif self.index is not None:
            raise ProfileError(f"selector {self.kind!r} does not accept an index")
        if self.kind == "token":
            if not isinstance(self.token, str) or not self.token:
                raise ProfileError("token selector requires a token name")
        elif self.token is not None:
            raise ProfileError(f"selector {self.kind!r} does not accept a token")


@dataclass(frozen=True, slots=True)
class ActionInvocation:
    """Invoke one allow-listed action during entry, exit or after one child."""

    name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    phase: str = "exit"
    after_child: int | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ProfileError("action name cannot be empty")
        if self.phase not in {"enter", "exit", "after_child"}:
            raise ProfileError(
                "action phase must be 'enter', 'exit' or 'after_child'"
            )
        if self.phase == "after_child":
            if (
                not isinstance(self.after_child, int)
                or isinstance(self.after_child, bool)
                or self.after_child < 0
            ):
                raise ProfileError(
                    "after_child phase requires a non-negative child index"
                )
        elif self.after_child is not None:
            raise ProfileError("after_child index requires the after_child phase")
        object.__setattr__(self, "arguments", MappingProxyType(dict(self.arguments)))


@dataclass(frozen=True, slots=True)
class RuleBinding:
    """Associate a rule or labeled alternative with ordered actions."""

    rule: str
    actions: tuple[ActionInvocation, ...]
    alternative: str | None = None

    def __post_init__(self) -> None:
        if not self.rule:
            raise ProfileError("binding rule cannot be empty")
        object.__setattr__(self, "actions", tuple(self.actions))
        if not self.actions:
            raise ProfileError("a binding requires at least one action")


@dataclass(frozen=True, slots=True)
class SemanticProfile:
    """Immutable set of grammar-independent semantic bindings."""

    name: str
    bindings: tuple[RuleBinding, ...]
    version: int = 1
    grammar_name: str | None = None
    grammar_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ProfileError("profile name cannot be empty")
        if self.version != 1:
            raise ProfileError(f"unsupported semantic profile version: {self.version}")
        if (self.grammar_name is None) != (self.grammar_sha256 is None):
            raise ProfileError(
                "profile grammar identity requires both name and sha256"
            )
        if self.grammar_name is not None and not self.grammar_name:
            raise ProfileError("profile grammar name cannot be empty")
        if self.grammar_sha256 is not None and (
            len(self.grammar_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.grammar_sha256)
        ):
            raise ProfileError(
                "profile grammar sha256 must be 64 lowercase hexadecimal characters"
            )
        object.__setattr__(self, "bindings", tuple(self.bindings))
        seen: set[tuple[str, str | None]] = set()
        for binding in self.bindings:
            key = (binding.rule, binding.alternative)
            if key in seen:
                raise ProfileError(
                    f"duplicate binding for rule {binding.rule!r}"
                    + (f" alternative {binding.alternative!r}" if binding.alternative else "")
                )
            seen.add(key)


def load_profile(path: str | Path) -> SemanticProfile:
    """Read and fully validate a version-1 JSON semantic profile."""
    profile_path = Path(path)
    try:
        raw = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileError(f"could not load semantic profile: {exc}") from exc
    if not isinstance(raw, dict):
        raise ProfileError("profile root must be a JSON object")
    allowed_root = {"name", "version", "grammar", "bindings"}
    unknown = set(raw) - allowed_root
    if unknown:
        raise ProfileError(f"unknown profile fields: {', '.join(sorted(unknown))}")
    name = raw.get("name")
    version = raw.get("version", 1)
    grammar_name, grammar_sha256 = _parse_grammar_identity(raw.get("grammar"))
    bindings_data = raw.get("bindings")
    if not isinstance(name, str) or not name:
        raise ProfileError("profile field 'name' must be a non-empty string")
    if not isinstance(version, int) or isinstance(version, bool):
        raise ProfileError("profile field 'version' must be an integer")
    if not isinstance(bindings_data, list):
        raise ProfileError("profile field 'bindings' must be an array")
    return SemanticProfile(
        name=name,
        version=version,
        grammar_name=grammar_name,
        grammar_sha256=grammar_sha256,
        bindings=tuple(_parse_binding(item) for item in bindings_data),
    )


def grammar_source_sha256(path: str | Path) -> str:
    """Hash UTF-8 grammar text after normalizing platform line endings."""
    grammar_path = Path(path)
    try:
        source = grammar_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ProfileError(f"could not fingerprint grammar: {exc}") from exc
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def validate_profile_identity(
    profile: SemanticProfile,
    grammar_name: str,
    grammar_path: str | Path,
) -> None:
    """Reject a profile explicitly bound to a different grammar source."""
    if profile.grammar_name is None:
        return
    if profile.grammar_name != grammar_name:
        raise ProfileError(
            "profile grammar name mismatch: "
            f"expected {profile.grammar_name!r}, got {grammar_name!r}"
        )
    actual_sha256 = grammar_source_sha256(grammar_path)
    if profile.grammar_sha256 != actual_sha256:
        raise ProfileError(
            "profile grammar fingerprint mismatch: "
            f"expected {profile.grammar_sha256}, got {actual_sha256}"
        )


def validate_profile(
    profile: SemanticProfile,
    available_rules: Collection[str],
) -> None:
    """Raise when a binding names a rule absent from the selected grammar."""
    available = set(available_rules)
    missing = sorted({binding.rule for binding in profile.bindings} - available)
    if missing:
        raise ProfileError(
            "profile references unavailable grammar rules: " + ", ".join(missing)
        )


def resolve_binding(node: Any, profile: SemanticProfile) -> RuleBinding | None:
    """Resolve a labeled alternative before falling back to its rule."""
    rule_name = getattr(node, "rule_name", None)
    alternative = getattr(node, "alternative", None)
    if rule_name is None:
        return None
    if alternative is not None:
        for binding in profile.bindings:
            if binding.rule == rule_name and binding.alternative == alternative:
                return binding
    for binding in profile.bindings:
        if binding.rule == rule_name and binding.alternative is None:
            return binding
    return None


def _parse_binding(raw: Any) -> RuleBinding:
    if not isinstance(raw, dict):
        raise ProfileError("each binding must be an object")
    unknown = set(raw) - {"rule", "alternative", "actions"}
    if unknown:
        raise ProfileError(f"unknown binding fields: {', '.join(sorted(unknown))}")
    rule = raw.get("rule")
    alternative = raw.get("alternative")
    actions = raw.get("actions")
    if not isinstance(rule, str) or not rule:
        raise ProfileError("binding field 'rule' must be a non-empty string")
    if alternative is not None and (not isinstance(alternative, str) or not alternative):
        raise ProfileError("binding field 'alternative' must be a non-empty string")
    if not isinstance(actions, list) or not actions:
        raise ProfileError("binding field 'actions' must be a non-empty array")
    return RuleBinding(
        rule=rule,
        alternative=alternative,
        actions=tuple(_parse_action(item) for item in actions),
    )


def _parse_grammar_identity(raw: Any) -> tuple[str | None, str | None]:
    if raw is None:
        return None, None
    if not isinstance(raw, dict):
        raise ProfileError("profile field 'grammar' must be an object")
    unknown = set(raw) - {"name", "sha256"}
    if unknown:
        raise ProfileError(
            "unknown grammar identity fields: " + ", ".join(sorted(unknown))
        )
    name = raw.get("name")
    sha256 = raw.get("sha256")
    if not isinstance(name, str) or not name:
        raise ProfileError("profile grammar name must be a non-empty string")
    if not isinstance(sha256, str):
        raise ProfileError("profile grammar sha256 must be a string")
    return name, sha256


def _parse_action(raw: Any) -> ActionInvocation:
    if isinstance(raw, str):
        return ActionInvocation(raw)
    if not isinstance(raw, dict):
        raise ProfileError("each action must be a name or object")
    unknown = set(raw) - {"name", "phase", "after_child", "arguments"}
    if unknown:
        raise ProfileError(f"unknown action fields: {', '.join(sorted(unknown))}")
    name = raw.get("name")
    phase = raw.get("phase", "exit")
    after_child = raw.get("after_child")
    arguments = raw.get("arguments", {})
    if not isinstance(name, str) or not name:
        raise ProfileError("action field 'name' must be a non-empty string")
    if not isinstance(phase, str):
        raise ProfileError("action field 'phase' must be a string")
    if not isinstance(arguments, dict):
        raise ProfileError("action field 'arguments' must be an object")
    return ActionInvocation(
        name=name,
        phase=phase,
        after_child=after_child,
        arguments={key: _parse_argument(value) for key, value in arguments.items()},
    )


def _parse_argument(raw: Any) -> Any:
    if not isinstance(raw, dict) or "$select" not in raw:
        if isinstance(raw, (dict, list)):
            raise ProfileError("action arguments must be JSON scalars or selectors")
        return raw
    if set(raw) - {"$select", "index", "token"}:
        raise ProfileError("selector contains unknown fields")
    kind = raw.get("$select")
    if not isinstance(kind, str):
        raise ProfileError("selector '$select' must be a string")
    return ChildSelector(kind=kind, index=raw.get("index"), token=raw.get("token"))
