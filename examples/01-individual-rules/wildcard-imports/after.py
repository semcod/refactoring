"""Example with wildcard imports flagged (not auto-fixed)."""

from typing import *
from utils import *
from .models import *
import os

def process():
    """Process using wildcard imports."""
    data = defaultdict(list)
    return data
