"""Core module with various code issues."""

from utils import *


def process_data(data):
    """Process some data without return type annotation."""
    result = "Processed: " + str(data)
    print("Debug: processing data", data)
    return result


def calculate_sum(numbers):
    """Calculate sum without type hints."""
    total = 0
    for num in numbers:
        total += num
    print("Total is: " + str(total))
    return total


class DataProcessor:
    """A class that processes data."""
    
    def __init__(self):
        self.items = []
        print("Initializing DataProcessor")
    
    def add_item(self, item):
        """Add an item to the processor."""
        self.items.append(item)
    
    def get_summary(self):
        """Get summary of items."""
        count = len(self.items)
        return "Items: " + str(count)
