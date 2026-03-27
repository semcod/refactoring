# Sorted Imports Rule Example

This example demonstrates the `sorted-imports` rule which flags import blocks that are not properly sorted.

## What it detects

- Imports not in the standard order: stdlib → third-party → local
- Mixed import groups
- Inconsistent import organization

## Standard import order

1. Standard library imports (os, sys, json, etc.)
2. Third-party imports (requests, pandas, etc.)
3. Local imports (from .module, from project.module, etc.)

## Example

**Unsorted:**
```python
from .local_module import local_func
import requests
import os
from typing import List
import sys
from collections import defaultdict
import json
```

**Should be:**
```python
import os
import sys
import json
from collections import defaultdict
import requests
from typing import List
from .local_module import local_func
```

## Running

```bash
prefact scan --path . --config prefact.yaml
```

Note: This rule only flags unsorted imports but doesn't auto-fix them. Use a tool like `isort` to automatically sort imports.
