"""Example file with unused imports removed."""

import datetime
from typing import List, Dict, Any


def process_data(data: List[str]) -> Dict[str, Any]:
    """Process some data."""
    result = {}
    for item in data:
        key = item.lower()
        value = len(item)
        result[key] = value
    return result


def format_timestamp(ts: datetime.datetime) -> str:
    """Format a timestamp."""
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def read_file(filepath: str) -> str:
    """Read file contents."""
    with open(filepath, 'r') as f:
        return f.read()


class DataProcessor:
    """A class with clean imports."""
    
    def __init__(self):
        self.data = {}
        self.timestamp = datetime.datetime.now()
    
    def add_data(self, key: str, value: Any) -> None:
        """Add data to processor."""
        self.data[key] = value
    
    def get_data(self, key: str) -> Any:
        """Get data from processor."""
        return self.data.get(key)
