"""Setup management for autonomous prefact - configuration and examples."""

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import yaml
from rich.progress import Progress

from prefact.config_extended import ConfigGenerator

from ._base import BaseManager, console


class SetupManager(BaseManager):
    """Handles project setup - configuration and examples."""
    
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
