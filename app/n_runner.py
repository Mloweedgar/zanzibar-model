"""Nitrogen model runner: orchestrates the nitrogen load calculation pipeline."""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Union

from . import n_core
from . import fio_config as config


def setup_logging(level: str = 'INFO') -> None:
    logging.basicConfig(level=getattr(logging, level.upper()), format='%(asctime)s - %(levelname)s - %(message)s')


def run_scenario(scenario: Union[Dict[str, Any], str] = 'crisis_2025_current') -> None:
    if isinstance(scenario, str):
        if scenario not in config.SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}. Available: {list(config.SCENARIOS.keys())}")
        scenario_dict = config.SCENARIOS[scenario]
        scenario_name = scenario
    else:
        scenario_dict = scenario
        # Allow caller to provide a friendly scenario name
        scenario_name = scenario_dict.get('scenario_name', 'custom')

    logging.info(f"=== Running Nitrogen Model for scenario: {scenario_name} ===")
    logging.info(f"Scenario parameters: {scenario_dict}")

    meta = {
        'scenario_name': scenario_name,
        'parameters': scenario_dict,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'model_type': 'nitrogen'
    }
    (config.OUTPUT_DATA_DIR / 'last_nitrogen_scenario.json').write_text(json.dumps(meta, indent=2))

    # Step 1: Layer 1 - Calculate nitrogen loads
    df_with_loads = n_core.build_or_load_household_tables(scenario_dict)
    
    logging.info(f"=== Nitrogen Model Complete ===")
    logging.info(f"Generated net nitrogen load file: {config.NET_NITROGEN_LOAD_PATH}")
    logging.info(f"Total records processed: {len(df_with_loads)}")
    logging.info(f"Total annual nitrogen load: {df_with_loads['nitrogen_load'].sum():.2f} kg N/year")


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', default='crisis_2025_current')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG','INFO','WARNING','ERROR'])
    args = parser.parse_args()
    setup_logging(args.log_level)
    scenario = args.scenario
    try:
        if isinstance(scenario, str) and scenario.startswith('{') and scenario.endswith('}'):
            scenario = json.loads(scenario)
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON scenario: {e}")
        return 1
    try:
        run_scenario(scenario)
        return 0
    except Exception as e:
        logging.error(f"Nitrogen pipeline failed: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
