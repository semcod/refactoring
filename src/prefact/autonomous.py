"""Autonomous prefact module for self-configuring and self-testing.

This module provides autonomous functionality for prefact including:
- Automatic prefact.yaml generation
- Example testing and verification
- Planfile.yaml ticket management
- TODO.md and CHANGELOG.md management

DEPRECATED: This module has been split into focused submodules.
Please import from prefact.autonomous instead.
"""

# Import the AutonomousRefact class from the new module structure
from .autonomous import AutonomousRefact  # noqa: F401

# Re-export everything for backward compatibility
__all__ = ['AutonomousRefact']
