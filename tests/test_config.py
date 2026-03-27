"""Tests for configuration loading and auto-detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from prefact.config import Config


@pytest.fixture
def project_with_pyproject(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "my-cool-app"\n'
    )
    pkg = tmp_path / "src" / "my_cool_app"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    return tmp_path


class TestConfig:
    def test_detect_from_pyproject(self, project_with_pyproject: Path) -> None:
        cfg = Config(project_root=project_with_pyproject)
        name = cfg.detect_package_name()
        assert name == "my_cool_app"

    def test_detect_from_src_layout(self, tmp_path: Path) -> None:
        pkg = tmp_path / "src" / "foobar"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        cfg = Config(project_root=tmp_path)
        assert cfg.detect_package_name() == "foobar"

    def test_detect_top_level_package(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mylib"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        cfg = Config(project_root=tmp_path)
        assert cfg.detect_package_name() == "mylib"

    def test_from_yaml(self, tmp_path: Path) -> None:
        yaml_content = """\
package_name: myapp
rules:
  relative-imports:
    enabled: true
    severity: error
  unused-imports: false
"""
        cfg_path = tmp_path / "prefact.yaml"
        cfg_path.write_text(yaml_content)
        cfg = Config.from_yaml(cfg_path)
        assert cfg.package_name == "myapp"
        assert cfg.rule_enabled("relative-imports") is True
        assert cfg.rule_enabled("unused-imports") is False

    def test_rule_defaults(self) -> None:
        cfg = Config()
        # All rules enabled by default
        assert cfg.rule_enabled("relative-imports") is True
        assert cfg.rule_enabled("nonexistent-rule") is True
        assert cfg.rule_options("nonexistent") == {}
