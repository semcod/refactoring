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

        # Collect all files first
        files = self.scanner.collect_files()
        if not files:
            return result

        # Preload small files into RAM to avoid multiple I/O operations
        sources = self._preload_sources(files)
        
        # Separate files that weren't preloaded (large files)
        large_files = [f for f in files if f not in sources]

        # Phase 1 – Scan (using preloaded sources for small files, direct read for large)
        issues_map = {}
        if sources:
            issues_map.update(self.scanner.scan_sources(sources))
        if large_files:
            issues_map.update(self.scanner.scan(large_files))
            
        for file_issues in issues_map.values():
            result.issues_found.extend(file_issues)

        if not result.issues_found:
            return result

        # Phase 2 – Fix (using preloaded sources when available)
        for path, issues in issues_map.items():
            if path in sources:
                original = sources[path]
                fixed_source, fixes = self.fixer.fix_file_with_source(path, original, issues, dry_run=dry_run)
            else:
                # Large file - read directly (always need original for validation)
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
        
        # Collect all files first
        files = self.scanner.collect_files()
        if not files:
            return result
            
        # Preload small files into RAM
        sources = self._preload_sources(files)
        
        # Separate files that weren't preloaded (large files)
        large_files = [f for f in files if f not in sources]
        
        # Scan both preloaded and large files
        issues_map = {}
        if sources:
            issues_map.update(self.scanner.scan_sources(sources))
        if large_files:
            issues_map.update(self.scanner.scan(large_files))
            
        for file_issues in issues_map.values():
            result.issues_found.extend(file_issues)
            
        return result

    def run_file(self, path: Path, *, dry_run: bool = False) -> PipelineResult:
        result = PipelineResult(dry_run=dry_run)
        
        # For single file, just load it directly
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return result
            
        sources = {path: source}
        issues_map = self.scanner.scan_sources(sources)
        issues = issues_map.get(path, [])
        result.issues_found.extend(issues)

        if not issues:
            return result

        fixed_source, fixes = self.fixer.fix_file_with_source(path, source, issues, dry_run=dry_run)
        for fix in fixes:
            (result.fixes_applied if fix.applied else result.fixes_failed).append(fix)

        validations = self.validator.validate_file(path, source, fixed_source, issues)
        result.validations.extend(validations)
        return result
    
    def _preload_sources(self, files: list[Path] | None = None) -> dict[Path, str]:
        """Preload small file sources into RAM to avoid multiple I/O operations.
        
        Returns a dictionary mapping file paths to their contents.
        Only loads files under 100KB to avoid excessive memory usage.
        
        Args:
            files: List of files to preload. If None, collects all files.
        """
        sources = {}
        max_file_size = 100 * 1024  # 100KB
        
        # Collect files if not provided
        if files is None:
            files = self.scanner.collect_files()
        
        # Load file contents into RAM
        for path in files:
            try:
                # Skip files larger than 100KB
                if path.stat().st_size > max_file_size:
                    if self.config.verbose:
                        print(f"Skipping large file (>{max_file_size//1024}KB): {path}")
                    continue
                    
                source = path.read_text(encoding="utf-8")
                sources[path] = source
            except (OSError, UnicodeDecodeError):
                # Skip files that can't be read
                continue
                
        if self.config.verbose:
            total_files = len(files) if files else 0
            preloaded_count = len(sources)
            total_bytes = sum(len(s) for s in sources.values())
            print(f"Preloaded {preloaded_count}/{total_files} files into RAM ({total_bytes} bytes)")
            
        return sources
