"""Example with return type annotations (flagged only)."""

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
