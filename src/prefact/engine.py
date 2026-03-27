"""Engine – orchestrates the full scan → fix → validate pipeline."""

from pathlib import Path

from prefact.config import Config
from prefact.fixer import Fixer
from prefact.models import PipelineResult
from prefact.scanner import Scanner
from prefact.validator import Validator


class RefactoringEngine:
    """Main entry point: scan the project, apply fixes, validate results."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.scanner = Scanner(config)
        self.fixer = Fixer(config)
        self.validator = Validator(config)

    def run(self, *, dry_run: bool | None = None) -> PipelineResult:
        if dry_run is None:
            dry_run = self.config.dry_run

        result = PipelineResult(dry_run=dry_run)

        # Phase 1 – Scan
        issues_map = self.scanner.scan()
        for file_issues in issues_map.values():
            result.issues_found.extend(file_issues)

        if not result.issues_found:
            return result

        # Phase 2 – Fix
        for path, issues in issues_map.items():
            original = path.read_text(encoding="utf-8")
            fixed_source, fixes = self.fixer.fix_file(path, issues, dry_run=dry_run)

            for fix in fixes:
                (result.fixes_applied if fix.applied else result.fixes_failed).append(fix)

            # Phase 3 – Validate
            validations = self.validator.validate_file(path, original, fixed_source, issues)
            result.validations.extend(validations)

        return result

    def scan_only(self) -> PipelineResult:
        result = PipelineResult(dry_run=True)
        issues_map = self.scanner.scan()
        for file_issues in issues_map.values():
            result.issues_found.extend(file_issues)
        return result

    def run_file(self, path: Path, *, dry_run: bool = False) -> PipelineResult:
        result = PipelineResult(dry_run=dry_run)
        issues_map = self.scanner.scan([path])
        issues = issues_map.get(path, [])
        result.issues_found.extend(issues)

        if not issues:
            return result

        original = path.read_text(encoding="utf-8")
        fixed_source, fixes = self.fixer.fix_file(path, issues, dry_run=dry_run)
        for fix in fixes:
            (result.fixes_applied if fix.applied else result.fixes_failed).append(fix)

        validations = self.validator.validate_file(path, original, fixed_source, issues)
        result.validations.extend(validations)
        return result
