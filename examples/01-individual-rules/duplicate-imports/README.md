# Duplicate Imports Rule Example

This example demonstrates the `duplicate-imports` rule which detects and removes duplicate imports.

## What it detects

- Same module imported multiple times with different names
- Same import statement repeated
- Imports that can be combined

## Example

**Before:**
```python
import os
import sys
import os  # Duplicate
from typing import List, Dict
from typing import Any  # Duplicate
```

**After:**
```python
import os
import sys
from typing import List, Dict, Any
```

## Running

```bash
prefact scan --path . --config prefact.yaml
prefact fix --path . --config prefact.yaml
```

The rule will automatically combine duplicate imports into a single statement.
