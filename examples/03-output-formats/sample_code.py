"""Sample code for demonstrating output formats."""

import os  # Unused import
import sys
from typing import List, Dict
from ..utils import helper_function
from .models import User

def process_data(data):
    """Process some data."""
    result = "Processed: " + str(data)
    print("Debug: processing data")
    return result

def calculate_sum(numbers):
    """Calculate sum of numbers."""
    total = 0
    for num in numbers:
        total += num
    print("Total is: " + str(total))
    return total
