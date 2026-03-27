# String Concatenation Rule Example

This example demonstrates the `string-concat` rule which converts string concatenation to f-strings.

## What it detects

- `"Hello " + name` style concatenation
- `str(value)` conversions in concatenation
- Multiple string parts joined with `+`

## Why f-strings are better

- More readable
- Faster performance
- Automatic type conversion
- Less verbose

## Example

**Before:**
```python
def greet(name, age):
    message = "Hello " + name + ", you are " + str(age) + " years old"
    return message

def format_data(data):
    result = "Data: " + str(data)
    return result
```

**After:**
```python
def greet(name, age):
    message = f"Hello {name}, you are {age} years old"
    return message

def format_data(data):
    result = f"Data: {data}"
    return result
```

## Running

```bash
prefact scan --path . --config prefact.yaml
prefact fix --path . --config prefact.yaml
```

The rule will automatically convert string concatenation to f-strings where possible.
