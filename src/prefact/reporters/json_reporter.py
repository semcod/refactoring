"""JSON reporter – structured output for CI pipelines."""

from __future__ import annotations

import json
from pathlib import Path

from prefact.models import PipelineResult


def to_dict(result: PipelineResult) -> dict:
    return {
        "dry_run": result.dry_run,
        "summary": {
            "issues": result.total_issues,
            "fixed": result.total_fixed,
            "failed": result.total_failed,
            "all_valid": result.all_valid,
        },
        "issues": [
            {
                "rule": i.rule_id,
                "file": str(i.file),
                "line": i.line,
                "col": i.col,
                "severity": i.severity.value,
                "message": i.message,
                "original": i.original,
                "suggested": i.suggested,
            }
            for i in result.issues_found
        ],
        "fixes": [
            {
                "file": str(f.file),
                "original": f.original_code,
                "fixed": f.fixed_code,
                "applied": f.applied,
                "error": f.error,
            }
            for f in result.fixes_applied + result.fixes_failed
        ],
        "validations": [
            {
                "file": str(v.file),
                "passed": v.passed,
                "checks": v.checks,
                "errors": v.errors,
            }
            for v in result.validations
        ],
    }


def dump(result: PipelineResult, *, output: Path | None = None) -> str:
    text = json.dumps(to_dict(result), indent=2, ensure_ascii=False)
    if output:
        output.write_text(text, encoding="utf-8")
    return text
