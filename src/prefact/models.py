"""Data models for the pprefact pipeline."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class Severity(enum.Enum):
    """How critical an issue is."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Phase(enum.Enum):
    """Pipeline phase."""

    SCAN = "scan"
    FIX = "fix"
    VALIDATE = "validate"


@dataclass
class Issue:
    """A single detected problem in the codebase."""

    rule_id: str
    file: Path
    line: int
    col: int
    message: str
    severity: Severity = Severity.WARNING
    original: str = ""
    suggested: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def location(self) -> str:
        return f"{self.file}:{self.line}:{self.col}"


@dataclass
class Fix:
    """A concrete code change to apply."""

    issue: Issue
    file: Path
    original_code: str
    fixed_code: str
    applied: bool = False
    error: str | None = None


@dataclass
class ValidationResult:
    """Result of post-fix validation."""

    file: Path
    passed: bool
    checks: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Aggregate result of the full scan → fix → validate pipeline."""

    issues_found: list[Issue] = field(default_factory=list)
    fixes_applied: list[Fix] = field(default_factory=list)
    fixes_failed: list[Fix] = field(default_factory=list)
    validations: list[ValidationResult] = field(default_factory=list)
    dry_run: bool = False

    @property
    def total_issues(self) -> int:
        return len(self.issues_found)

    @property
    def total_fixed(self) -> int:
        return len(self.fixes_applied)

    @property
    def total_failed(self) -> int:
        return len(self.fixes_failed)

    @property
    def all_valid(self) -> bool:
        return all(v.passed for v in self.validations)
