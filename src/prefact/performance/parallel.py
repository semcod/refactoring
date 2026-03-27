"""Parallel processing engine for pprefact.

This module provides multiprocessing capabilities to scan multiple files
in parallel, significantly improving performance on large codebases.
"""

from __future__ import annotations

import hashlib
import multiprocessing
import os
import pickle
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from prefact.config import Config
from prefact.engine import RefactoringEngine
from prefact.models import Issue, ScanResult


class ParallelScanTask:
    """A task for parallel scanning."""
    
    def __init__(
        self,
        file_path: Path,
        config_dict: Dict[str, Any],
        rule_ids: List[str],
        cache_enabled: bool = True
    ):
        self.file_path = file_path
        self.config_dict = config_dict
        self.rule_ids = rule_ids
        self.cache_enabled = cache_enabled
        self.file_hash = self._calculate_file_hash()
    
    def _calculate_file_hash(self) -> str:
        """Calculate hash of file content for cache key."""
        try:
            with open(self.file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def execute(self) -> ScanResult:
        """Execute the scan task."""
        # Check cache first if enabled
        if self.cache_enabled:
            from prefact.performance.cache import get_cache
            cache = get_cache()
            cache_key = f"scan:{self.file_path}:{self.file_hash}:{hash(tuple(self.rule_ids))}"
            
            cached_result = cache.get(cache_key)
            if cached_result:
                return pickle.loads(cached_result)
        
        # Perform actual scan
        config = Config.from_dict(self.config_dict)
        engine = RefactoringEngine(config)
        
        result = engine.scan_file(self.file_path, self.rule_ids)
        
        # Cache result if enabled
        if self.cache_enabled:
            cache.set(cache_key, pickle.dumps(result), expire=3600)  # 1 hour
        
        return result


class ParallelEngine:
    """Parallel processing engine for pprefact."""
    
    def __init__(self, config: Config):
        self.config = config
        self.max_workers = config.get_rule_option(
            "_performance", 
            "max_workers", 
            min(multiprocessing.cpu_count(), 8)
        )
        self.chunk_size = config.get_rule_option(
            "_performance", 
            "chunk_size", 
            10
        )
        self.cache_enabled = config.get_rule_option(
            "_performance", 
            "cache", 
            True
        )
    
    def scan_files(
        self, 
        file_paths: List[Path], 
        rule_ids: Optional[List[str]] = None
    ) -> List[ScanResult]:
        """Scan multiple files in parallel."""
        if not file_paths:
            return []
        
        # Use all enabled rules if none specified
        if rule_ids is None:
            rule_ids = self._get_enabled_rule_ids()
        
        # Create tasks
        tasks = [
            ParallelScanTask(
                path, 
                self.config.to_dict(), 
                rule_ids,
                self.cache_enabled
            )
            for path in file_paths
        ]
        
        # Decide execution method based on number of files
        if len(tasks) == 1:
            # Single file - no need for parallel processing
            return [tasks[0].execute()]
        elif len(tasks) <= self.chunk_size:
            # Small batch - use thread pool for faster startup
            return self._scan_with_thread_pool(tasks)
        else:
            # Large batch - use process pool for true parallelism
            return self._scan_with_process_pool(tasks)
    
    def _scan_with_thread_pool(self, tasks: List[ParallelScanTask]) -> List[ScanResult]:
        """Scan using thread pool (for small batches)."""
        results = []
        
        with ProcessPoolExecutor(max_workers=min(self.max_workers, len(tasks))) as executor:
            future_to_task = {
                executor.submit(self._execute_task_wrapper, task): task
                for task in tasks
            }
            
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    # Create error result
                    error_result = ScanResult(
                        file=task.file_path,
                        issues=[],
                        fixes=[],
                        errors=[str(e)]
                    )
                    results.append(error_result)
        
        return results
    
    def _scan_with_process_pool(self, tasks: List[ParallelScanTask]) -> List[ScanResult]:
        """Scan using process pool (for large batches)."""
        results = []
        
        # Process in chunks to avoid memory issues
        for i in range(0, len(tasks), self.chunk_size):
            chunk = tasks[i:i + self.chunk_size]
            
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_task = {
                    executor.submit(self._execute_task_wrapper, task): task
                    for task in chunk
                }
                
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        # Create error result
                        error_result = ScanResult(
                            file=task.file_path,
                            issues=[],
                            fixes=[],
                            errors=[str(e)]
                        )
                        results.append(error_result)
        
        return results
    
    @staticmethod
    def _execute_task_wrapper(task: ParallelScanTask) -> ScanResult:
        """Wrapper for executing tasks in separate process."""
        return task.execute()
    
    def _get_enabled_rule_ids(self) -> List[str]:
        """Get list of enabled rule IDs."""
        from prefact.rules.registry import get_lazy_registry
        registry = get_lazy_registry()
        
        enabled_rules = []
        for rule_id in registry.list_available_rules():
            if self.config.is_rule_enabled(rule_id):
                enabled_rules.append(rule_id)
        
        return enabled_rules
    
    def fix_files(
        self, 
        file_paths: List[Path], 
        rule_ids: Optional[List[str]] = None
    ) -> List[ScanResult]:
        """Fix multiple files in parallel."""
        # For fixing, we need to be more careful about file conflicts
        # So we'll process sequentially but in parallel for scanning
        results = []
        
        for file_path in file_paths:
            try:
                config = Config.from_dict(self.config.to_dict())
                engine = RefactoringEngine(config)
                result = engine.run_file(file_path, rule_ids)
                results.append(result)
            except Exception as e:
                error_result = ScanResult(
                    file=file_path,
                    issues=[],
                    fixes=[],
                    errors=[str(e)]
                )
                results.append(error_result)
        
        return results


class ParallelScanner:
    """High-level interface for parallel scanning."""
    
    def __init__(self, config: Config):
        self.config = config
        self.engine = ParallelEngine(config)
    
    def scan_directory(
        self, 
        directory: Path, 
        pattern: str = "**/*.py",
        rule_ids: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[ScanResult]:
        """Scan all Python files in a directory."""
        if exclude_patterns is None:
            exclude_patterns = self.config.exclude
        
        # Find all Python files
        file_paths = []
        for pattern in self.config.include:
            for file_path in directory.glob(pattern):
                if file_path.is_file():
                    # Check exclude patterns
                    if not any(file_path.match(exclude) for exclude in exclude_patterns):
                        file_paths.append(file_path)
        
        # Scan in parallel
        return self.engine.scan_files(file_paths, rule_ids)
    
    def scan_workspace(
        self, 
        rule_ids: Optional[List[str]] = None
    ) -> List[ScanResult]:
        """Scan the entire workspace."""
        return self.scan_directory(self.config.project_root, rule_ids=rule_ids)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "max_workers": self.engine.max_workers,
            "chunk_size": self.engine.chunk_size,
            "cache_enabled": self.engine.cache_enabled,
            "cpu_count": multiprocessing.cpu_count(),
        }


# Utility functions for multiprocessing
def init_worker():
    """Initialize worker process."""
    # Set up worker-specific configuration
    os.environ['PREFACT_WORKER'] = '1'


def scan_file_worker(args: Tuple[Path, Dict[str, Any], List[str]]) -> ScanResult:
    """Worker function for scanning a single file."""
    file_path, config_dict, rule_ids = args
    
    config = Config.from_dict(config_dict)
    engine = RefactoringEngine(config)
    
    return engine.scan_file(file_path, rule_ids)


# Performance monitoring
class PerformanceMonitor:
    """Monitor performance of parallel operations."""
    
    def __init__(self):
        self.stats = {
            "files_scanned": 0,
            "total_time": 0,
            "parallel_time": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
    
    def start_timing(self):
        """Start timing an operation."""
        self.start_time = time.time()
    
    def end_timing(self, files_scanned: int):
        """End timing an operation."""
        elapsed = time.time() - self.start_time
        self.stats["files_scanned"] += files_scanned
        self.stats["total_time"] += elapsed
    
    def record_cache_hit(self):
        """Record a cache hit."""
        self.stats["cache_hits"] += 1
    
    def record_cache_miss(self):
        """Record a cache miss."""
        self.stats["cache_misses"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = self.stats.copy()
        
        if stats["files_scanned"] > 0:
            stats["avg_time_per_file"] = stats["total_time"] / stats["files_scanned"]
            stats["files_per_second"] = stats["files_scanned"] / stats["total_time"] if stats["total_time"] > 0 else 0
        
        total_cache_operations = stats["cache_hits"] + stats["cache_misses"]
        if total_cache_operations > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / total_cache_operations
        
        return stats


# Global performance monitor
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor
