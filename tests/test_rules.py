"""Tests for additional rules."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from prefact.config import Config
from prefact.rules.duplicate_imports import DuplicateImports
from prefact.rules.wildcard_imports import WildcardImports
from prefact.rules.string_concat import StringConcatToFstring
from prefact.rules.print_statements import PrintStatements
from prefact.rules.type_hints import MissingReturnType
from prefact.rules.sorted_imports import SortedImports


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(project_root=tmp_path)


# ── DuplicateImports ─────────────────────────────────────────────────


class TestDuplicateImports:
    def test_detects_duplicate(self, config: Config) -> None:
        source = textwrap.dedent("""\
            from os.path import join
            from shutil import copy
            from os.path import join
        """)
        rule = DuplicateImports(config)
        issues = rule.scan_file(config.project_root / "x.py", source)
        assert len(issues) == 1
        assert "join" in issues[0].message

    def test_no_duplicates(self, config: Config) -> None:
        source = "import os\nimport sys\n"
        rule = DuplicateImports(config)
        assert rule.scan_file(config.project_root / "x.py", source) == []

    def test_fix_removes_duplicate_line(self, config: Config) -> None:
        source = "from os.path import join\nfrom os.path import join\n"
        rule = DuplicateImports(config)
        issues = rule.scan_file(config.project_root / "x.py", source)
        fixed, fixes = rule.fix(config.project_root / "x.py", source, issues)
        assert fixed.count("join") == 1
        assert len(fixes) == 1


# ── WildcardImports ──────────────────────────────────────────────────


class TestWildcardImports:
    def test_detects_wildcard(self, config: Config) -> None:
        source = "from os.path import *\n"
        rule = WildcardImports(config)
        issues = rule.scan_file(config.project_root / "x.py", source)
        assert len(issues) == 1
        assert "Wildcard" in issues[0].message

    def test_no_autofix(self, config: Config) -> None:
        source = "from os.path import *\n"
        rule = WildcardImports(config)
        issues = rule.scan_file(config.project_root / "x.py", source)
        fixed, fixes = rule.fix(config.project_root / "x.py", source, issues)
        assert fixed == source
        assert fixes == []


# ── StringConcatToFstring ────────────────────────────────────────────


class TestStringConcat:
    def test_detects_concat(self, config: Config) -> None:
        source = textwrap.dedent("""\
            name = "world"
            msg = "Hello " + name + "!"
        """)
        rule = StringConcatToFstring(config)
        issues = rule.scan_file(config.project_root / "x.py", source)
        assert len(issues) >= 1
        assert "f-string" in issues[0].message

    def test_ignores_pure_string_concat(self, config: Config) -> None:
        source = 'msg = "Hello " + "world"\n'
        rule = StringConcatToFstring(config)
        issues = rule.scan_file(config.project_root / "x.py", source)
        assert len(issues) == 0

    def test_ignores_numeric_add(self, config: Config) -> None:
        source = "x = 1 + 2\n"
        rule = StringConcatToFstring(config)
        issues = rule.scan_file(config.project_root / "x.py", source)
        assert len(issues) == 0


# ── PrintStatements ──────────────────────────────────────────────────


class TestPrintStatements:
    def test_detects_print(self, config: Config) -> None:
        source = textwrap.dedent("""\
            def run():
                print("debug info")
                return 42
        """)
        rule = PrintStatements(config)
        issues = rule.scan_file(config.project_root / "x.py", source)
        assert len(issues) == 1
        assert "print()" in issues[0].message

    def test_no_print_no_issue(self, config: Config) -> None:
        source = "def run():\n    return 42\n"
        rule = PrintStatements(config)
        assert rule.scan_file(config.project_root / "x.py", source) == []


# ── MissingReturnType ────────────────────────────────────────────────


class TestMissingReturnType:
    def test_detects_missing(self, config: Config) -> None:
        source = textwrap.dedent("""\
            def hello():
                return "hi"
        """)
        rule = MissingReturnType(config)
        issues = rule.scan_file(config.project_root / "x.py", source)
        assert len(issues) == 1
        assert "hello" in issues[0].message

    def test_has_return_type(self, config: Config) -> None:
        source = 'def hello() -> str:\n    return "hi"\n'
        rule = MissingReturnType(config)
        assert rule.scan_file(config.project_root / "x.py", source) == []

    def test_skips_private(self, config: Config) -> None:
        source = "def _private():\n    pass\n"
        rule = MissingReturnType(config)
        assert rule.scan_file(config.project_root / "x.py", source) == []


# ── SortedImports ────────────────────────────────────────────────────


class TestSortedImports:
    def test_detects_unsorted(self, config: Config) -> None:
        source = textwrap.dedent("""\
            from mypackage import foo
            import os
        """)
        rule = SortedImports(config)
        issues = rule.scan_file(config.project_root / "x.py", source)
        assert len(issues) == 1
        assert "not sorted" in issues[0].message

    def test_sorted_ok(self, config: Config) -> None:
        source = "import os\nimport sys\n"
        rule = SortedImports(config)
        assert rule.scan_file(config.project_root / "x.py", source) == []
