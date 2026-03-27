# Wildcard Imports Rule Example

This example demonstrates the `wildcard-imports` rule which flags the use of wildcard imports (`from module import *`).

## What it detects

- `from module import *` statements
- Wildcard imports that pollute the namespace
- Non-explicit imports that make code harder to understand

## Why it's flagged

Wildcard imports can:
- Make it unclear where names come from
- Cause name conflicts
- Hide unused imports
- Make refactoring harder

## Example

```python
from typing import *
from utils import *
from .models import *
```

## Running

```bash
prefact scan --path . --config prefact.yaml
```

Note: This rule only flags wildcard imports but doesn't auto-fix them. You should manually replace them with explicit imports.
