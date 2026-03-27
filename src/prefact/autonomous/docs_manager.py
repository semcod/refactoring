"""Documentation management for autonomous prefact."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

from ._base import BaseManager, console, __version__


class DocsManager(BaseManager):
    """Manages documentation files - planfile.yaml and CHANGELOG.md."""
    
    def __init__(self, project_root: Path):
        super().__init__(project_root)
        self.tickets_created: List[Dict[str, Any]] = []
        self.issues_found: List[Dict[str, Any]] = []
    
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
            
            new_content = f"{chr(10).join(lines[:insert_pos])}\n{entry}\n{chr(10).join(lines[insert_pos:])}"
        else:
            new_content = f"# Changelog\n\n{entry}"
        
        self.changelog_path.write_text(new_content)
        console.print(f"📝 Updated CHANGELOG.md with {len(self.tickets_created)} changes")
