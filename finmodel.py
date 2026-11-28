#!/usr/bin/env python
"""
finmodel CLI entry point.

Usage:
    finmodel run --input <path_or_folder> [--output <dir>]
    py finmodel.py run --input <path_or_folder> [--output <dir>]
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cli import main

if __name__ == "__main__":
    main()
