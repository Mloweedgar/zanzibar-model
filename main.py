"""Main CLI Entry Point for Zanzibar Model."""

import argparse
import sys
from app import engine, calibrate_runner, config

def main():
    parser = argparse.ArgumentParser(description="Zanzibar FIO/Nitrogen/Phosphorus Model CLI")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Pipeline Command
    pipe_parser = subparsers.add_parser('pipeline', help='Run the model pipeline')
    pipe_parser.add_argument('--model', choices=['fio', 'nitrogen', 'phosphorus'], required=True, help='Model type to run')
    pipe_parser.add_argument('--scenario', default='baseline_2025', help='Scenario name')
    
    # Dashboard Command
    dash_parser = subparsers.add_parser('dashboard', help='Launch the dashboard')

    # Calibration Command
    calib_parser = subparsers.add_parser('calibration', help='Run the calibration suite')
    
    # 4. Compare Subcommand
    parser_compare = subparsers.add_parser('compare', help='Compare scenarios and generate charts')

    args = parser.parse_args()
    
    if args.command == 'pipeline':
        from app.engine import run_pipeline
        # Parse overrides
        overrides = {}
        if args.scenario:
            overrides = config.SCENARIOS.get(args.scenario, {})
            if not overrides:
                logging.warning(f"Scenario '{args.scenario}' not found. Using defaults.")
        
        run_pipeline(args.model, scenario_name=args.scenario, scenario_override=overrides)
            
    elif args.command == 'dashboard':
        # Placeholder for future dashboard
        print("Dashboard feature coming soon.")

    elif args.command == 'calibration':
        from app.calibrate_runner import run_grid_search, print_calibration_report, run_random_forest_cv
        
        # 1. Run Grid Search
        results = run_grid_search()
        best = results.iloc[0]
        
        # 2. Print Scorecard
        print_calibration_report(best)
        
        # 3. Run RF CV (Data-Driven Ceiling)
        print("\nRunning data-driven RF CV (upper bound on trend signal)...")
        from app.calibration_utils import load_government_data
        from app.engine import load_and_standardize_sanitation
        
        toilets = load_and_standardize_sanitation()
        obs = load_government_data()
        cv_results = run_random_forest_cv(toilets, obs)
        
        # Save CV results
        import json
        cv_path = config.OUTPUT_DATA_DIR / "calibration_rf_cv.json"
        with open(cv_path, "w") as f:
            json.dump(cv_results, f, indent=2)
        print(f"RF CV metrics saved to {cv_path}")

    elif args.command == 'compare':
        from app.analysis_runner import run_comparison
        run_comparison()
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
