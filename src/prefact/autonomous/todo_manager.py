"""TODO management for autonomous prefact."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from prefact.config_extended import ExtendedConfig
from prefact.fixer import Fixer
from prefact.scanner import Scanner

from ._base import BaseManager, console, __version__


class TodoManager(BaseManager):
    """Manages TODO.md file operations."""
    
    def __init__(self, project_root: Path):
        super().__init__(project_root)
        self.issues_found: List[Dict[str, Any]] = []
    
    def update_todo_md(self) -> None:
        """Update TODO.md with current issues, marking completed tasks."""
        # Parse existing TODO.md if it exists
        existing_todos, completed_todos = self._parse_existing_todos()
        
        # Create set of current issues and generate new todos
        current_issues, new_todos = self._generate_current_todos(existing_todos)
        
        # Find completed tasks (exist in TODO.md but not in current issues)
        completed_tasks = self._find_completed_tasks(existing_todos, current_issues)
        
        # Build and write TODO.md content
        self._write_todo_md(new_todos, completed_tasks)
    
    def _parse_existing_todos(self) -> Tuple[Dict, List]:
        """Parse existing TODO.md entries."""
        existing_todos = {}
        completed_todos = []
        
        if not self.todo_path.exists():
            return existing_todos, completed_todos
        
        existing_content = self.todo_path.read_text()
        lines = existing_content.split("\n")
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith("- [ ] ") or line.startswith("- [x] "):
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
        
        return existing_todos, completed_todos
    
    def _generate_current_todos(self, existing_todos: Dict) -> Tuple[set, List[str]]:
        """Generate todos for current issues."""
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
                    rel_file = self._get_relative_file_path(issue_group['file'])
                    new_todos.append(f"- {checkbox} {rel_file}:{example['line']} - {example['message']}")
                    seen.add(key)
        
        return current_issues, new_todos
    
    def _find_completed_tasks(self, existing_todos: Dict, current_issues: set) -> List[str]:
        """Find tasks that were completed since last run."""
        completed_tasks = []
        
        for key, todo_info in existing_todos.items():
            if key not in current_issues and todo_info['status'] == 'pending':
                # Mark as completed
                completed_tasks.append(f"- [x] {todo_info['original_line'][6:]}")
        
        return completed_tasks
    
    def _write_todo_md(self, new_todos: List[str], completed_tasks: List[str]) -> None:
        """Write the updated TODO.md file."""
        content = f"# TODO\n\n"
        content += f"**Generated by:** prefact v{__version__}\n"
        content += f"**Generated on:** {datetime.now().isoformat()}\n"
        content += f"**Total issues:** {len(new_todos)} active, {len(completed_tasks)} completed\n\n"
        content += "---\n\n"
        
        # Add completed tasks first
        if completed_tasks:
            content += "## ✅ Completed Tasks\n\n"
            content += "\n".join(completed_tasks)
            content += "\n\n"
        
        # Add current tasks
        if new_todos:
            content += "## 📋 Current Issues\n\n"
            content += "\n".join(new_todos)
            content += f"\n\n---\n\n*To execute all tasks, run: `prefact -a --execute-todos`*"
        
        # Write TODO.md
        self.todo_path.write_text(content)
        
        total_items = len(new_todos) + len(completed_tasks)
        console.print(f"📝 Updated TODO.md: {len(new_todos)} active, {len(completed_tasks)} completed ({total_items} total)")
    
    def _get_relative_file_path(self, file_path: str) -> str:
        """Convert file path to relative path for better portability."""
        path = Path(file_path)
        if path.is_absolute():
            return str(path.relative_to(self.project_root))
        return str(file_path)
    
    def execute_todos(self) -> None:
        """Execute all tasks from TODO.md, marking completed ones and removing obsolete ones."""
        if not self.todo_path.exists():
            console.print("❌ TODO.md not found. Run autonomous mode first.")
            return
        
        console.print("🔧 Executing TODO tasks...")
        
        # Parse tasks from TODO.md
        active_tasks = self._parse_todo_tasks()
        
        if not active_tasks:
            console.print("ℹ️ No active tasks found.")
            return
        
        # Execute tasks using the refactoring engine
        executed_count, completed_tasks = self._execute_todo_tasks(active_tasks)
        
        # Update TODO.md with results
        self._update_todo_with_execution_results(completed_tasks, executed_count, len(active_tasks))
    
    def _parse_todo_tasks(self) -> List[Dict[str, Any]]:
        """Parse active tasks from TODO.md."""
        content = self.todo_path.read_text()
        lines = content.split("\n")
        
        active_tasks = []
        in_current_section = False
        
        for line in lines:
            if line.strip() == "## 📋 Current Issues":
                in_current_section = True
                continue
            elif line.strip().startswith("##") and in_current_section:
                in_current_section = False
                continue
            elif in_current_section and line.strip().startswith("- [ ]"):
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
        
        return active_tasks
    
    def _get_refactoring_config(self):
        """Get configuration for the refactoring engine."""
        if self.refact_config_path.exists():
            try:
                config = ExtendedConfig.from_yaml(self.refact_config_path)
            except Exception:
                from prefact.config import Config
                config = Config.from_yaml(self.refact_config_path)
        else:
            from prefact.config import Config
            config = Config()
        config.project_root = self.project_root
        return config
    
    def _execute_todo_tasks(self, active_tasks: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
        """Execute TODO tasks and return count of fixed tasks and completed task lines."""
        config = self._get_refactoring_config()
        scanner = Scanner(config)
        fixer = Fixer(config)
        executed_count = 0
        completed_tasks = []
        
        # Group tasks by file to avoid scanning the same file multiple times
        tasks_by_file = self._group_tasks_by_file(active_tasks)
        
        # Process each file
        for file_path, file_tasks in tasks_by_file.items():
            if file_path.exists():
                try:
                    result = self._process_file_tasks(file_path, file_tasks, scanner, fixer)
                    executed_count += result['fixed_count']
                    completed_tasks.extend(result['completed_tasks'])
                except Exception as e:
                    console.print(f"❌ Error fixing {file_path}: {str(e)}")
                    completed_tasks.extend(task['original_line'] for task in file_tasks)
            else:
                console.print(f"⚠️  File not found: {file_path}")
                completed_tasks.extend(task['original_line'] for task in file_tasks)
        
        return executed_count, completed_tasks
    
    def _group_tasks_by_file(self, active_tasks: List[Dict[str, Any]]) -> Dict[Path, List[Dict[str, Any]]]:
        """Group tasks by file path."""
        tasks_by_file = {}
        for task in active_tasks:
            file_path = self.project_root / task['file']
            if file_path not in tasks_by_file:
                tasks_by_file[file_path] = []
            tasks_by_file[file_path].append(task)
        return tasks_by_file
    
    def _process_file_tasks(self, file_path: Path, file_tasks: List[Dict[str, Any]], 
                           scanner: Scanner, fixer: Fixer) -> Dict[str, Any]:
        """Process tasks for a single file."""
        # Scan the file to get current issues
        issues_map = scanner.scan([file_path])
        issues = issues_map.get(file_path, [])
        
        completed_tasks = []
        fixed_count = 0
        
        if issues:
            # Fix the file with its issues
            fixed_source, fixes = fixer.fix_file(file_path, issues)
            if fixes:
                # Mark all tasks for this file as completed
                for task in file_tasks:
                    completed_tasks.append(f"- [x] {task['file']}:{task['line']} - {task['message']} ✅")
                    fixed_count += 1
                    console.print(f"✅ Fixed: {task['file']}:{task['line']}")
            else:
                # Keep as active if not fixed
                completed_tasks.extend(task['original_line'] for task in file_tasks)
        else:
            # No issues found, keep as active
            completed_tasks.extend(task['original_line'] for task in file_tasks)
        
        return {
            'completed_tasks': completed_tasks,
            'fixed_count': fixed_count
        }
    
    def _update_todo_with_execution_results(self, completed_tasks: List[str], 
                                           executed_count: int, total_tasks: int) -> None:
        """Update TODO.md with execution results."""
        new_content = f"# TODO\n\n"
        new_content += f"**Generated by:** prefact v{__version__}\n"
        new_content += f"**Generated on:** {datetime.now().isoformat()}\n"
        new_content += f"**Last executed:** {datetime.now().isoformat()}\n"
        new_content += f"**Total issues:** {total_tasks} processed, {executed_count} fixed\n\n"
        new_content += "---\n\n"
        
        if completed_tasks:
            new_content += "## 📋 Task Status\n\n"
            new_content += "\n".join(completed_tasks)
            new_content += "\n\n"
        
        self.todo_path.write_text(new_content)
        console.print(f"🎉 Execution complete: {executed_count}/{total_tasks} tasks processed")
