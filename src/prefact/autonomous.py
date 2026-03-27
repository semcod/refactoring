"""Autonomous prefact module for self-configuring and self-testing.

This module provides autonomous functionality for prefact including:
- Automatic prefact.yaml generation
- Example testing and verification
- Planfile.yaml ticket management
- TODO.md and CHANGELOG.md management
"""

import hashlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress

from prefact import __version__
from prefact.config_extended import ConfigGenerator, ExtendedConfig
from prefact.engine import RefactoringEngine
from prefact.fixer import Fixer
from prefact.scanner import Scanner

# Constants for code analysis
MIN_CODE_SIZE = 50

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
        console.print(Panel.fit(f" Prefact v {__version__} ", style="bold blue"))
        
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
                    console.print(f"🚀 Using parallel processing with {max_workers} workers")
                    
                    def scan_file(file_path: Path) -> Tuple[Path, List[Any]]:
                        file_issues = []
                        try:
                            # Skip large files (>100KB) for speed
                            if file_path.stat().st_size > 100 * 1024:
                                console.print(f"  ⏭️  Skipping large file: {file_path} ({file_path.stat().st_size // 1024}KB)")
                                return file_path, file_issues
                            
                            source = file_path.read_text(encoding="utf-8")
                            
                            # Skip files with no actual code (mostly comments/strings)
                            if len(source.strip()) < MIN_CODE_SIZE:
                                return file_path, file_issues
                            
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
                            # Skip large files (>100KB) for speed
                            if file_path.stat().st_size > 100 * 1024:
                                console.print(f"  ⏭️  Skipping large file: {file_path} ({file_path.stat().st_size // 1024}KB)")
                                continue
                            
                            source = file_path.read_text(encoding="utf-8")
                            
                            # Skip files with no actual code (mostly comments/strings)
                            if len(source.strip()) < MIN_CODE_SIZE:
                                continue
                            
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
        seen_tickets = set()
        for issue_group in self.issues_found:
            ticket = self.create_ticket_from_issue(issue_group)
            
            # Create unique key for deduplication
            ticket_key = (ticket["rule_id"], tuple(ticket["files"]))
            
            # Check if ticket already exists in planfile or current run
            if ticket_key not in seen_tickets and not self.ticket_exists(planfile, ticket):
                new_tickets.append(ticket)
                seen_tickets.add(ticket_key)
        
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
        # Use relative path for consistent hashing across different environments
        file_path = Path(issue_group['file'])
        if file_path.is_absolute():
            rel_file = str(file_path.relative_to(self.project_root))
        else:
            rel_file = str(file_path)
        
        content_hash = hashlib.md5(
            f"{issue_group['rule_id']}:{rel_file}".encode()
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
            "description": f"Resolve {issue_group['count']} {issue_group['rule_id']} issues in {rel_file}",
            "task_type": "bugfix" if issue_group["severity"] == "error" else "prefactor",
            "priority": priority,
            "estimate": estimate,
            "files": [rel_file],
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
        """Update TODO.md with current issues, marking completed tasks."""
        # Parse existing TODO.md if it exists
        existing_todos = {}
        completed_todos = []
        
        if self.todo_path.exists():
            existing_content = self.todo_path.read_text()
            
            # Parse existing TODO entries
            lines = existing_content.split("\n")
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                if line.startswith("- [ ] ") or line.startswith("- [x] "):
                    # Extract file, line, and message from todo
                    # Format: - [ ] file:line - message
                    content = line[6:]  # Remove "- [ ] " or "- [x] "
                    
                    # Handle multi-line messages
                    while i + 1 < len(lines) and not lines[i + 1].strip().startswith("- [") and lines[i + 1].strip():
                        content += f" {lines[i + 1].strip()}"
                        i += 1
                    
                    if " - " in content:
                        file_line_part = content.split(" - ", 1)[0]
                        message_part = content.split(" - ", 1)[1]
                        
                        # Parse file and line
                        if ":" in file_line_part:
                            file_part = file_line_part.rsplit(":", 1)[0]
                            line_part = file_line_part.rsplit(":", 1)[1]
                            try:
                                line_num = int(line_part)
                                key = (file_part, line_num, message_part)
                                existing_todos[key] = {
                                    'status': 'completed' if line.startswith("- [x] ") else 'pending',
                                    'original_line': line
                                }
                            except ValueError:
                                # Line number is not an integer, treat differently
                                key = (file_part, message_part)
                                existing_todos[key] = {
                                    'status': 'completed' if line.startswith("- [x] ") else 'pending',
                                    'original_line': line
                                }
                i += 1
        
        # Create set of current issues
        current_issues = set()
        new_todos = []
        seen = set()
        
        for issue_group in self.issues_found:
            for example in issue_group["examples"]:
                key = (issue_group['file'], example['line'], example['message'])
                current_issues.add(key)
                
                # Check if this is a new issue or existing one
                if key in existing_todos:
                    # Keep existing status
                    status = existing_todos[key]['status']
                    checkbox = "[x]" if status == 'completed' else "[ ]"
                else:
                    # New issue
                    checkbox = "[ ]"
                
                # Avoid duplicates
                if key not in seen:
                    # Convert to relative path for better portability
                    file_path = Path(issue_group['file'])
                    if file_path.is_absolute():
                        rel_file = str(file_path.relative_to(self.project_root))
                    else:
                        rel_file = str(file_path)
                    new_todos.append(f"- {checkbox} {rel_file}:{example['line']} - {example['message']}")
                    seen.add(key)
        
        # Find completed tasks (exist in TODO.md but not in current issues)
        for key, todo_info in existing_todos.items():
            if key not in current_issues and todo_info['status'] == 'pending':
                # Mark as completed
                completed_todos.append(f"- [x] {todo_info['original_line'][6:]}")
        
        # Build content
        content = f"# TODO\n\n"
        content += f"**Generated by:** prefact v{__version__}\n"
        content += f"**Generated on:** {datetime.now().isoformat()}\n"
        content += f"**Total issues:** {len(new_todos)} active, {len(completed_todos)} completed\n\n"
        content += "---\n\n"
        
        # Add completed tasks first
        if completed_todos:
            content += "## ✅ Completed Tasks\n\n"
            content += "\n".join(completed_todos)
            content += "\n\n"
        
        # Add current tasks
        if new_todos:
            content += "## 📋 Current Issues\n\n"
            content += "\n".join(new_todos)
            content += f"\n\n---\n\n*To execute all tasks, run: `prefact -a --execute-todos`*"
        
        # Write TODO.md
        self.todo_path.write_text(content)
        
        total_items = len(new_todos) + len(completed_todos)
        console.print(f"📝 Updated TODO.md: {len(new_todos)} active, {len(completed_todos)} completed ({total_items} total)")
    
    def execute_todos(self) -> None:
        """Execute all tasks from TODO.md, marking completed ones and removing obsolete ones."""
        if not self.todo_path.exists():
            console.print("❌ TODO.md not found. Run autonomous mode first.")
            return
        
        console.print("🔧 Executing TODO tasks...")
        
        # Read current TODO.md
        content = self.todo_path.read_text()
        lines = content.split("\n")
        
        # Parse tasks
        active_tasks = []
        completed_tasks = []
        in_current_section = False
        
        for line in lines:
            if line.strip() == "## 📋 Current Issues":
                in_current_section = True
                continue
            elif line.strip().startswith("##") and in_current_section:
                in_current_section = False
                continue
            elif in_current_section and line.strip().startswith("- [ ]"):
                # Extract file path and issue
                task_line = line.strip()[6:]  # Remove "- [ ] "
                if " - " in task_line:
                    file_line_part = task_line.split(" - ")[0]
                    message = task_line.split(" - ", 1)[1]
                    
                    if ":" in file_line_part:
                        file_path = file_line_part.rsplit(":", 1)[0]
                        line_num = int(file_line_part.rsplit(":", 1)[1])
                        active_tasks.append({
                            'file': file_path,
                            'line': line_num,
                            'message': message,
                            'original_line': line
                        })
        
        # Execute tasks using the refactoring engine
        # Load config for the refactoring engine
        if self.refact_config_path.exists():
            try:
                config = ExtendedConfig.from_yaml(self.refact_config_path)
            except Exception:
                config = Config.from_yaml(self.refact_config_path)
        else:
            config = Config()
        config.project_root = self.project_root
        
        scanner = Scanner(config)
        fixer = Fixer(config)
        executed_count = 0
        
        # Group tasks by file to avoid scanning the same file multiple times
        tasks_by_file = {}
        for task in active_tasks:
            file_path = self.project_root / task['file']
            if file_path not in tasks_by_file:
                tasks_by_file[file_path] = []
            tasks_by_file[file_path].append(task)
        
        # Process each file
        for file_path, file_tasks in tasks_by_file.items():
            if file_path.exists():
                try:
                    # Scan the file to get current issues
                    issues_map = scanner.scan([file_path])
                    issues = issues_map.get(file_path, [])
                    
                    if issues:
                        # Fix the file with its issues
                        fixed_source, fixes = fixer.fix_file(file_path, issues)
                        if fixes:
                            # Mark all tasks for this file as completed
                            for task in file_tasks:
                                completed_tasks.append(f"- [x] {task['file']}:{task['line']} - {task['message']} ✅")
                                executed_count += 1
                                console.print(f"✅ Fixed: {task['file']}:{task['line']}")
                        else:
                            # Keep as active if not fixed
                            for task in file_tasks:
                                completed_tasks.append(task['original_line'])
                    else:
                        # No issues found, keep as active
                        for task in file_tasks:
                            completed_tasks.append(task['original_line'])
                except Exception as e:
                    console.print(f"❌ Error fixing {file_path}: {str(e)}")
                    for task in file_tasks:
                        completed_tasks.append(task['original_line'])
            else:
                console.print(f"⚠️  File not found: {file_path}")
                for task in file_tasks:
                    completed_tasks.append(task['original_line'])
        
        # Update TODO.md with results
        new_content = f"# TODO\n\n"
        new_content += f"**Generated by:** prefact v{__version__}\n"
        new_content += f"**Generated on:** {datetime.now().isoformat()}\n"
        new_content += f"**Last executed:** {datetime.now().isoformat()}\n"
        new_content += f"**Total issues:** {len(active_tasks)} processed, {executed_count} fixed\n\n"
        new_content += "---\n\n"
        
        if completed_tasks:
            new_content += "## 📋 Task Status\n\n"
            new_content += "\n".join(completed_tasks)
            new_content += "\n\n"
        
        self.todo_path.write_text(new_content)
        console.print(f"🎉 Execution complete: {executed_count}/{len(active_tasks)} tasks processed")
    
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
            
            new_content = f"{'\n'.join(lines[:insert_pos])}\n{entry}\n{'\n'.join(lines[insert_pos:])}"
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
