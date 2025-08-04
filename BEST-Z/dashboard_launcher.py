#!/usr/bin/env python3
"""Simple launcher for the BEST-Z dashboard that handles module imports properly."""

import sys
from pathlib import Path

# Add the BEST-Z directory to the Python path
best_z_dir = Path(__file__).parent
sys.path.insert(0, str(best_z_dir))

# Now import and run the dashboard
from scripts.interactive_dashboard import main

if __name__ == "__main__":
    main()