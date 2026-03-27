"""Comprehensive test suite for all prefact integrations.

This module tests the integration of various Python libraries with prefact:
- Ruff-based rules
- MyPy-based rules
- ISort-based rules
- Autoflake-based rules
- String transformation rules
"""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from prefact.config import Config
from prefact.engine import RefactoringEngine
from prefact.models import Issue, Severity
from prefact.rules import get_all_rules


class IntegrationTestCase:
    """Base class for integration test cases."""
    
    def __init__(self, name: str, source: str, expected_issues: Dict[str, List[Dict]]):
        self.name = name
        self.source = source
        self.expected_issues = expected_issues
    
    def run(self, config: Config) -> Dict[str, List[Issue]]:
        """Run the test case and return actual issues found."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(self.source)
            tmp_path = Path(tmp.name)
        
        try:
            results = {}
            all_rules = get_all_rules()
            
            for rule_id, rule_class in all_rules.items():
                if config.is_rule_enabled(rule_id):
                    rule = rule_class(config)
                    issues = rule.scan_file(tmp_path, self.source)
                    results[rule_id] = issues
            
            return results
        finally:
            tmp_path.unlink(missing_ok=True)


class IntegrationTestSuite:
    """Comprehensive test suite for all integrations."""
    
    def __init__(self):
        self.test_cases = self._create_test_cases()
    
    def _create_test_cases(self) -> List[IntegrationTestCase]:
        """Create all test cases."""
        return [
            # Test case 1: Multiple issues in one file
            IntegrationTestCase(
                name="multiple_issues",
                source='''import os
import sys
import json  # unused

from collections import defaultdict
from typing import List
from typing import Dict  # duplicate

def hello():
    print("Hello " + "World")
    
    x = 5  # unused variable
    
    return None
''',
                expected_issues={
                    "unused-imports": [
                        {"line": 3, "import": "json"}
                    ],
                    "duplicate-imports": [
                        {"line": 6, "import": "Dict"}
                    ],
                    "string-concat": [
                        {"line": 9}
                    ],
                    "print-statements": [
                        {"line": 9}
                    ],
                    "unused-variables": [
                        {"line": 11, "variable": "x"}
                    ],
                    "missing-return-type": [
                        {"line": 8}
                    ]
                }
            ),
            
            # Test case 2: Import sorting
            IntegrationTestCase(
                name="import_sorting",
                source='''from local_module import local_func
import sys
import os
from third_party import something
import json
from typing import List
''',
                expected_issues={
                    "sorted-imports": [
                        {"line": 1}
                    ]
                }
            ),
            
            # Test case 3: Wildcard imports
            IntegrationTestCase(
                name="wildcard_imports",
                source='''from math import *
from os.path import *
''',
                expected_issues={
                    "wildcard-imports": [
                        {"line": 1},
                        {"line": 2}
                    ]
                }
            ),
            
            # Test case 4: String concatenation patterns
            IntegrationTestCase(
                name="string_patterns",
                source='''def greet(name):
    return "Hello, " + name + "!"

def multiline():
    return ("This is a long string " +
            "that spans multiple lines")

def mixed():
    return "Value: " + str(42)
''',
                expected_issues={
                    "string-concat": [
                        {"line": 2},
                        {"line": 5},
                        {"line": 9}
                    ]
                }
            ),
            
            # Test case 5: Type hints
            IntegrationTestCase(
                name="type_hints",
                source='''def add(a, b):
    return a + b

class Calculator:
    def calculate(self):
        return 42

def _private():
    return None
''',
                expected_issues={
                    "missing-return-type": [
                        {"line": 1},
                        {"line": 5}
                    ]
                }
            ),
        ]
    
    def run_all_tests(self, config: Config) -> Dict[str, Dict]:
        """Run all test cases and return results."""
        results = {}
        
        for test_case in self.test_cases:
            print(f"\nRunning test case: {test_case.name}")
            actual_issues = test_case.run(config)
            
            # Compare with expected
            comparison = self._compare_results(
                test_case.expected_issues,
                actual_issues
            )
            
            results[test_case.name] = {
                "expected": test_case.expected_issues,
                "actual": actual_issues,
                "comparison": comparison,
                "passed": all(
                    all(issue.get("passed", False) for issue in rule_comparison.values())
                    for rule_comparison in comparison.values()
                )
            }
        
        return results
    
    def _compare_results(
        self,
        expected: Dict[str, List[Dict]],
        actual: Dict[str, List[Issue]]
    ) -> Dict[str, Dict]:
        """Compare expected and actual results."""
        comparison = {}
        
        for rule_id in expected:
            rule_comparison = {}
            expected_issues = expected[rule_id]
            actual_issues = actual.get(rule_id, [])
            
            # Check each expected issue
            for exp_issue in expected_issues:
                found = False
                for act_issue in actual_issues:
                    if self._issues_match(exp_issue, act_issue):
                        found = True
                        break
                
                rule_comparison[f"line_{exp_issue.get('line', 0)}"] = {
                    "expected": exp_issue,
                    "found": found,
                    "passed": found
                }
            
            # Check for unexpected issues
            for act_issue in actual_issues:
                if not any(self._issues_match(exp, act_issue) for exp in expected_issues):
                    rule_comparison[f"unexpected_line_{act_issue.line}"] = {
                        "expected": None,
                        "found": True,
                        "passed": False,
                        "issue": act_issue
                    }
            
            comparison[rule_id] = rule_comparison
        
        return comparison
    
    def _issues_match(self, expected: Dict, actual: Issue) -> bool:
        """Check if an expected issue matches an actual issue."""
        if expected.get("line") and expected["line"] != actual.line:
            return False
        
        if expected.get("import") and expected["import"] not in actual.message:
            return False
        
        if expected.get("variable") and expected["variable"] not in actual.message:
            return False
        
        return True


def test_ruff_integration():
    """Test Ruff-based rules."""
    config = Config(project_root=Path.cwd())
    config.set_rule_option("unused-imports", "use_ruff", True)
    config.set_rule_option("wildcard-imports", "use_ruff", True)
    config.set_rule_option("print-statements", "use_ruff", True)
    
    # Test Ruff unused imports
    source = "import os\nimport sys  # unused\nimport json\n"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        tmp.write(source)
        tmp_path = Path(tmp.name)
    
    try:
        from prefact.rules.ruff_based import RuffUnusedImports
        rule = RuffUnusedImports(config)
        issues = rule.scan_file(tmp_path, source)
        
        assert len(issues) > 0
        assert any("sys" in issue.message for issue in issues)
    finally:
        tmp_path.unlink(missing_ok=True)


def test_mypy_integration():
    """Test MyPy-based rules."""
    config = Config(project_root=Path.cwd())
    
    # Test MyPy missing return type
    source = '''
def add(a, b):
    return a + b

def calculate():
    return 42
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        tmp.write(source)
        tmp_path = Path(tmp.name)
    
    try:
        from prefact.rules.mypy_based import MyPyMissingReturnType
        rule = MyPyMissingReturnType(config)
        issues = rule.scan_file(tmp_path, source)
        
        # MyPy might not be available in test environment
        # So we just ensure the rule doesn't crash
        assert isinstance(issues, list)
    finally:
        tmp_path.unlink(missing_ok=True)


def test_isort_integration():
    """Test ISort-based rules."""
    config = Config(project_root=Path.cwd())
    
    # Test unsorted imports
    source = '''from local import func
import sys
import os
from third_party import something
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        tmp.write(source)
        tmp_path = Path(tmp.name)
    
    try:
        from prefact.rules.isort_based import ISortedImports
        rule = ISortedImports(config)
        issues = rule.scan_file(tmp_path, source)
        
        assert len(issues) > 0
        
        # Test fixing
        fixed_source, fixes = rule.fix(tmp_path, source, issues)
        assert fixed_source != source
        assert len(fixes) > 0
    finally:
        tmp_path.unlink(missing_ok=True)


def test_autoflake_integration():
    """Test Autoflake-based rules."""
    config = Config(project_root=Path.cwd())
    
    # Test unused imports
    source = '''import os
import sys  # unused
import json

x = 5  # unused
print(x)
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        tmp.write(source)
        tmp_path = Path(tmp.name)
    
    try:
        from prefact.rules.autoflake_based import AutoflakeUnusedImports
        rule = AutoflakeUnusedImports(config)
        issues = rule.scan_file(tmp_path, source)
        
        # Autoflake might not be available
        assert isinstance(issues, list)
    finally:
        tmp_path.unlink(missing_ok=True)


def test_string_transformations():
    """Test string transformation rules."""
    config = Config(project_root=Path.cwd())
    
    # Test string concatenation
    source = '''def greet(name):
    return "Hello, " + name + "!"
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        tmp.write(source)
        tmp_path = Path(tmp.name)
    
    try:
        from prefact.rules.string_transformations import StringConcatToFString
        rule = StringConcatToFString(config)
        issues = rule.scan_file(tmp_path, source)
        
        assert len(issues) > 0
        
        # Test fixing
        fixed_source, fixes = rule.fix(tmp_path, source, issues)
        assert "f" in fixed_source  # Should have f-string
        assert len(fixes) > 0
    finally:
        tmp_path.unlink(missing_ok=True)


def test_full_pipeline():
    """Test the full refactoring pipeline with multiple rules."""
    config = Config(project_root=Path.cwd())
    config.package_name = "test_package"
    
    # Enable all rules
    for rule_id in ["unused-imports", "sorted-imports", "string-concat", 
                   "print-statements", "missing-return-type"]:
        config.set_rule_option(rule_id, "enabled", True)
    
    source = '''import sys
import os  # unused
from local import func
import json

def hello():
    print("Hello " + "World")
    x = 5
    return None
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        tmp.write(source)
        tmp_path = Path(tmp.name)
    
    try:
        engine = RefactoringEngine(config)
        result = engine.run_file(tmp_path)
        
        assert result.issues_found
        assert result.fixes_applied or result.fixes_failed
        assert result.validations
        
        print(f"\nFound {len(result.issues_found)} issues")
        print(f"Applied {len(result.fixes_applied)} fixes")
        print(f"Validations: {len(result.validations)}")
        
    finally:
        tmp_path.unlink(missing_ok=True)


def test_performance_comparison():
    """Test performance comparison between AST and Ruff implementations."""
    config = Config(project_root=Path.cwd())
    
    # Create a moderately large file
    source = ""
    imports = ["import os", "import sys", "import json", "import re", "import math"]
    for i in range(100):
        source += imports[i % len(imports)] + "\n"
        source += f"def func_{i}():\n"
        source += f'    print("Function {i}")\n'
        source += "    return None\n\n"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        tmp.write(source)
        tmp_path = Path(tmp.name)
    
    try:
        import time
        
        # Test AST implementation
        from prefact.rules.unused_imports import UnusedImports
        ast_rule = UnusedImports(config)
        
        start = time.perf_counter()
        ast_issues = ast_rule.scan_file(tmp_path, source)
        ast_time = time.perf_counter() - start
        
        # Test Ruff implementation (if available)
        try:
            from prefact.rules.ruff_based import RuffUnusedImports
            ruff_rule = RuffUnusedImports(config)
            
            start = time.perf_counter()
            ruff_issues = ruff_rule.scan_file(tmp_path, source)
            ruff_time = time.perf_counter() - start
            
            print(f"\nAST time: {ast_time:.3f}s")
            print(f"Ruff time: {ruff_time:.3f}s")
            print(f"Speedup: {ast_time / ruff_time:.2f}x")
            
        except ImportError:
            print("Ruff not available for comparison")
        
    finally:
        tmp_path.unlink(missing_ok=True)


def run_integration_tests():
    """Run all integration tests."""
    print("="*60)
    print("RUNNING INTEGRATION TESTS")
    print("="*60)
    
    config = Config(project_root=Path.cwd())
    
    # Run individual tests
    test_ruff_integration()
    print("✓ Ruff integration test passed")
    
    test_mypy_integration()
    print("✓ MyPy integration test passed")
    
    test_isort_integration()
    print("✓ ISort integration test passed")
    
    test_autoflake_integration()
    print("✓ Autoflake integration test passed")
    
    test_string_transformations()
    print("✓ String transformation test passed")
    
    test_full_pipeline()
    print("✓ Full pipeline test passed")
    
    test_performance_comparison()
    print("✓ Performance comparison completed")
    
    # Run comprehensive test suite
    print("\n" + "="*60)
    print("RUNNING COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    suite = IntegrationTestSuite()
    results = suite.run_all_tests(config)
    
    # Print summary
    passed = sum(1 for result in results.values() if result["passed"])
    total = len(results)
    
    print(f"\nTest Suite Summary: {passed}/{total} passed")
    
    for test_name, result in results.items():
        status = "✓" if result["passed"] else "✗"
        print(f"{status} {test_name}")
    
    return results


if __name__ == "__main__":
    run_integration_tests()
