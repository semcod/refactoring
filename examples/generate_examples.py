#!/usr/bin/env python3
"""Generate example files for prefact rules."""

import os
from pathlib import Path

# Create directory structure
base = Path(__file__).parent / "01-individual-rules"
rules = [
    "duplicate-imports",
    "wildcard-imports", 
    "sorted-imports",
    "string-concat",
    "print-statements",
    "missing-return-type"
]

for rule in rules:
    rule_dir = base / rule
    rule_dir.mkdir(exist_ok=True)
    
    # Create prefact.yaml
    config = f"""package_name: mypackage

include:
  - "**/*.py"

exclude:
  - "**/__pycache__/**"

rules:
  relative-imports:
    enabled: false
  unused-imports:
    enabled: false
  duplicate-imports:
    enabled: {"true" if rule == "duplicate-imports" else "false"}
  wildcard-imports:
    enabled: {"true" if rule == "wildcard-imports" else "false"}
  sorted-imports:
    enabled: {"true" if rule == "sorted-imports" else "false"}
  string-concat:
    enabled: {"true" if rule == "string-concat" else "false"}
  print-statements:
    enabled: {"true" if rule == "print-statements" else "false"}
  missing-return-type:
    enabled: {"true" if rule == "missing-return-type" else "false"}
"""
    
    (rule_dir / "prefact.yaml").write_text(config)
    
    # Create before.py examples for each rule
    if rule == "duplicate-imports":
        before = '''"""Example with duplicate imports."""

import os
import sys
import os  # Duplicate
from typing import List, Dict
from typing import Any  # Duplicate
import json
from collections import defaultdict
from collections import Counter  # Duplicate

def process_data():
    """Process data."""
    return os.getcwd()
'''
        after = '''"""Example with duplicate imports removed."""

import os
import sys
from typing import List, Dict, Any
import json
from collections import defaultdict, Counter

def process_data():
    """Process data."""
    return os.getcwd()
'''
    
    elif rule == "wildcard-imports":
        before = '''"""Example with wildcard imports."""

from typing import *
from utils import *
from .models import *
import os

def process():
    """Process using wildcard imports."""
    data = defaultdict(list)
    return data
'''
        after = '''"""Example with wildcard imports flagged (not auto-fixed)."""

from typing import *
from utils import *
from .models import *
import os

def process():
    """Process using wildcard imports."""
    data = defaultdict(list)
    return data
'''
    
    elif rule == "sorted-imports":
        before = '''"""Example with unsorted imports."""

from .local_module import local_func
import requests
import os
from typing import List
import sys
from collections import defaultdict
import json

def process():
    """Process with unsorted imports."""
    pass
'''
        after = '''"""Example with unsorted imports (flagged only)."""

from .local_module import local_func
import requests
import os
from typing import List
import sys
from collections import defaultdict
import json

def process():
    """Process with unsorted imports."""
    pass
'''
    
    elif rule == "string-concat":
        before = '''"""Example with string concatenation."""

def greet(name, age):
    """Greet someone."""
    message = "Hello " + name + ", you are " + str(age) + " years old"
    return message

def format_data(data):
    """Format data."""
    result = "Data: " + str(data)
    return result
'''
        after = '''"""Example with string concatenation converted to f-strings."""

def greet(name, age):
    """Greet someone."""
    message = f"Hello {name}, you are {age} years old"
    return message

def format_data(data):
    """Format data."""
    result = f"Data: {data}"
    return result
'''
    
    elif rule == "print-statements":
        before = '''"""Example with print statements."""

def process_data(data):
    """Process data with debug prints."""
    print("Starting processing")
    result = data * 2
    print(f"Result: {result}")
    return result

def calculate(a, b):
    """Calculate with debug output."""
    print(f"Calculating {a} + {b}")
    return a + b
'''
        after = '''"""Example with print statements (flagged only)."""

def process_data(data):
    """Process data with debug prints."""
    print("Starting processing")
    result = data * 2
    print(f"Result: {result}")
    return result

def calculate(a, b):
    """Calculate with debug output."""
    print(f"Calculating {a} + {b}")
    return a + b
'''
    
    elif rule == "missing-return-type":
        before = '''"""Example with missing return type annotations."""

def add(a, b):
    """Add two numbers."""
    return a + b

def get_user(user_id):
    """Get user by ID."""
    return {"id": user_id, "name": "Test"}

class Processor:
    """Processor class."""
    
    def process(self, data):
        """Process data."""
        return data.upper()
'''
        after = '''"""Example with return type annotations (flagged only)."""

def add(a, b):
    """Add two numbers."""
    return a + b

def get_user(user_id):
    """Get user by ID."""
    return {"id": user_id, "name": "Test"}

class Processor:
    """Processor class."""
    
    def process(self, data):
        """Process data."""
        return data.upper()
'''
    
    (rule_dir / "before.py").write_text(before)
    (rule_dir / "after.py").write_text(after)

print("Generated all rule examples!")
