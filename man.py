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
    p2_enhanced = sub.add_parser('dashboard-enhanced')
    p2_old = sub.add_parser('dashboard-old')
    p3 = sub.add_parser('inspect-private-q')
    p4 = sub.add_parser('derive-private-q')
    p5 = sub.add_parser('derive-government-q')
    p6 = sub.add_parser('calibrate')
    p7 = sub.add_parser('calibrate-eff')
    p8 = sub.add_parser('trend')

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
        # Launch lightweight Streamlit dashboard (optimized for <4GB RAM)
        import subprocess
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app/lightweight_dashboard.py", "--server.port", "8502"], check=False)
        return 0
    if args.cmd == 'dashboard-enhanced':
        # Launch enhanced Streamlit dashboard (requires more memory)
        import subprocess
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app/enhanced_dashboard_full.py", "--server.port", "8504"], check=False)
        return 0
    if args.cmd == 'dashboard-old':
        # Launch original Streamlit dashboard 
        import subprocess
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app/dashboard.py", "--server.port", "8503"], check=False)
        return 0
    if args.cmd == 'inspect-private-q':
        from app.preprocess_boreholes import extract_private_q_uniques
        extract_private_q_uniques()
        print("Saved unique value summaries to data/output/")
        return 0
    if args.cmd == 'derive-private-q':
        from app.preprocess_boreholes import derive_private_Q_L_per_day
        out = derive_private_Q_L_per_day()
        print(f"Saved enriched private boreholes to {out}")
        return 0
    if args.cmd == 'derive-government-q':
        from app.preprocess_boreholes import derive_government_Q_L_per_day
        out = derive_government_Q_L_per_day()
        print(f"Saved enriched government boreholes to {out}")
        return 0
    if args.cmd == 'calibrate':
        from app.calibrate import run_calibration
        rep = run_calibration()
        print("Calibration finished. Best:")
        print(json.dumps(rep.get('best', {}), indent=2))
        return 0
    if args.cmd == 'calibrate-eff':
        from app.calibrate import run_efficiency_calibration
        rep = run_efficiency_calibration()
        print("Efficiency calibration finished. Best:")
        print(json.dumps(rep.get('best', {}), indent=2))
        return 0
    if args.cmd == 'trend':
        from app.calibrate import run_trend_search
        rep = run_trend_search()
        print("Trend search finished. Best by Spearman:")
        print(json.dumps(rep.get('best_by_spearman', {}), indent=2))
        return 0
    return 1


if __name__ == '__main__':
    sys.exit(main())
