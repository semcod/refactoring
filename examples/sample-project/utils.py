"""Utility functions with various issues."""

import re


def format_name(first, last):
    """Format a full name."""
    full = first + " " + last
    print("Formatted name:", full)
    return full


def validate_email(email):
    """Validate email address."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern, email):
        print("Email is valid")
        return True
    print("Email is invalid")
    return False


def helper_function(data):
    """A helper function without type hints."""
    processed = "Helper: " + str(data)
    return processed


class UtilClass:
    """Utility class."""
    
    def __init__(self):
        self.cache = {}
        print("UtilClass initialized")
    
    def get_cached(self, key):
        """Get cached value."""
        if key in self.cache:
            return self.cache[key]
        return None
