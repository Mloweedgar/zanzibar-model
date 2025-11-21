"""Main CLI Entry Point for Zanzibar Model."""

import argparse
import sys
from app import engine

def main():
    parser = argparse.ArgumentParser(description="Zanzibar FIO/Nitrogen/Phosphorus Model CLI")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Pipeline Command
    pipe_parser = subparsers.add_parser('pipeline', help='Run the model pipeline')
    pipe_parser.add_argument('--model', choices=['fio', 'nitrogen', 'phosphorus'], required=True, help='Model type to run')
    pipe_parser.add_argument('--scenario', default='crisis_2025_current', help='Scenario name')
    
    # Dashboard Command
    dash_parser = subparsers.add_parser('dashboard', help='Launch the dashboard')
    
    args = parser.parse_args()
    
    if args.command == 'pipeline':
        try:
            engine.run_pipeline(args.model, args.scenario)
            print("Pipeline completed successfully.")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
            
    elif args.command == 'dashboard':
        import os
        print("Launching dashboard...")
        # Force PYTHONPATH to include current directory first to avoid name collisions
        cwd = os.getcwd()
        os.system(f"PYTHONPATH='{cwd}:$PYTHONPATH' streamlit run app/dashboard.py")
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
