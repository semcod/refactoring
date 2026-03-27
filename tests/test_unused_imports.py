"""Tests for the unused-imports rule."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from prefact.config import Config
from prefact.rules.unused_imports import UnusedImports


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(project_root=tmp_path)


class TestScanUnused:
    def test_detects_unused(self, config: Config) -> None:
        source = textwrap.dedent("""\
            import os
            import sys

            print("hello")
        """)
        rule = UnusedImports(config)
        issues = rule.scan_file(config.project_root / "x.py", source)
        names = {i.original for i in issues}
        assert "os" in names
        assert "sys" in names

    def test_used_import_not_flagged(self, config: Config) -> None:
        source = 'import os\n\nos.path.join("a", "b")\n'
        rule = UnusedImports(config)
        assert rule.scan_file(config.project_root / "x.py", source) == []

    def test_respects_all_exports(self, config: Config) -> None:
        source = 'from foo import bar\n\n__all__ = ["bar"]\n'
        rule = UnusedImports(config)
        assert rule.scan_file(config.project_root / "x.py", source) == []

    def test_skips_underscore_imports(self, config: Config) -> None:
        source = "from foo import _private\n"
        rule = UnusedImports(config)
        assert rule.scan_file(config.project_root / "x.py", source) == []

    def test_attribute_access_counts_as_used(self, config: Config) -> None:
        source = "import json\n\njson.dumps({})\n"
        rule = UnusedImports(config)
        assert rule.scan_file(config.project_root / "x.py", source) == []


class TestFixUnused:
    def test_removes_unused_line(self, config: Config) -> None:
        source = textwrap.dedent("""\
            import os
            import sys

            print(sys.argv)
        """)
        rule = UnusedImports(config)
        issues = rule.scan_file(config.project_root / "x.py", source)
        fixed, fixes = rule.fix(config.project_root / "x.py", source, issues)
        assert "import os" not in fixed
        assert "import sys" in fixed
        assert len(fixes) >= 1
