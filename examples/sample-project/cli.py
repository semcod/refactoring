"""CLI module with print statements and import issues."""

import click
import sys
from ..core import DataProcessor, process_data
from models import User, Post
from utils import format_name, validate_email


@click.command()
@click.option('--name', prompt='Your name', help='Your name')
@click.option('--email', prompt='Your email', help='Your email')
def main(name, email):
    """Main CLI command."""
    print("Starting CLI application")
    
    # Validate email
    if not validate_email(email):
        print("Invalid email provided!")
        sys.exit(1)
    
    # Create user
    user = User(
        id="",
        name=name,
        email=email,
        created_at=datetime.now()
    )
    
    print("Created user: " + user.name)
    
    # Process some data
    processor = DataProcessor()
    processor.add_item(user.name)
    processor.add_item(user.email)
    
    result = process_data("test data")
    print("Processing result: " + str(result))
    
    summary = processor.get_summary()
    print("Summary: " + summary)


@click.group()
def admin():
    """Admin commands."""
    print("Admin mode activated")


@admin.command()
def users():
    """List all users."""
    print("Listing users...")
    # Would normally load from database
    users = [
        User("1", "Alice", "alice@example.com", datetime.now()),
        User("2", "Bob", "bob@example.com", datetime.now()),
    ]
    
    for user in users:
        print("User: " + user.name + " (" + user.email + ")")


if __name__ == '__main__':
    main()
