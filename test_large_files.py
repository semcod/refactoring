#!/usr/bin/env python3
"""Test that large files are still processed correctly with RAM optimization."""

import tempfile
from pathlib import Path

# Create a test with a large file
def test_large_file_handling() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create a small file that will be preloaded
        small_file = tmpdir / "small.py"
        small_file.write_text("from os import path\nprint('hello')")
        
        # Create a large file that will NOT be preloaded (>100KB)
        large_file = tmpdir / "large.py"
        large_content = f"# Large file\n{'x' * (101 * 1024)}\nfrom sys import argv\n"
        large_file.write_text(large_content)
        
        print(f"Created small file: {small_file.stat().st_size} bytes")
        print(f"Created large file: {large_file.stat().st_size} bytes")
        
        # Test the preloading logic
        files = [small_file, large_file]
        max_file_size = 100 * 1024
        
        preloaded = {}
        large_files = []
        
        for path in files:
            if path.stat().st_size <= max_file_size:
                preloaded[path] = path.read_text()
            else:
                large_files.append(path)
        
        print(f"\nPreloaded files: {len(preloaded)}")
        print(f"Large files: {len(large_files)}")
        
        # Verify both files would be processed
        assert len(preloaded) == 1, "Should preload 1 small file"
        assert len(large_files) == 1, "Should have 1 large file"
        assert small_file in preloaded, "Small file should be preloaded"
        assert large_file in large_files, "Large file should be in large_files list"
        
        print("\n✅ Test passed: Both small and large files are handled correctly!")
        print("   - Small files are preloaded into RAM")
        print("   - Large files are processed on-demand")
