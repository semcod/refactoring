"""Example with duplicate imports."""

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
