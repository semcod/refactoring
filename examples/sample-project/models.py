"""Models with import issues."""

import uuid
from datetime import datetime
from dataclasses import dataclass
import json


@dataclass
class User:
    """User model."""
    id: str
    name: str
    email: str
    created_at: datetime
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        print("Created user:", self.name)


@dataclass
class Post:
    """Post model."""
    id: str
    title: str
    content: str
    author_id: str
    created_at: datetime
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        print("Created post:", self.title)
    
    def get_summary(self):
        """Get post summary."""
        summary = "Post: " + self.title
        return summary


def create_user(name, email):
    """Create a new user."""
    user = User(
        id="",
        name=name,
        email=email,
        created_at=datetime.now()
    )
    return user


def load_users_from_file(filepath):
    """Load users from JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    users = []
    for item in data:
        user = User(**item)
        users.append(user)
    return users
