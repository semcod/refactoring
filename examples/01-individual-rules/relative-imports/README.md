# Relative Imports Rule Example

This example demonstrates the `relative-imports` rule which converts relative imports to absolute imports.

## What it detects

- `from ..module import` style imports
- `from .module import` style imports
- Any dotted relative imports

## Why absolute imports are better

- Clearer module origin
- Easier refactoring
- Better IDE support
- Avoids circular import issues
- More reliable in complex projects

## Example

**Before:**
```python
from ..models import User, Post
from .utils import helper_function
from ...config import settings
from ..models import User as UserModel
from .utils import *
from .. import constants
```

**After:**
```python
from mypackage.models import User, Post
from mypackage.utils import helper_function
from mypackage.config import settings
from mypackage.models import User as UserModel
from mypackage.utils import *
from mypackage import constants
```

## Configuration

The rule needs to know the package name to convert relative imports correctly. Set it in `prefact.yaml`:

```yaml
package_name: mypackage
```

## Running

```bash
prefact scan --path . --config prefact.yaml
prefact fix --path . --config prefact.yaml
```

The rule will automatically convert all relative imports to absolute imports based on the package name.
