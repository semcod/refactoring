"""Custom rules package for prefact examples."""

# Import custom rules to register them
from .no_todo_rule import NoTodoRule, NoPrintRule

__all__ = ["NoTodoRule", "NoPrintRule"]
