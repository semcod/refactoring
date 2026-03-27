"""Tests for the relative-imports rule."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from prefact.config import Config
from prefact.models import Severity
from prefact.rules.relative_imports import RelativeToAbsoluteImports


@pytest.fixture
def config(tmp_path: Path) -> Config:
    pkg = tmp_path / "src" / "planfile"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "llm").mkdir()
    (pkg / "llm" / "__init__.py").write_text("")
    (pkg / "llm" / "generator.py").write_text("def generate_strategy(): ...")
    (pkg / "loaders").mkdir()
    (pkg / "loaders" / "__init__.py").write_text("")
    (pkg / "loaders" / "yaml_loader.py").write_text("def save_strategy_yaml(): ...")
    (pkg / "cli").mkdir()
    (pkg / "cli" / "__init__.py").write_text("")
    return Config(project_root=tmp_path, package_name="planfile")


class TestScan:
    def test_detects_relative_imports(self, config: Config) -> None:
        source = textwrap.dedent("""\
            from ....llm.generator import generate_strategy
            from ....loaders.yaml_loader import save_strategy_yaml
            import os
        """)
        rule = RelativeToAbsoluteImports(config)
        path = config.project_root / "src" / "planfile" / "cli" / "commands.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)

        issues = rule.scan_file(path, source)
        assert len(issues) == 2
        assert all(i.rule_id == "relative-imports" for i in issues)
        assert issues[0].severity == Severity.WARNING
        assert "level=4" in issues[0].message

    def test_ignores_absolute_imports(self, config: Config) -> None:
        source = "from planfile.llm.generator import generate_strategy\nimport os\n"
        rule = RelativeToAbsoluteImports(config)
        path = config.project_root / "src" / "planfile" / "cli" / "commands.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
        assert rule.scan_file(path, source) == []

    def test_handles_syntax_error_gracefully(self, config: Config) -> None:
        source = "from . import (\n"
        rule = RelativeToAbsoluteImports(config)
        path = config.project_root / "src" / "planfile" / "bad.py"
        assert rule.scan_file(path, source) == []


class TestFix:
    def test_converts_single_dot_import(self, config: Config) -> None:
        source = "from .utils import helper\n"
        rule = RelativeToAbsoluteImports(config)
        path = config.project_root / "src" / "planfile" / "cli" / "commands.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)

        issues = rule.scan_file(path, source)
        fixed, fixes = rule.fix(path, source, issues)
        assert "from planfile.cli.utils import helper" in fixed
        assert len(fixes) >= 1

    def test_converts_deep_relative_import(self, config: Config) -> None:
        source = "from ...llm.generator import generate_strategy\n"
        rule = RelativeToAbsoluteImports(config)
        path = config.project_root / "src" / "planfile" / "cli" / "sub" / "deep.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)

        issues = rule.scan_file(path, source)
        fixed, fixes = rule.fix(path, source, issues)
        assert "from planfile.llm.generator import generate_strategy" in fixed

    def test_preserves_absolute_imports(self, config: Config) -> None:
        source = textwrap.dedent("""\
            from planfile.llm.generator import generate_strategy
            from .utils import helper
        """)
        rule = RelativeToAbsoluteImports(config)
        path = config.project_root / "src" / "planfile" / "cli" / "commands.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)

        issues = rule.scan_file(path, source)
        fixed, _ = rule.fix(path, source, issues)
        assert "from planfile.llm.generator import generate_strategy" in fixed
        assert "from planfile.cli.utils import helper" in fixed

    def test_no_fix_without_package_name(self, tmp_path: Path) -> None:
        # Use a bare temp dir with no detectable package
        cfg = Config(project_root=tmp_path, package_name="")
        source = "from .utils import helper\n"
        rule = RelativeToAbsoluteImports(cfg)
        path = tmp_path / "some" / "module.py"
        issues = rule.scan_file(path, source)
        fixed, fixes = rule.fix(path, source, issues)
        assert fixed == source
        assert fixes == []


class TestValidate:
    def test_valid_after_fix(self, config: Config) -> None:
        original = "from .utils import helper\n"
        fixed = "from planfile.cli.utils import helper\n"
        rule = RelativeToAbsoluteImports(config)
        path = config.project_root / "src" / "planfile" / "cli" / "commands.py"

        result = rule.validate(path, original, fixed)
        assert result.passed
        assert "syntax_valid" in result.checks
        assert "no_relative_imports" in result.checks
        assert "import_count_preserved" in result.checks

    def test_invalid_if_relative_remains(self, config: Config) -> None:
        original = "from .utils import helper\n"
        fixed = "from .utils import helper\n"
        rule = RelativeToAbsoluteImports(config)
        path = config.project_root / "src" / "planfile" / "cli" / "commands.py"

        result = rule.validate(path, original, fixed)
        assert not result.passed
