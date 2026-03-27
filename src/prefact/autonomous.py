"""Autonomous prefact module for self-configuring and self-testing.

This module provides autonomous functionality for prefact including:
- Automatic prefact.yaml generation
- Example testing and verification
- Planfile.yaml ticket management
- TODO.md and CHANGELOG.md management
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, TaskID

from prefact.config import Config
from prefact.config_extended import ConfigGenerator, ExtendedConfig
from prefact.engine import RefactoringEngine

console = Console()


class AutonomousRefact:
    """Autonomous prefact manager."""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.refact_config_path = self.project_root / "prefact.yaml"
        self.planfile_path = self.project_root / "planfile.yaml"
        self.todo_path = self.project_root / "TODO.md"
        self.changelog_path = self.project_root / "CHANGELOG.md"
        self.examples_dir = self.project_root / "examples"
        
        # Initialize state
        self.issues_found: List[Dict[str, Any]] = []
        self.tickets_created: List[Dict[str, Any]] = []
        
    def run_autonomous(self) -> bool:
        """Run autonomous prefact process."""
        console.print(Panel.fit("🤖 Autonomous Refact Mode", style="bold blue"))
        
        try:
            # Step 1: Initialize if needed
            if not self.refact_config_path.exists():
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
        # Detect project type and characteristics
        project_info = self.detect_project_info()
        
        # Generate configuration
        config_content = ConfigGenerator.generate_extended_config(
            self.project_root,
            tools=["ruff", "mypy", "isort"],
            rules=["unused-imports", "relative-imports", "missing-return-type"]
        )
        
        # Customize based on project
        config = yaml.safe_load(config_content)
        
        # Add project-specific settings
        config["project_root"] = str(self.project_root)
        config["package_name"] = project_info["package_name"]
        
        # Enable LLM rules if AI-generated code detected
        if project_info["has_ai_code"]:
            config["rules"]["llm-hallucinations"] = {"enabled": True}
            config["rules"]["magic-numbers"] = {"enabled": True}
        
        # Write configuration
        with open(self.refact_config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        console.print(f"✅ Created {self.refact_config_path}")
    
    def detect_project_info(self) -> Dict[str, Any]:
        """Detect project characteristics."""
        info = {
            "package_name": self.project_root.name,
            "has_ai_code": False,
            "is_test_project": False,
            "has_tests": False,
            "python_version": "3.8"
        }
        
        # Check for AI indicators
        for py_file in self.project_root.rglob("*.py"):
            try:
                content = py_file.read_text()
                if any(indicator in content for indicator in ["TODO", "placeholder", "AI", "LLM"]):
                    info["has_ai_code"] = True
                    break
            except Exception:
                pass
        
        # Check for tests
        if any(self.project_root.glob("test*")) or any(self.project_root.glob("**/test*")):
            info["has_tests"] = True
        
        # Check if this is a test project
        if "test" in self.project_root.name.lower() or "example" in self.project_root.name.lower():
            info["is_test_project"] = True
        
        return info
    
    def run_examples(self) -> bool:
        """Run all examples and verify they work."""
        if not self.examples_dir.exists():
            console.print("⚠️ No examples directory found", style="yellow")
            return True
        
        # Find all prefact.yaml files in examples
        example_configs = list(self.examples_dir.rglob("prefact.yaml"))
        
        if not example_configs:
            console.print("⚠️ No example configurations found", style="yellow")
            return True
        
        success = True
        
        with Progress() as progress:
            task = progress.add_task("Running examples...", total=len(example_configs))
            
            for config_path in example_configs:
                example_dir = config_path.parent
                
                try:
                    # Run prefact scan
                    result = subprocess.run(
                        [sys.executable, "-m", "prefact.cli", "scan", "--path", str(example_dir), "--config", str(config_path)],
                        capture_output=True,
                        text=True,
                        cwd=self.project_root
                    )
                    
                    if result.returncode != 0:
                        console.print(f"❌ Example {example_dir.name} failed: {result.stderr}", style="red")
                        success = False
                    else:
                        console.print(f"✅ Example {example_dir.name} passed")
                    
                except Exception as e:
                    console.print(f"❌ Error running example {example_dir.name}: {e}", style="red")
                    success = False
                
                progress.advance(task)
        
        return success
    
    def scan_project(self) -> None:
        """Scan project for issues."""
        try:
            # Load configuration
            config = ExtendedConfig.from_yaml(self.refact_config_path)
            engine = RefactoringEngine(config)
            
            # Get list of files to scan
            from prefact.scanner import Scanner
            scanner = Scanner(config)
            files_to_scan = list(scanner.collect_files())
            
            console.print(f"📂 Found {len(files_to_scan)} files to scan")
            
            # Show progress bar
            with Progress() as progress:
                scan_task = progress.add_task(
                    "[cyan]Scanning files...", 
                    total=len(files_to_scan),
                    show_speed=True,
                    show_eta=True,
                    show_remaining=True
                )
                
                start_time = datetime.now()
                issues_found = []
                
                # Use parallel processing if enabled
                if config.tools.get('parallel', False) and len(files_to_scan) > 1:
                    max_workers = min(config.performance.get('max_workers', 4), len(files_to_scan))
                    
                    def scan_file(file_path):
                        file_issues = []
                        try:
                            source = file_path.read_text(encoding="utf-8")
                            for rule in scanner._rules:
                                file_issues.extend(rule.scan_file(file_path, source))
                        except Exception as e:
                            console.print(f"  ⚠️ Error scanning {file_path}: {e}")
                        return file_path, file_issues
                    
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        # Submit all files for scanning
                        future_to_file = {executor.submit(scan_file, fp): fp for fp in files_to_scan}
                        
                        for future in as_completed(future_to_file):
                            file_path, file_issues = future.result()
                            issues_found.extend(file_issues)
                            progress.update(scan_task, advance=1, description=f"[cyan]Scanning {file_path.name}")
                else:
                    # Sequential processing
                    for i, file_path in enumerate(files_to_scan):
                        # Update progress
                        progress.update(scan_task, advance=1, description=f"[cyan]Scanning {file_path.name}")
                        
                        # Show current file every 10 files
                        if i % 10 == 0 or i == len(files_to_scan) - 1:
                            elapsed = (datetime.now() - start_time).total_seconds()
                            if i > 0:
                                avg_time = elapsed / i
                                eta = avg_time * (len(files_to_scan) - i)
                                console.print(f"  📄 [{i+1}/{len(files_to_scan)}] {file_path} (ETA: {eta:.1f}s)")
                        
                        # Scan the file
                        try:
                            source = file_path.read_text(encoding="utf-8")
                            for rule in scanner._rules:
                                file_issues = rule.scan_file(file_path, source)
                                issues_found.extend(file_issues)
                        except Exception as e:
                            console.print(f"  ⚠️ Error scanning {file_path}: {e}")
            
            # Group issues by type
            self.issues_found = self.group_issues(issues_found)
            
            elapsed_time = (datetime.now() - start_time).total_seconds()
            console.print(f"📊 Found {len(issues_found)} issues across {len(self.issues_found)} categories in {elapsed_time:.1f}s")
            
        except Exception as e:
            console.print(f"❌ Error scanning project: {e}", style="red")
            import traceback
            traceback.print_exc()
            self.issues_found = []
    
    def group_issues(self, issues: List[Any]) -> List[Dict[str, Any]]:
        """Group issues by type and location."""
        grouped = {}
        
        for issue in issues:
            # Ensure file is a string
            file_path = str(issue.file) if hasattr(issue, 'file') else str(issue)
            rule_id = getattr(issue, 'rule_id', 'unknown')
            
            key = f"{rule_id}:{file_path}"
            if key not in grouped:
                grouped[key] = {
                    "rule_id": rule_id,
                    "file": file_path,
                    "count": 0,
                    "severity": issue.severity.value if hasattr(issue, 'severity') else "warning",
                    "examples": []
                }
            
            grouped[key]["count"] += 1
            if len(grouped[key]["examples"]) < 3:  # Limit examples
                grouped[key]["examples"].append({
                    "line": getattr(issue, 'line', 0),
                    "message": getattr(issue, 'message', 'No message')
                })
        
        return list(grouped.values())
    
    def update_planfile(self) -> None:
        """Update planfile.yaml with new tickets."""
        # Load existing planfile or create new
        if self.planfile_path.exists():
            with open(self.planfile_path) as f:
                planfile = yaml.safe_load(f)
        else:
            planfile = self.create_default_planfile()
        
        # Add tickets for issues
        new_tickets = []
        for issue_group in self.issues_found:
            ticket = self.create_ticket_from_issue(issue_group)
            
            # Check if ticket already exists
            if not self.ticket_exists(planfile, ticket):
                new_tickets.append(ticket)
        
        # Add tickets to planfile
        if "sprints" not in planfile:
            planfile["sprints"] = []
        
        if not planfile["sprints"]:
            planfile["sprints"].append({
                "id": "sprint-1",
                "name": "Code Quality Improvements",
                "duration": "2 weeks",
                "objectives": ["Fix code quality issues"],
                "task_patterns": []
            })
        
        # Add new tickets to first sprint
        sprint = planfile["sprints"][0]
        if "task_patterns" not in sprint:
            sprint["task_patterns"] = []
        
        sprint["task_patterns"].extend(new_tickets)
        
        # Save planfile
        with open(self.planfile_path, 'w') as f:
            yaml.dump(planfile, f, default_flow_style=False, sort_keys=False)
        
        self.tickets_created = new_tickets
        console.print(f"🎫 Created {len(new_tickets)} tickets in planfile.yaml")
    
    def create_default_planfile(self) -> Dict[str, Any]:
        """Create default planfile structure."""
        return {
            "name": "Code Quality Improvement",
            "project_name": self.project_root.name,
            "project_type": "prefactoring",
            "domain": "dev-tools",
            "goal": "Improve code quality using prefact",
            "goals": [
                "Fix all prefact-detected issues",
                "Improve code maintainability",
                "Ensure consistent code style"
            ],
            "quality_gates": [
                {"metric": "Prefact Issues", "threshold": "0"}
            ],
            "sprints": []
        }
    
    def create_ticket_from_issue(self, issue_group: Dict[str, Any]) -> Dict[str, Any]:
        """Create a ticket from an issue group."""
        # Generate unique ID from issue content
        content_hash = hashlib.md5(
            f"{issue_group['rule_id']}:{issue_group['file']}".encode()
        ).hexdigest()[:8]
        
        # Determine priority based on severity and count
        priority = "medium"
        if issue_group["severity"] == "error":
            priority = "critical"
        elif issue_group["count"] > 5:
            priority = "high"
        
        # Estimate based on count
        estimate = "1d" if issue_group["count"] <= 3 else "2d" if issue_group["count"] <= 10 else "3d"
        
        return {
            "id": f"ticket-{content_hash}",
            "name": f"Fix {issue_group['rule_id']} issues",
            "description": f"Resolve {issue_group['count']} {issue_group['rule_id']} issues in {issue_group['file']}",
            "task_type": "bugfix" if issue_group["severity"] == "error" else "prefactor",
            "priority": priority,
            "estimate": estimate,
            "files": [issue_group["file"]],
            "rule_id": issue_group["rule_id"],
            "count": issue_group["count"],
            "model_hints": {
                "planning": "balanced",
                "implementation": "balanced"
            }
        }
    
    def ticket_exists(self, planfile: Dict[str, Any], ticket: Dict[str, Any]) -> bool:
        """Check if ticket already exists in planfile."""
        for sprint in planfile.get("sprints", []):
            for existing in sprint.get("task_patterns", []):
                if (existing.get("rule_id") == ticket["rule_id"] and 
                    existing.get("files") == ticket["files"]):
                    return True
        return False
    
    def manage_documentation(self) -> None:
        """Manage TODO.md and CHANGELOG.md."""
        # Update TODO.md
        self.update_todo_md()
        
        # Update CHANGELOG.md
        self.update_changelog_md()
    
    def update_todo_md(self) -> None:
        """Update TODO.md with current issues."""
        todos = []
        
        # Add issues as TODOs
        for issue_group in self.issues_found:
            for example in issue_group["examples"]:
                todos.append(f"- [ ] {issue_group['file']}:{example['line']} - {example['message']}")
        
        # Write TODO.md
        if todos:
            content = f"# TODO\n\nGenerated by prefact on {datetime.now().isoformat()}\n\n"
            content += "\n".join(todos)
            
            # Append to existing TODO.md or create new
            if self.todo_path.exists():
                existing = self.todo_path.read_text()
                if "# TODO" in existing:
                    # Update existing
                    lines = existing.split("\n")
                    todo_start = next(i for i, line in enumerate(lines) if line.startswith("# TODO"))
                    new_content = "\n".join(lines[:todo_start]) + "\n" + content
                else:
                    new_content = existing + "\n\n" + content
            else:
                new_content = content
            
            self.todo_path.write_text(new_content)
            console.print(f"📝 Updated TODO.md with {len(todos)} items")
    
    def update_changelog_md(self) -> None:
        """Update CHANGELOG.md with recent changes."""
        if not self.tickets_created:
            return
        
        # Create changelog entry
        version = "0.1.10"  # Could be detected from project
        date = datetime.now().strftime("%Y-%m-%d")
        
        entry = f"## [{version}] - {date}\n\n"
        entry += "### Fixed\n"
        
        for ticket in self.tickets_created:
            entry += f"- {ticket['name']} ({ticket['id']})\n"
        
        # Write CHANGELOG.md
        if self.changelog_path.exists():
            existing = self.changelog_path.read_text()
            # Insert after first header
            lines = existing.split("\n")
            insert_pos = 1
            while insert_pos < len(lines) and not lines[insert_pos].startswith("##"):
                insert_pos += 1
            
            new_content = "\n".join(lines[:insert_pos]) + "\n" + entry + "\n" + "\n".join(lines[insert_pos:])
        else:
            new_content = f"# Changelog\n\n{entry}"
        
        self.changelog_path.write_text(new_content)
        console.print(f"📝 Updated CHANGELOG.md with {len(self.tickets_created)} changes")
    
    def run_tests(self) -> bool:
        """Run project tests."""
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
