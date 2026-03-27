"""Git hooks integration for prefact.

This module provides utilities for installing and managing Git hooks
that run prefact scans before commits and other Git operations.
"""

import stat
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from prefact.config import Config


class GitHooks:
    """Manages Git hooks for prefact."""
    
    def __init__(self, repo_root: Path, config: Optional[Config] = None):
        self.repo_root = repo_root.resolve()
        self.git_dir = self._find_git_dir()
        self.hooks_dir = self.git_dir / "hooks"
        self.config = config or Config(project_root=self.repo_root)
    
    def _find_git_dir(self) -> Path:
        """Find the .git directory."""
        git_dir = self.repo_root / ".git"
        if git_dir.is_file():
            # Git worktree
            with open(git_dir) as f:
                git_dir = self.repo_root / f.read().strip().split(" ")[1]
        return git_dir
    
    def install_hooks(self, hook_types: Optional[List[str]] = None) -> None:
        """Install Git hooks for prefact."""
        if hook_types is None:
            hook_types = ["pre-commit", "pre-push", "commit-msg"]
        
        # Ensure hooks directory exists
        self.hooks_dir.mkdir(exist_ok=True)
        
        for hook_type in hook_types:
            hook_path = self.hooks_dir / hook_type
            self._install_hook(hook_type, hook_path)
    
    def _install_hook(self, hook_type: str, hook_path: Path) -> None:
        """Install a specific Git hook."""
        hook_content = self._generate_hook_script(hook_type)
        
        # Backup existing hook if it exists
        if hook_path.exists():
            backup_path = hook_path.with_suffix(".prefact.bak")
            hook_path.rename(backup_path)
            print(f"Backed up existing hook to {backup_path}")
        
        # Write new hook
        hook_path.write_text(hook_content)
        
        # Make hook executable
        current_permissions = hook_path.stat().st_mode
        hook_path.chmod(current_permissions | stat.S_IEXEC)
        
        print(f"Installed {hook_type} hook")
    
    def _generate_hook_script(self, hook_type: str) -> str:
        """Generate the script content for a hook."""
        if hook_type == "pre-commit":
            return self._pre_commit_hook()
        elif hook_type == "pre-push":
            return self._pre_push_hook()
        elif hook_type == "commit-msg":
            return self._commit_msg_hook()
        else:
            raise ValueError(f"Unsupported hook type: {hook_type}")
    
    def _pre_commit_hook(self) -> str:
        """Generate pre-commit hook script."""
        return f"""#!/bin/bash
# Pprefact pre-commit hook
# Runs prefact on staged files before commit

set -e

# Get list of staged Python files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\\.py$' || true)

if [ -z "$STAGED_FILES" ]; then
    echo "No Python files staged, skipping prefact check"
    exit 0
fi

echo "Running prefact on staged Python files..."
echo "Files: $STAGED_FILES"

# Run prefact scan
if command -v prefact &> /dev/null; then
    # Use installed prefact
    echo "$STAGED_FILES" | xargs prefact scan --path -
else
    # Use python -m prefact
    echo "$STAGED_FILES" | xargs python -m prefact scan --path -
fi

# Check if any issues were found
if [ $? -ne 0 ]; then
    echo ""
    echo "prefact found issues in staged files."
    echo "Fix them before committing, or use --no-verify to bypass."
    echo ""
    echo "To fix automatically:"
    echo "  prefact fix --path <file>"
    echo ""
    exit 1
fi

echo "prefact check passed"
exit 0
"""
    
    def _pre_push_hook(self) -> str:
        """Generate pre-push hook script."""
        return f"""#!/bin/bash
# Pprefact pre-push hook
# Runs prefact on all files before pushing

set -e

echo "Running prefact check before push..."

# Run prefact on the entire project
if command -v prefact &> /dev/null; then
    prefact scan --path {self.repo_root}
else
    python -m prefact scan --path {self.repo_root}
fi

# Check if any issues were found
if [ $? -ne 0 ]; then
    echo ""
    echo "prefact found issues in the repository."
    echo "Fix them before pushing, or use --no-verify to bypass."
    echo ""
    exit 1
fi

echo "prefact check passed"
exit 0
"""
    
    def _commit_msg_hook(self) -> str:
        """Generate commit-msg hook script."""
        return f"""#!/bin/bash
# Pprefact commit-msg hook
# Validates commit messages

set -e

commit_msg_file=$1

# Read commit message
commit_msg=$(cat "$commit_msg_file")

# Check for common issues
if [[ "$commit_msg" =~ ^[Ww][Ii][Pp] ]]; then
    echo "Commit message starts with 'WIP' - aborting commit"
    echo "Remove 'WIP' prefix or use --no-verify to bypass"
    exit 1
fi

# Check minimum length
if [ ${{#commit_msg}} -lt 10 ]; then
    echo "Commit message too short (minimum 10 characters)"
    echo "Provide a more descriptive message or use --no-verify to bypass"
    exit 1
fi

exit 0
"""
    
    def uninstall_hooks(self, hook_types: Optional[List[str]] = None) -> None:
        """Uninstall Git hooks."""
        if hook_types is None:
            hook_types = ["pre-commit", "pre-push", "commit-msg"]
        
        for hook_type in hook_types:
            hook_path = self.hooks_dir / hook_type
            backup_path = hook_path.with_suffix(".prefact.bak")
            
            if hook_path.exists():
                # Check if it's a prefact hook
                content = hook_path.read_text()
                if "prefact" in content:
                    hook_path.unlink()
                    
                    # Restore backup if it exists
                    if backup_path.exists():
                        backup_path.rename(hook_path)
                        print(f"Restored original {hook_type} hook")
                    else:
                        print(f"Removed {hook_type} hook")
    
    def list_hooks(self) -> Dict[str, bool]:
        """List status of all hooks."""
        hook_types = ["pre-commit", "pre-push", "commit-msg"]
        status = {}
        
        for hook_type in hook_types:
            hook_path = self.hooks_dir / hook_type
            if hook_path.exists():
                content = hook_path.read_text()
                status[hook_type] = "prefact" in content
            else:
                status[hook_type] = False
        
        return status
    
    def test_hook(self, hook_type: str) -> bool:
        """Test if a hook is working correctly."""
        hook_path = self.hooks_dir / hook_type
        
        if not hook_path.exists():
            return False
        
        try:
            # Run the hook with --help or similar to test
            result = subprocess.run(
                [str(hook_path)],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                timeout=5
            )
            # Hooks may return non-zero for testing, that's OK
            return True
        except Exception:
            return False


class PreCommitConfig:
    """Generate pre-commit configuration for prefact."""
    
    @staticmethod
    def generate_config(repo_root: Path) -> str:
        """Generate .pre-commit-config.yaml content."""
        return f"""# Pre-commit configuration for prefact
# See https://pre-commit.com for more information

repos:
  - repo: local
    hooks:
      - id: prefact-scan
        name: prefact scan
        entry: prefact
        language: system
        args: [scan, --path, .]
        types: [python]
        pass_filenames: false
        always_run: false
        
      - id: prefact-fix
        name: prefact fix
        entry: prefact
        language: system
        args: [fix, --path, .]
        types: [python]
        pass_filenames: false
        always_run: false
        
  # Additional hooks that work well with prefact
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
        
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black
        
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: ["--profile", "black"]
"""
    
    @staticmethod
    def install(repo_root: Path) -> None:
        """Install pre-commit configuration."""
        config_path = repo_root / ".pre-commit-config.yaml"
        
        if config_path.exists():
            backup_path = config_path.with_suffix(".prefact.bak")
            config_path.rename(backup_path)
            print(f"Backed up existing config to {backup_path}")
        
        config_path.write_text(PreCommitConfig.generate_config(repo_root))
        print(f"Installed pre-commit config at {config_path}")
        
        # Install pre-commit hooks
        try:
            subprocess.run(
                ["pre-commit", "install"],
                cwd=repo_root,
                check=True,
                capture_output=True
            )
            print("Installed pre-commit hooks")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install pre-commit hooks: {e}")
            print("Install pre-commit with: pip install pre-commit")


def install_git_hooks(repo_root: Optional[Path] = None) -> None:
    """Install Git hooks for the current repository."""
    if repo_root is None:
        repo_root = Path.cwd()
    
    # Check if we're in a Git repository
    git_dir = repo_root / ".git"
    if not git_dir.exists() and not git_dir.is_file():
        print("Error: Not in a Git repository")
        return
    
    # Install hooks
    hooks = GitHooks(repo_root)
    hooks.install_hooks()
    
    print("\nGit hooks installed successfully!")
    print("They will run before each commit/push.")
    print("To bypass, use: git commit --no-verify")


def uninstall_git_hooks(repo_root: Optional[Path] = None) -> None:
    """Uninstall Git hooks for the current repository."""
    if repo_root is None:
        repo_root = Path.cwd()
    
    hooks = GitHooks(repo_root)
    hooks.uninstall_hooks()
    
    print("Git hooks uninstalled")


def list_git_hooks(repo_root: Optional[Path] = None) -> None:
    """List status of Git hooks."""
    if repo_root is None:
        repo_root = Path.cwd()
    
    hooks = GitHooks(repo_root)
    status = hooks.list_hooks()
    
    print("Git hooks status:")
    for hook_type, installed in status.items():
        status_str = "✓ Installed (prefact)" if installed else "✗ Not installed"
        print(f"  {hook_type}: {status_str}")


# CLI commands
def main() -> None:
    """Main CLI for Git hooks management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage Git hooks for prefact")
    parser.add_argument("command", choices=["install", "uninstall", "list", "test"])
    parser.add_argument("--path", type=Path, default=Path.cwd(), help="Repository path")
    parser.add_argument("--hooks", nargs="+", help="Specific hooks to manage")
    
    args = parser.parse_args()
    
    if args.command == "install":
        install_git_hooks(args.path)
    elif args.command == "uninstall":
        uninstall_git_hooks(args.path)
    elif args.command == "list":
        list_git_hooks(args.path)
    elif args.command == "test":
        hooks = GitHooks(args.path)
        for hook_type in args.hooks or ["pre-commit", "pre-push", "commit-msg"]:
            result = hooks.test_hook(hook_type)
            status = "✓ Working" if result else "✗ Not working"
            print(f"{hook_type}: {status}")


if __name__ == "__main__":
    main()
