"""CLI orchestrator for the FIO pathogen model pipeline (app)."""

import pandas as pd
import json
import logging
import argparse
from typing import Dict, Any, Union
from datetime import datetime

from . import fio_config as config
from . import fio_core
from . import fio_transport


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

    logging.info(f"=== Running FIO Model for scenario: {scenario_name} ===")
    logging.info(f"Scenario parameters: {scenario_dict}")

    meta = {
        'scenario_name': scenario_name,
        'parameters': scenario_dict,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    }
    (config.OUTPUT_DATA_DIR / 'last_scenario.json').write_text(json.dumps(meta, indent=2))

    # Step 1: Layer 1
    df_with_loads = fio_core.build_or_load_household_tables(scenario_dict)

    # Step 2: Boreholes with IDs (required inputs)
    # Require enriched private boreholes to be produced beforehand
    missing_inputs = []
    if not config.PRIVATE_BOREHOLES_ENRICHED_PATH.exists():
        missing_inputs.append(f"private boreholes (enriched): {config.PRIVATE_BOREHOLES_ENRICHED_PATH}")
    if not config.GOVERNMENT_BOREHOLES_ENRICHED_PATH.exists():
        missing_inputs.append(f"government boreholes (enriched): {config.GOVERNMENT_BOREHOLES_ENRICHED_PATH}")
    if missing_inputs:
        raise FileNotFoundError("Missing required input files:\n" + "\n".join(missing_inputs))

    # Load enriched private boreholes
    private_df = fio_transport.load_boreholes_with_ids(
        str(config.PRIVATE_BOREHOLES_ENRICHED_PATH), str(config.PRIVATE_BOREHOLES_WITH_ID_PATH), 'privbh'
    )
    government_df = fio_transport.load_boreholes_with_ids(
        str(config.GOVERNMENT_BOREHOLES_ENRICHED_PATH), str(config.GOVERNMENT_BOREHOLES_WITH_ID_PATH), 'govbh'
    )

    # Step 3: Layer 2 links
    ks_per_m = scenario_dict.get('ks_per_m', config.KS_PER_M_DEFAULT)
    radius_by_type = scenario_dict.get('radius_by_type', config.RADIUS_BY_TYPE_DEFAULT)
    all_links = []
    batch_size = int(scenario_dict.get('link_batch_size', 10000))
    if len(private_df) > 0:
        all_links.append(fio_transport.link_sources_to_boreholes(
            df_with_loads, private_df, 'private', ks_per_m, radius_by_type['private'], batch_size,
            scenario_name=scenario_name, use_cache=True
        ))
    if len(government_df) > 0:
        all_links.append(fio_transport.link_sources_to_boreholes(
            df_with_loads, government_df, 'government', ks_per_m, radius_by_type['government'], batch_size,
            scenario_name=scenario_name, use_cache=True
        ))
    if all_links:
        combined_links = pd.concat(all_links, ignore_index=True)
    else:
        combined_links = pd.DataFrame(columns=['toilet_id','toilet_lat','toilet_long','borehole_id','borehole_type','distance_m','surviving_fio_load'])
    combined_links.to_csv(config.NET_SURVIVING_PATHOGEN_LOAD_LINKS_PATH, index=False)

    # Step 4: Q + Layer 3
    q_maps = []
    if len(private_df) > 0:
        q_maps.append(private_df[['id','Q_L_per_day']].assign(borehole_type='private'))
    if len(government_df) > 0:
        q_maps.append(government_df[['id','Q_L_per_day']].assign(borehole_type='government'))
    combined_q = pd.concat(q_maps, ignore_index=True) if q_maps else pd.DataFrame(columns=['id','borehole_type','Q_L_per_day'])

    borehole_concentrations = fio_transport.compute_borehole_concentrations(combined_links, combined_q)

    # Dashboard exports (include coordinates for markers/heatmaps)
    if not borehole_concentrations.empty:
        priv = borehole_concentrations[borehole_concentrations['borehole_type']=='private'].copy()
        gov = borehole_concentrations[borehole_concentrations['borehole_type']=='government'].copy()

        # Join coordinates (and lab columns where available) from borehole source tables
        priv_coords = private_df[['id','lat','long']].rename(columns={'id':'borehole_id'}) if not private_df.empty else pd.DataFrame(columns=['borehole_id','lat','long'])
        if not government_df.empty:
            gov_cols = ['id','lat','long']
            if 'Total Coli' in government_df.columns:
                gov_cols.append('Total Coli')
            if 'E. coli-CF' in government_df.columns:
                gov_cols.append('E. coli-CF')
            gov_coords = government_df[gov_cols].rename(columns={'id':'borehole_id'})
            # Rename lab columns to explicit per-100mL units
            rename_map = {}
            if 'Total Coli' in gov_coords.columns:
                rename_map['Total Coli'] = 'lab_total_coliform_CFU_per_100mL'
            if 'E. coli-CF' in gov_coords.columns:
                rename_map['E. coli-CF'] = 'lab_e_coli_CFU_per_100mL'
            if rename_map:
                gov_coords = gov_coords.rename(columns=rename_map)
        else:
            gov_coords = pd.DataFrame(columns=['borehole_id','lat','long'])
        priv = priv.merge(priv_coords, on='borehole_id', how='left')
        gov = gov.merge(gov_coords, on='borehole_id', how='left')

        if len(priv) > 20000:
            priv = priv.nlargest(20000, 'concentration_CFU_per_100mL')
        if len(gov) > 20000:
            gov = gov.nlargest(20000, 'concentration_CFU_per_100mL')
        priv.to_csv(config.DASH_PRIVATE_BH_PATH, index=False)
        gov.to_csv(config.DASH_GOVERNMENT_BH_PATH, index=False)
    else:
        pd.DataFrame().to_csv(config.DASH_PRIVATE_BH_PATH, index=False)
        pd.DataFrame().to_csv(config.DASH_GOVERNMENT_BH_PATH, index=False)

    hh = df_with_loads[['id','lat','long','fio_load']].dropna(subset=['lat','long']).copy()
    # Use all data instead of sampling for better analysis
    markers = hh  # Use all household data
    heat = hh[['lat','long','fio_load']].copy()  # Use all data for heatmap too
    markers.to_csv(config.DASH_TOILETS_MARKERS_PATH, index=False)
    heat.to_csv(config.DASH_TOILETS_HEATMAP_PATH, index=False)


def main() -> int:
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
        logging.error(f"Pipeline failed: {e}")
        return 1


if __name__ == '__main__':
    exit(main())

