# Missing Return Type Rule Example

This example demonstrates the `missing-return-type` rule which flags functions without return type annotations.

## What it detects

- Public functions without return type hints
- Methods without return type annotations
- Functions that should have explicit return types

## Why return types matter

- Better IDE support and autocomplete
- Clearer API documentation
- Type checking with mypy/pyright
- Easier refactoring

## Example

**Before:**
```python
def add(a, b):
    """Add two numbers."""
    return a + b

def get_user(user_id):
    """Get user by ID."""
    return {"id": user_id, "name": "Test"}

class Processor:
    def process(self, data):
        """Process data."""
        return data.upper()
```

**Should be:**
```python
def add(a, b) -> int:
    """Add two numbers."""
    return a + b

def get_user(user_id) -> dict:
    """Get user by ID."""
    return {"id": user_id, "name": "Test"}

class Processor:
    def process(self, data) -> str:
        """Process data."""
        return data.upper()
```

## Running

```bash
prefact scan --path . --config prefact.yaml
```

Note: This rule only flags missing return types but doesn't auto-fix them. You should manually add appropriate type annotations.
