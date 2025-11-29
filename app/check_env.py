#!/usr/bin/env python3
"""Check if environment variables are loaded correctly"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

print("Environment Variables Check:")
print("=" * 40)

# Check required variables
required_vars = ['GEMINI_API_KEY']
optional_vars = ['AIPIPE_API_KEY', 'DEBUG', 'BROWSER_HEADLESS']

for var in required_vars:
    value = os.getenv(var)
    if value and value != "your_actual_gemini_api_key_here":
        print(f"✓ {var}: [SET]")
    else:
        print(f"✗ {var}: [MISSING or DEFAULT]")

for var in optional_vars:
    value = os.getenv(var)
    if value:
        print(f"✓ {var}: {value}")
    else:
        print(f"○ {var}: [NOT SET]")

# Check for problematic variables that should NOT be in .env
problematic_vars = ['email', 'secret']
for var in problematic_vars:
    value = os.getenv(var)
    if value:
        print(f"⚠ {var}: [SHOULD NOT BE IN .env - REMOVE THIS]")

print("=" * 40)
print("Note: email and secret should come from POST request, not .env file")