"""Tests for the engine (full scan → fix → validate pipeline)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from prefact.config import Config
from prefact.engine import RefactoringEngine


@pytest.fixture
def project(tmp_path: Path) -> Path:
    pkg = tmp_path / "src" / "myapp"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "core").mkdir()
    (pkg / "core" / "__init__.py").write_text("")
    (pkg / "utils").mkdir()
    (pkg / "utils" / "__init__.py").write_text("")
    (pkg / "utils" / "helpers.py").write_text("def helper(): pass")

    module = pkg / "core" / "service.py"
    module.write_text(
        textwrap.dedent("""\
            import os
            import json
            from ..utils.helpers import helper
            from ..utils.helpers import helper as h2

            def run():
                helper()
        """)
    )
    return tmp_path


class TestEngine:
    def test_scan_only(self, project: Path) -> None:
        cfg = Config(project_root=project, package_name="myapp")
        engine = RefactoringEngine(cfg)
        result = engine.scan_only()
        assert result.total_issues > 0
        rule_ids = {i.rule_id for i in result.issues_found}
        assert "relative-imports" in rule_ids

    def test_full_pipeline_dry_run(self, project: Path) -> None:
        cfg = Config(project_root=project, package_name="myapp")
        engine = RefactoringEngine(cfg)
        result = engine.run(dry_run=True)
        assert result.dry_run is True
        assert result.total_issues > 0
        # Dry-run: file should be unchanged
        source = (project / "src" / "myapp" / "core" / "service.py").read_text()
        assert "from ..utils" in source

    def test_full_pipeline_apply(self, project: Path) -> None:
        cfg = Config(project_root=project, package_name="myapp", backup=False)
        engine = RefactoringEngine(cfg)
        result = engine.run(dry_run=False)
        assert result.total_fixed > 0
        source = (project / "src" / "myapp" / "core" / "service.py").read_text()
        assert "from myapp.utils.helpers import helper" in source
        assert "from .." not in source

    def test_run_single_file(self, project: Path) -> None:
        cfg = Config(project_root=project, package_name="myapp")
        engine = RefactoringEngine(cfg)
        target = project / "src" / "myapp" / "core" / "service.py"
        result = engine.run_file(target, dry_run=True)
        assert result.total_issues > 0

    def test_backup_created(self, project: Path) -> None:
        cfg = Config(project_root=project, package_name="myapp", backup=True)
        engine = RefactoringEngine(cfg)
        target = project / "src" / "myapp" / "core" / "service.py"
        engine.run_file(target, dry_run=False)
        assert target.with_suffix(".py.bak").exists()

    def test_clean_project_no_issues(self, tmp_path: Path) -> None:
        pkg = tmp_path / "src" / "cleanapp"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "main.py").write_text(
            textwrap.dedent("""\
                import os

                def run() -> None:
                    os.getcwd()
            """)
        )
        cfg = Config(project_root=tmp_path, package_name="cleanapp")
        engine = RefactoringEngine(cfg)
        result = engine.scan_only()
        # Should find zero or minimal issues (maybe sorted-imports)
        auto_fixable = [i for i in result.issues_found if i.rule_id in ("relative-imports", "unused-imports", "duplicate-imports")]
        assert len(auto_fixable) == 0
