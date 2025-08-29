"""CLI orchestrator for the FIO pathogen model pipeline."""

import pandas as pd
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Union

from . import fio_config as config
from . import fio_core
from . import fio_transport


def setup_logging(level: str = 'INFO') -> None:
    """Configure logging for the FIO model."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def run_scenario(scenario: Union[Dict[str, Any], str] = 'crisis_2025_current') -> None:
    """
    Run the complete FIO pathogen model pipeline for a scenario.
    
    Args:
        scenario: Either scenario name (str) or scenario dict
    """
    # Resolve scenario
    if isinstance(scenario, str):
        if scenario not in config.SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}. Available: {list(config.SCENARIOS.keys())}")
        scenario_dict = config.SCENARIOS[scenario]
        scenario_name = scenario
    else:
        scenario_dict = scenario
        scenario_name = 'custom'
    
    logging.info(f"=== Running FIO Model for scenario: {scenario_name} ===")
    logging.info(f"Scenario parameters: {scenario_dict}")
    
    # Ensure output directory exists
    config.DERIVED_DATA_DIR.mkdir(exist_ok=True)
    
    # === STEP 1: Build/load standardized sanitation table and compute Layer 1 ===
    logging.info("Step 1: Building household sanitation tables and computing Layer 1 loads")
    
    try:
        df_with_loads, pathogen_load_df = fio_core.build_or_load_household_tables(
            config.CONTEXT_DIR, scenario_dict
        )
        logging.info(f"✅ Layer 1 complete: {len(pathogen_load_df)} household records with FIO loads")
    except Exception as e:
        logging.error(f"Failed in Step 1: {e}")
        raise
    
    # === STEP 2: Ensure borehole files with IDs exist ===
    logging.info("Step 2: Loading and standardizing borehole data")
    
    try:
        # Load private boreholes
        if config.PRIVATE_BOREHOLES_PATH.exists():
            private_df = fio_transport.load_boreholes_with_ids(
                str(config.PRIVATE_BOREHOLES_PATH),
                str(config.PRIVATE_BOREHOLES_WITH_ID_PATH), 
                'privbh'
            )
        else:
            logging.warning("Private boreholes file not found - creating empty")
            private_df = pd.DataFrame(columns=['id', 'lat', 'long'])
            private_df.to_csv(config.PRIVATE_BOREHOLES_WITH_ID_PATH, index=False)
        
        # Load government boreholes
        if config.GOVERNMENT_BOREHOLES_PATH.exists():
            government_df = fio_transport.load_boreholes_with_ids(
                str(config.GOVERNMENT_BOREHOLES_PATH),
                str(config.GOVERNMENT_BOREHOLES_WITH_ID_PATH),
                'govbh'
            )
        else:
            logging.warning("Government boreholes file not found - creating empty")
            government_df = pd.DataFrame(columns=['id', 'lat', 'long'])
            government_df.to_csv(config.GOVERNMENT_BOREHOLES_WITH_ID_PATH, index=False)
        
        logging.info(f"✅ Boreholes loaded: {len(private_df)} private, {len(government_df)} government")
    except Exception as e:
        logging.error(f"Failed in Step 2: {e}")
        raise
    
    # === STEP 3: Build link tables and compute Layer 2 ===
    logging.info("Step 3: Computing spatial links and Layer 2 survival")
    
    try:
        ks_per_m = scenario_dict.get('ks_per_m', config.KS_PER_M_DEFAULT)
        radius_by_type = scenario_dict.get('radius_by_type', config.RADIUS_BY_TYPE_DEFAULT)
        
        all_links = []
        
        # Link to private boreholes
        if len(private_df) > 0:
            private_links = fio_transport.link_sources_to_boreholes(
                df_with_loads, private_df, 'private',
                ks_per_m, radius_by_type['private']
            )
            all_links.append(private_links)
        
        # Link to government boreholes  
        if len(government_df) > 0:
            government_links = fio_transport.link_sources_to_boreholes(
                df_with_loads, government_df, 'government',
                ks_per_m, radius_by_type['government']  
            )
            all_links.append(government_links)
        
        # Combine all links
        if all_links:
            combined_links = pd.concat(all_links, ignore_index=True)
        else:
            combined_links = pd.DataFrame(columns=[
                'toilet_id', 'toilet_lat', 'toilet_long', 'borehole_id', 
                'borehole_type', 'distance_m', 'surviving_fio_load'
            ])
        
        # Save combined links
        combined_links.to_csv(config.NET_SURVIVING_PATHOGEN_LOAD_LINKS_PATH, index=False)
        logging.info(f"✅ Layer 2 complete: {len(combined_links)} spatial links created")
        
    except Exception as e:
        logging.error(f"Failed in Step 3: {e}")
        raise
    
    # === STEP 4: Build Q map and compute Layer 3 concentrations ===
    logging.info("Step 4: Computing Layer 3 dilution and concentrations")
    
    try:
        # Build Q maps for both borehole types
        q_maps = []
        
        if len(private_df) > 0:
            private_q = fio_transport.build_borehole_Q_map(
                private_df, 'private', config.Q_DEFAULTS_BY_TYPE
            )
            q_maps.append(private_q)
        
        if len(government_df) > 0:
            government_q = fio_transport.build_borehole_Q_map(
                government_df, 'government', config.Q_DEFAULTS_BY_TYPE
            )
            q_maps.append(government_q)
        
        # Combine Q maps
        if q_maps:
            combined_q = pd.concat(q_maps, ignore_index=True)
        else:
            combined_q = pd.DataFrame(columns=['id', 'borehole_type', 'Q_L_per_day'])
        
        # Compute concentrations
        concentration_links, borehole_concentrations = fio_transport.compute_borehole_concentrations(
            combined_links, combined_q
        )
        
        logging.info(f"✅ Layer 3 complete: {len(borehole_concentrations)} boreholes with concentrations")
        
    except Exception as e:
        logging.error(f"Failed in Step 4: {e}")
        raise
    
    # === SUMMARY REPORTING ===
    logging.info("=== PIPELINE SUMMARY ===")
    
    try:
        # Total surviving load to all boreholes
        if not combined_links.empty:
            total_surviving_load = combined_links['surviving_fio_load'].sum()
            logging.info(f"Total surviving FIO load to all boreholes: {total_surviving_load:.2e} CFU/day")
        
        # Top-5 boreholes by concentration
        if not borehole_concentrations.empty:
            top_5 = borehole_concentrations.nlargest(5, 'concentration_CFU_per_L')
            logging.info("Top 5 boreholes by concentration:")
            for _, row in top_5.iterrows():
                logging.info(f"  {row['borehole_id']} ({row['borehole_type']}): {row['concentration_CFU_per_L']:.2e} CFU/L")
        
        # File outputs summary
        output_files = [
            config.SANITATION_STANDARDIZED_PATH,
            config.NET_PATHOGEN_LOAD_PATH,
            config.PRIVATE_BOREHOLES_WITH_ID_PATH,
            config.GOVERNMENT_BOREHOLES_WITH_ID_PATH,
            config.NET_SURVIVING_PATHOGEN_LOAD_LINKS_PATH,
            config.NET_SURVIVING_PATHOGEN_CONCENTRATION_LINKS_PATH,
            config.FIO_CONCENTRATION_AT_BOREHOLES_PATH
        ]
        
        logging.info("Output files created:")
        for file_path in output_files:
            if file_path.exists():
                size_kb = file_path.stat().st_size / 1024
                logging.info(f"  ✅ {file_path.name} ({size_kb:.1f} KB)")
            else:
                logging.warning(f"  ❌ {file_path.name} (missing)")
        
    except Exception as e:
        logging.warning(f"Error in summary reporting: {e}")
    
    logging.info("=== FIO MODEL PIPELINE COMPLETE ===")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="FIO Pathogen Model Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m BEST-Z.scripts.fio_runner
  python -m BEST-Z.scripts.fio_runner --scenario crisis_2030_no_action
  python -m BEST-Z.scripts.fio_runner --scenario '{"pop_factor": 1.25, "od_reduction_percent": 10}'
  python -m BEST-Z.scripts.fio_runner --log-level DEBUG
        """
    )
    
    parser.add_argument(
        '--scenario', 
        default='crisis_2025_current',
        help='Scenario name or JSON string (default: crisis_2025_current)'
    )
    
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Parse scenario
    scenario = args.scenario
    try:
        # Try to parse as JSON if it looks like a dict
        if scenario.startswith('{') and scenario.endswith('}'):
            scenario = json.loads(scenario)
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON scenario: {e}")
        return 1
    
    # Run pipeline
    try:
        run_scenario(scenario)
        return 0
    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        return 1


if __name__ == '__main__':
    exit(main())