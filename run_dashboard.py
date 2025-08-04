#!/usr/bin/env python3
"""Launch the BEST-Z Interactive Dashboard."""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Launch Streamlit dashboard."""
    project_root = Path(__file__).parent
    best_z_dir = project_root / "BEST-Z"
    dashboard_path = best_z_dir / "scripts" / "interactive_dashboard.py"
    
    if not dashboard_path.exists():
        print(f"Error: Dashboard file not found at {dashboard_path}")
        sys.exit(1)
    
    print("🌊 Starting BEST-Z Interactive Dashboard...")
    print("The dashboard will open in your web browser automatically.")
    print("Press Ctrl+C to stop the server.")
    
    try:
        # Run using the launcher script that handles imports properly
        launcher_path = best_z_dir / "dashboard_launcher.py"
        
        subprocess.run([
            "python", "-m", "streamlit", "run", str(launcher_path),
            "--server.port", "8501",
            "--server.headless", "false"
        ], cwd=project_root)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped.")
    except FileNotFoundError:
        print("Error: Streamlit not found. Please install it with: pip install streamlit")
        sys.exit(1)

if __name__ == "__main__":
    main()