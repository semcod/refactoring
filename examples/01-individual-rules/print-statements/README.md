# Print Statements Rule Example

This example demonstrates the `print-statements` rule which flags print statements in production code.

## What it detects

- `print()` calls in production code
- Debug prints left in the codebase
- Console output that should use logging

## Why flag print statements

- `print()` outputs to stdout which may not be captured in production
- No log levels or filtering
- Can't be easily disabled or redirected
- Mixing with application output

## Better alternatives

```python
import logging

logger = logging.getLogger(__name__)

# Instead of:
print("Debug message")

# Use:
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

## Example

```python
def process_data(data):
    print("Starting processing")  # Flagged
    result = data * 2
    print(f"Result: {result}")    # Flagged
    return result
```

## Running

```bash
prefact scan --path . --config prefact.yaml
```

Note: This rule only flags print statements but doesn't auto-fix them. You should manually replace them with appropriate logging calls.
