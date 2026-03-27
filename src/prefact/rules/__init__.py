"""Refactoring rules – each rule can scan, fix, and validate."""

from __future__ import annotations

import abc
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prefact.config import Config
    from prefact.models import Fix, Issue, ValidationResult

# Global rule registry
_REGISTRY: dict[str, type["BaseRule"]] = {}


def register(cls: type["BaseRule"]) -> type["BaseRule"]:
    """Decorator that registers a rule class."""
    _REGISTRY[cls.rule_id] = cls
    return cls


def get_all_rules() -> dict[str, type["BaseRule"]]:
    return dict(_REGISTRY)


def get_rule(rule_id: str) -> type["BaseRule"]:
    return _REGISTRY[rule_id]


class BaseRule(abc.ABC):
    """Base class every refactoring rule must implement."""

    rule_id: str = ""
    description: str = ""

    def __init__(self, config: "Config") -> None:
        self.config = config

    @abc.abstractmethod
    def scan_file(self, path: Path, source: str) -> list["Issue"]:
        """Return list of issues found in *source*."""

    @abc.abstractmethod
    def fix(self, path: Path, source: str, issues: list["Issue"]) -> tuple[str, list["Fix"]]:
        """Return (fixed_source, list_of_fixes)."""

    @abc.abstractmethod
    def validate(self, path: Path, original: str, fixed: str) -> "ValidationResult":
        """Check that the fix didn't break anything."""


# Force-import concrete rules so they self-register.
from prefact.rules.relative_imports import RelativeToAbsoluteImports as _r1  # noqa: F401, E402
from prefact.rules.unused_imports import UnusedImports as _r2  # noqa: F401, E402
from prefact.rules.duplicate_imports import DuplicateImports as _r3  # noqa: F401, E402
from prefact.rules.wildcard_imports import WildcardImports as _r4  # noqa: F401, E402
from prefact.rules.sorted_imports import SortedImports as _r5  # noqa: F401, E402
from prefact.rules.string_concat import StringConcatToFstring as _r6  # noqa: F401, E402
from prefact.rules.print_statements import PrintStatements as _r7  # noqa: F401, E402
from prefact.rules.type_hints import MissingReturnType as _r8  # noqa: F401, E402
