"""Tool orchestration strategies for composite rules.

This module provides different strategies for orchestrating multiple tools
to provide comprehensive code analysis and fixing.
"""

from __future__ import annotations

import concurrent.futures
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from prefact.models import Fix, Issue
from prefact.rules import BaseRule


class ToolStrategy(ABC):
    """Abstract base class for tool orchestration strategies."""
    
    @abstractmethod
    def scan(self, path: Path, source: str, tools: List[BaseRule]) -> List[Issue]:
        """Scan using multiple tools."""
        pass
    
    @abstractmethod
    def fix(self, path: Path, source: str, issues: List[Issue], tools: List[BaseRule]) -> tuple[str, List[Fix]]:
        """Fix issues using multiple tools."""
        pass


class ParallelScanStrategy(ToolStrategy):
    """Run all tools in parallel and merge results."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
    
    def scan(self, path: Path, source: str, tools: List[BaseRule]) -> List[Issue]:
        """Scan with all tools in parallel."""
        all_issues = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all scan tasks
            future_to_tool = {
                executor.submit(tool.scan_file, path, source): tool
                for tool in tools
            }
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_tool):
                tool = future_to_tool[future]
                try:
                    issues = future.result()
                    all_issues.extend(issues)
                except Exception as e:
                    # Log error but continue with other tools
                    print(f"Error in {tool.rule_id}: {e}")
        
        return all_issues
    
    def fix(self, path: Path, source: str, issues: List[Issue], tools: List[BaseRule]) -> tuple[str, List[Fix]]:
        """Apply fixes sequentially (order matters for fixes)."""
        current_source = source
        all_fixes = []
        
        # Group issues by rule ID
        issues_by_rule = defaultdict(list)
        for issue in issues:
            issues_by_rule[issue.rule_id].append(issue)
        
        # Apply fixes in tool priority order
        for tool in tools:
            rule_issues = issues_by_rule.get(tool.rule_id, [])
            if rule_issues:
                fixed_source, fixes = tool.fix(path, current_source, rule_issues)
                if fixed_source != current_source:
                    current_source = fixed_source
                    all_fixes.extend(fixes)
        
        return current_source, all_fixes


class SequentialScanStrategy(ToolStrategy):
    """Run tools sequentially, passing results between them."""
    
    def scan(self, path: Path, source: str, tools: List[BaseRule]) -> List[Issue]:
        """Scan with tools in sequence."""
        all_issues = []
        current_source = source
        
        for tool in tools:
            issues = tool.scan_file(path, current_source)
            all_issues.extend(issues)
            
            # Optionally apply fixes between scans
            if hasattr(tool, 'auto_fix') and tool.auto_fix:
                current_source, _ = tool.fix(path, current_source, issues)
        
        return all_issues
    
    def fix(self, path: Path, source: str, issues: List[Issue], tools: List[BaseRule]) -> tuple[str, List[Fix]]:
        """Fix using tools in sequence."""
        return ParallelScanStrategy().fix(path, source, issues, tools)


class PriorityBasedStrategy(ToolStrategy):
    """Use tool priority to resolve conflicts."""
    
    def __init__(self, tool_priorities: Dict[str, int]):
        self.tool_priorities = tool_priorities
    
    def scan(self, path: Path, source: str, tools: List[BaseRule]) -> List[Issue]:
        """Scan with all tools and resolve conflicts by priority."""
        all_issues = []
        
        # Group issues by location
        issues_by_location = defaultdict(list)
        
        # Scan with all tools
        for tool in tools:
            issues = tool.scan_file(path, source)
            for issue in issues:
                key = (issue.file, issue.line, issue.rule_id)
                issues_by_location[key].append((issue, tool))
        
        # Resolve conflicts
        for key, issue_list in issues_by_location.items():
            if len(issue_list) == 1:
                all_issues.append(issue_list[0][0])
            else:
                # Choose issue from highest priority tool
                best_issue = max(
                    issue_list,
                    key=lambda x: self.tool_priorities.get(x[1].rule_id, 0)
                )[0]
                all_issues.append(best_issue)
        
        return all_issues
    
    def fix(self, path: Path, source: str, issues: List[Issue], tools: List[BaseRule]) -> tuple[str, List[Fix]]:
        """Fix using tools in priority order."""
        # Sort tools by priority
        sorted_tools = sorted(
            tools,
            key=lambda t: self.tool_priorities.get(t.rule_id, 0),
            reverse=True
        )
        
        return ParallelScanStrategy().fix(path, source, issues, sorted_tools)
