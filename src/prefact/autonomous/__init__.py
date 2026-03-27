"""Autonomous prefact module for self-configuring and self-testing.

This module provides autonomous functionality for prefact including:
- Automatic prefact.yaml generation
- Example testing and verification
- Planfile.yaml ticket management
- TODO.md and CHANGELOG.md management
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

from ._base import console
from .docs_manager import DocsManager
from .project_scanner import ProjectScanner
from .setup_manager import SetupManager
from .todo_manager import TodoManager


class AutonomousRefact:
    """Autonomous prefact manager."""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        
        # Initialize sub-managers
        self.setup_manager = SetupManager(self.project_root)
        self.scanner = ProjectScanner(self.project_root)
        self.todo_manager = TodoManager(self.project_root)
        self.docs_manager = DocsManager(self.project_root)
        
        # Initialize state for backward compatibility
        self.issues_found: List[Dict[str, Any]] = []
        self.tickets_created: List[Dict[str, Any]] = []
    
    def run_autonomous(self) -> bool:
        """Run autonomous prefact process."""
        from prefact import __version__
        from rich.panel import Panel
        
        console.print(Panel.fit(f" Prefact v {__version__} ", style="bold blue"))
        
        try:
            # Step 1: Initialize if needed
            if not self.setup_manager.refact_config_path.exists():
                console.print("📝 Creating prefact.yaml configuration...")
                self.create_refact_config()
            
            # Step 2: Run examples and verify
            console.print("🧪 Running examples verification...")
            if not self.run_examples():
                console.print("❌ Examples verification failed", style="red")
                return False
            
            # Step 3: Scan project for issues
            console.print("🔍 Scanning project for issues...")
            self.scan_project()
            
            # Step 4: Update planfile.yaml with tickets
            console.print("🎫 Updating planfile.yaml...")
            self.update_planfile()
            
            # Step 5: Manage TODO.md and CHANGELOG.md
            console.print("📋 Managing documentation...")
            self.manage_documentation()
            
            console.print("✅ Autonomous prefact completed successfully!", style="green")
            return True
            
        except Exception as e:
            console.print(f"❌ Error: {e}", style="red")
            return False
    
    def create_refact_config(self) -> None:
        """Create prefact.yaml configuration automatically."""
        self.setup_manager.create_refact_config()
    
    def detect_project_info(self) -> Dict[str, Any]:
        """Detect project characteristics."""
        return self.setup_manager.detect_project_info()
    
    def run_examples(self) -> bool:
        """Run all examples and verify they work."""
        return self.setup_manager.run_examples()
    
    def scan_project(self) -> None:
        """Scan project for issues."""
        raw_issues = self.scanner.scan_project()
        # Group issues for other managers
        self.issues_found = self.scanner.group_issues(raw_issues)
        # Share issues with other managers
        self.todo_manager.issues_found = self.issues_found
        self.docs_manager.issues_found = self.issues_found
    
    def group_issues(self, issues: List[Any]) -> List[Dict[str, Any]]:
        """Group issues by type and location."""
        return self.scanner.group_issues(issues)
    
    def update_planfile(self) -> None:
        """Update planfile.yaml with new tickets."""
        self.docs_manager.update_planfile()
        self.tickets_created = self.docs_manager.tickets_created
    
    def create_default_planfile(self) -> Dict[str, Any]:
        """Create default planfile structure."""
        return self.docs_manager.create_default_planfile()
    
    def create_ticket_from_issue(self, issue_group: Dict[str, Any]) -> Dict[str, Any]:
        """Create a ticket from an issue group."""
        return self.docs_manager.create_ticket_from_issue(issue_group)
    
    def ticket_exists(self, planfile: Dict[str, Any], ticket: Dict[str, Any]) -> bool:
        """Check if ticket already exists in planfile."""
        return self.docs_manager.ticket_exists(planfile, ticket)
    
    def manage_documentation(self) -> None:
        """Manage TODO.md and CHANGELOG.md."""
        # Update TODO.md
        self.update_todo_md()
        
        # Update CHANGELOG.md
        self.update_changelog_md()
    
    def update_todo_md(self) -> None:
        """Update TODO.md with current issues, marking completed tasks."""
        self.todo_manager.update_todo_md()
    
    def execute_todos(self) -> None:
        """Execute all tasks from TODO.md, marking completed ones and removing obsolete ones."""
        self.todo_manager.execute_todos()
    
    def update_changelog_md(self) -> None:
        """Update CHANGELOG.md with recent changes."""
        self.docs_manager.update_changelog_md()
    
    def run_tests(self) -> bool:
        """Run project tests."""
        import subprocess
        import sys
        
        test_dirs = ["tests", "test"]
        
        for test_dir in test_dirs:
            test_path = self.project_root / test_dir
            if test_path.exists():
                console.print(f"🧪 Running tests in {test_dir}...")
                
                try:
                    # Try pytest first
                    result = subprocess.run(
                        ["pytest", str(test_path), "-v"],
                        capture_output=True,
                        text=True,
                        cwd=self.project_root
                    )
                    
                    if result.returncode == 0:
                        console.print("✅ Tests passed", style="green")
                        return True
                    else:
                        console.print(f"⚠️ Tests failed: {result.stderr}", style="yellow")
                
                except FileNotFoundError:
                    # Try unittest
                    try:
                        result = subprocess.run(
                            [sys.executable, "-m", "unittest", "discover", "-s", test_dir, "-v"],
                            capture_output=True,
                            text=True,
                            cwd=self.project_root
                        )
                        
                        if result.returncode == 0:
                            console.print("✅ Tests passed", style="green")
                            return True
                        else:
                            console.print(f"⚠️ Tests failed: {result.stderr}", style="yellow")
                    
                    except Exception as e:
                        console.print(f"⚠️ Could not run tests: {e}", style="yellow")
        
        console.print("ℹ️ No tests found", style="blue")
        return True
