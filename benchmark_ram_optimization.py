#!/usr/bin/env python3
"""Benchmark script to measure performance gains from RAM preloading optimization.

This script creates test files and measures execution time with and without
RAM preloading to quantify the performance improvement.
"""

import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prefact.config import Config
from prefact.engine import RefactoringEngine

# Constants for benchmark configuration
SMALL_FILE_COUNT = 50
MEDIUM_FILE_COUNT = 100
LARGE_FILE_COUNT = 500
SMALL_FILE_SIZE = 1
MEDIUM_FILE_SIZE = 5
LARGE_FILE_SIZE = 10


def create_test_files(base_dir: Path, num_files: int = 100, file_size_kb: int = 1) -> List[Path]:
    """Create test Python files with import issues to benchmark against."""
    files = []
    
    # Create a simple Python template with import issues
    template = '''"""Test module {i}."""

# Some relative imports that need fixing
from ....module{i % 10} import function{i % 5}
from ..utils import helper

# Duplicate import
from os import path
from os import path

# Unused import
import sys

def main():
    """Main function."""
    return "hello"
'''

    for i in range(num_files):
        file_path = base_dir / f"test_module_{i:03d}.py"
        
        # Adjust content size if needed
        content = template.format(i=i)
        if file_size_kb > 1:
            # Add padding to increase file size
            padding = f"\n# {'x' * (file_size_kb * 1024 - len(content))}\n"
            content += padding
        
        file_path.write_text(content, encoding='utf-8')
        files.append(file_path)
    
    return files


def benchmark_without_rampreload(config: Config) -> float:
    """Run benchmark without RAM preloading (original implementation)."""
    # Create a modified engine that doesn't use preloading
    class OriginalRefactoringEngine(RefactoringEngine):
        def run(self, *, dry_run: bool | None = None) -> "PipelineResult":
            if dry_run is None:
                dry_run = self.config.dry_run

            from prefact.models import PipelineResult
            result = PipelineResult(dry_run=dry_run)

            # Phase 1 – Scan (original way, reads files)
            issues_map = self.scanner.scan()
            for file_issues in issues_map.values():
                result.issues_found.extend(file_issues)

            if not result.issues_found:
                return result

            # Phase 2 – Fix (reads files again)
            for path, issues in issues_map.items():
                original = path.read_text(encoding="utf-8")
                fixed_source, fixes = self.fixer.fix_file(path, issues, dry_run=dry_run)

                for fix in fixes:
                    (result.fixes_applied if fix.applied else result.fixes_failed).append(fix)

                # Phase 3 – Validate (reads files again)
                validations = self.validator.validate_file(path, original, fixed_source, issues)
                result.validations.extend(validations)

            return result
    
    engine = OriginalRefactoringEngine(config)
    
    start_time = time.perf_counter()
    result = engine.run(dry_run=True)  # Dry run to avoid modifying files
    end_time = time.perf_counter()
    
    return end_time - start_time


def benchmark_with_rampreload(config: Config) -> float:
    """Run benchmark with RAM preloading (optimized implementation)."""
    engine = RefactoringEngine(config)
    
    start_time = time.perf_counter()
    result = engine.run(dry_run=True)  # Dry run to avoid modifying files
    end_time = time.perf_counter()
    
    return end_time - start_time


def run_benchmark(num_files: int = 100, file_size_kb: int = 1) -> Dict[str, float]:
    """Run a complete benchmark comparing both implementations."""
    results = {}
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        
        print(f"Creating {num_files} test files ({file_size_kb}KB each)...")
        files = create_test_files(base_dir, num_files, file_size_kb)
        
        # Create config
        config = Config(
            project_root=base_dir,
            package_name="test_package",
            dry_run=True,
            verbose=False
        )
        
        # Benchmark without RAM preloading
        print("Running benchmark WITHOUT RAM preloading...")
        time_without = benchmark_without_rampreload(config)
        results['without_ram_preload'] = time_without
        print(f"  Time: {time_without:.4f} seconds")
        
        # Benchmark with RAM preloading
        print("Running benchmark WITH RAM preloading...")
        time_with = benchmark_with_rampreload(config)
        results['with_ram_preload'] = time_with
        print(f"  Time: {time_with:.4f} seconds")
        
        # Calculate improvement
        improvement = (time_without - time_with) / time_without * 100
        results['improvement_percent'] = improvement
        speedup = time_without / time_with
        results['speedup_factor'] = speedup
        
        print(f"\nResults:")
        print(f"  Without RAM preload: {time_without:.4f}s")
        print(f"  With RAM preload:    {time_with:.4f}s")
        print(f"  Improvement:         {improvement:.1f}%")
        print(f"  Speedup factor:      {speedup:.2f}x")
    
    return results


def main() -> None:
    """Run multiple benchmarks with different file counts and sizes."""
    print("=" * 60)
    print("PREFACT RAM PRELOADING BENCHMARK")
    print("=" * 60)
    
    test_cases = [
        (SMALL_FILE_COUNT, SMALL_FILE_SIZE),    # 50 files, 1KB each
        (MEDIUM_FILE_COUNT, SMALL_FILE_SIZE),   # 100 files, 1KB each
        (LARGE_FILE_COUNT, SMALL_FILE_SIZE),     # 500 files, 1KB each
        (MEDIUM_FILE_COUNT, MEDIUM_FILE_SIZE),   # 100 files, 5KB each
        (MEDIUM_FILE_COUNT, LARGE_FILE_SIZE),    # 100 files, 10KB each
        (1000, 1),  # 1000 files, 1KB each
    ]
    
    all_results = []
    
    for num_files, file_size_kb in test_cases:
        print(f"\nTest case: {num_files} files × {file_size_kb}KB")
        print("-" * 40)
        
        try:
            results = run_benchmark(num_files, file_size_kb)
            all_results.append({
                'num_files': num_files,
                'file_size_kb': file_size_kb,
                **results
            })
        except Exception as e:
            print(f"Error in benchmark: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print(f"\n{'=' * 60}")
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"{'Files':<6} {'Size':<6} {'Without':<10} {'With':<10} {'Improvement':<12} {'Speedup':<8}")
    print("-" * 60)
    
    for result in all_results:
        print(f"{result['num_files']:<6} {result['file_size_kb']:<6}KB "
              f"{result['without_ram_preload']:<10.4f}s {result['with_ram_preload']:<10.4f}s "
              f"{result['improvement_percent']:<12.1f}% {result['speedup_factor']:<8.2f}x")
    
    # Average improvement
    if all_results:
        avg_improvement = sum(r['improvement_percent'] for r in all_results) / len(all_results)
        avg_speedup = sum(r['speedup_factor'] for r in all_results) / len(all_results)
        print("-" * 60)
        print(f"Average improvement: {avg_improvement:.1f}%")
        print(f"Average speedup:     {avg_speedup:.2f}x")
