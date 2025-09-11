#!/usr/bin/env python3
"""Entrypoint for FIO app: run pipeline or launch dashboard.

Usage:
  python man.py pipeline [--scenario JSON_OR_NAME]
  python man.py dashboard
"""

import sys
import json
import argparse
from pathlib import Path

from app import fio_runner


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)

    p1 = sub.add_parser('pipeline')
    p1.add_argument('--scenario', default='crisis_2025_current')
    p1.add_argument('--log-level', default='INFO', choices=['DEBUG','INFO','WARNING','ERROR'])

    p2 = sub.add_parser('dashboard')

    args = parser.parse_args()

    if args.cmd == 'pipeline':
        fio_runner.setup_logging(args.log_level)
        scenario = args.scenario
        try:
            if isinstance(scenario, str) and scenario.startswith('{') and scenario.endswith('}'):
                scenario = json.loads(scenario)
        except json.JSONDecodeError:
            pass
        fio_runner.run_scenario(scenario)
        return 0
    if args.cmd == 'dashboard':
        # Launch Streamlit by module to ensure package context
        import subprocess
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app/simple_dashboard.py", "--server.port", "8502"], check=False)
        return 0
    return 1


if __name__ == '__main__':
    sys.exit(main())
