"""
DEPRECATED: This module is deprecated. Please use src.solid.solid_server instead.
This module now imports and re-exports from the new location for backward compatibility.
"""

import warnings
import sys
import os

# Add proper import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import from the new location
from src.solid.solid_server import (
    SolidServer, 
    SolidPrinciple, 
    CodeAnalysis, 
    SolidError,
    ApiError,
    RateLimitError,
    ValidationError
)

# Display deprecation warning
warnings.warn(
    "The 'solid-server.py' module is deprecated. Please use 'solid_server.py' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export main function
from src.solid.solid_server import main

if __name__ == "__main__":
    main() 