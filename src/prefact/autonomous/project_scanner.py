"""Project scanning functionality for autonomous prefact."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, List, Tuple

from prefact.config_extended import ExtendedConfig
from prefact.engine import RefactoringEngine
from prefact.scanner import Scanner

from ._base import BaseManager, console, MIN_CODE_SIZE


class ProjectScanner(BaseManager):
    """Handles project scanning operations."""
    
    def __init__(self, project_root: Path):
        super().__init__(project_root)
        self.issues_found: List[Any] = []
    
    def scan_project(self) -> List[Any]:
        """Scan project for issues."""
        try:
            # Load configuration
            config = ExtendedConfig.from_yaml(self.refact_config_path)
            engine = RefactoringEngine(config)
            
            # Get list of files to scan
            scanner = Scanner(config)
            files_to_scan = list(scanner.collect_files())
            
            console.print(f"📂 Found {len(files_to_scan)} files to scan")
            
            # Show progress bar and scan files
            issues_found = self._scan_files_with_progress(scanner, files_to_scan, config)
            
            # Store issues for other modules
            self.issues_found = issues_found
            
            console.print(f"📊 Found {len(issues_found)} issues across {len(self.group_issues(issues_found))} categories")
            
            return issues_found
            
        except Exception as e:
            console.print(f"❌ Error scanning project: {e}", style="red")
            import traceback
            traceback.print_exc()
            self.issues_found = []
            return []
    
    def _scan_files_with_progress(self, scanner: Scanner, files_to_scan: List[Path], 
                                 config) -> List[Any]:
        """Scan files with progress tracking."""
        from rich.progress import Progress
        
        with Progress() as progress:
            scan_task = progress.add_task(
                "[cyan]Scanning files...", 
                total=len(files_to_scan),
                show_speed=True,
                show_eta=True,
                show_remaining=True
            )
            
            start_time = datetime.now()
            issues_found = []
            
            # Use parallel processing if enabled
            if config.tools.get('parallel', False) and len(files_to_scan) > 1:
                issues_found = self._scan_files_parallel(
                    scanner, files_to_scan, progress, scan_task, start_time, config
                )
            else:
                issues_found = self._scan_files_sequential(
                    scanner, files_to_scan, progress, scan_task, start_time
                )
            
            elapsed_time = (datetime.now() - start_time).total_seconds()
            console.print(f" in {elapsed_time:.1f}s")
            
            return issues_found
    
    def _scan_files_parallel(self, scanner: Scanner, files_to_scan: List[Path], 
                           progress, scan_task, start_time, config) -> List[Any]:
        """Scan files using parallel processing."""
        max_workers = min(config.performance.get('max_workers', 4), len(files_to_scan))
        console.print(f"🚀 Using parallel processing with {max_workers} workers")
        
        def scan_file(file_path: Path) -> Tuple[Path, List[Any]]:
            file_issues = []
            try:
                # Skip large files (>100KB) for speed
                if file_path.stat().st_size > 100 * 1024:
                    console.print(f"  ⏭️  Skipping large file: {file_path} ({file_path.stat().st_size // 1024}KB)")
                    return file_path, file_issues
                
                source = file_path.read_text(encoding="utf-8")
                
                # Skip files with no actual code (mostly comments/strings)
                if len(source.strip()) < MIN_CODE_SIZE:
                    return file_path, file_issues
                
                for rule in scanner._rules:
                    file_issues.extend(rule.scan_file(file_path, source))
            except Exception as e:
                console.print(f"  ⚠️ Error scanning {file_path}: {e}")
            return file_path, file_issues
        
        issues_found = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all files for scanning
            future_to_file = {executor.submit(scan_file, fp): fp for fp in files_to_scan}
            
            for future in as_completed(future_to_file):
                file_path, file_issues = future.result()
                issues_found.extend(file_issues)
                progress.update(scan_task, advance=1, description=f"[cyan]Scanning {file_path.name}")
        
        return issues_found
    
    def _scan_files_sequential(self, scanner: Scanner, files_to_scan: List[Path], 
                             progress, scan_task, start_time) -> List[Any]:
        """Scan files sequentially."""
        issues_found = []
        
        for i, file_path in enumerate(files_to_scan):
            # Update progress
            progress.update(scan_task, advance=1, description=f"[cyan]Scanning {file_path.name}")
            
            # Show current file every 10 files
            if i % 10 == 0 or i == len(files_to_scan) - 1:
                elapsed = (datetime.now() - start_time).total_seconds()
                if i > 0:
                    avg_time = elapsed / i
                    eta = avg_time * (len(files_to_scan) - i)
                    console.print(f"  📄 [{i+1}/{len(files_to_scan)}] {file_path} (ETA: {eta:.1f}s)")
            
            # Scan the file
            file_issues = self._scan_single_file(scanner, file_path)
            issues_found.extend(file_issues)
        
        return issues_found
    
    def _scan_single_file(self, scanner: Scanner, file_path: Path) -> List[Any]:
        """Scan a single file for issues."""
        try:
            # Skip large files (>100KB) for speed
            if file_path.stat().st_size > 100 * 1024:
                console.print(f"  ⏭️  Skipping large file: {file_path} ({file_path.stat().st_size // 1024}KB)")
                return []
            
            source = file_path.read_text(encoding="utf-8")
            
            # Skip files with no actual code (mostly comments/strings)
            if len(source.strip()) < MIN_CODE_SIZE:
                return []
            
            file_issues = []
            for rule in scanner._rules:
                file_issues.extend(rule.scan_file(file_path, source))
            
            return file_issues
        except Exception as e:
            console.print(f"  ⚠️ Error scanning {file_path}: {e}")
            return []
    
    def group_issues(self, issues: List[Any]) -> List[dict]:
        """Group issues by type and location."""
        grouped = {}
        
        for issue in issues:
            # Ensure file is a string
            file_path = str(issue.file) if hasattr(issue, 'file') else str(issue)
            rule_id = getattr(issue, 'rule_id', 'unknown')
            
            key = f"{rule_id}:{file_path}"
            if key not in grouped:
                grouped[key] = {
                    "rule_id": rule_id,
                    "file": file_path,
                    "count": 0,
                    "severity": issue.severity.value if hasattr(issue, 'severity') else "warning",
                    "examples": []
                }
            
            grouped[key]["count"] += 1
            if len(grouped[key]["examples"]) < 3:  # Limit examples
                grouped[key]["examples"].append({
                    "line": getattr(issue, 'line', 0),
                    "message": getattr(issue, 'message', 'No message')
                })
        
        return list(grouped.values())
