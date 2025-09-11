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
        scenario_name = 'custom'

    logging.info(f"=== Running FIO Model for scenario: {scenario_name} ===")
    logging.info(f"Scenario parameters: {scenario_dict}")

    meta = {'scenario_name': scenario_name, 'parameters': scenario_dict, 'timestamp': datetime.utcnow().isoformat() + 'Z'}
    (config.OUTPUT_DATA_DIR / 'last_scenario.json').write_text(json.dumps(meta, indent=2))

    # Step 1: Layer 1
    df_with_loads, pathogen_load_df = fio_core.build_or_load_household_tables(scenario_dict)

    # Step 2: Boreholes with IDs
    if config.PRIVATE_BOREHOLES_PATH.exists():
        private_df = fio_transport.load_boreholes_with_ids(str(config.PRIVATE_BOREHOLES_PATH), str(config.PRIVATE_BOREHOLES_WITH_ID_PATH), 'privbh')
    else:
        private_df = pd.DataFrame(columns=['id','lat','long'])
        private_df.to_csv(config.PRIVATE_BOREHOLES_WITH_ID_PATH, index=False)

    if config.GOVERNMENT_BOREHOLES_PATH.exists():
        government_df = fio_transport.load_boreholes_with_ids(str(config.GOVERNMENT_BOREHOLES_PATH), str(config.GOVERNMENT_BOREHOLES_WITH_ID_PATH), 'govbh')
    else:
        government_df = pd.DataFrame(columns=['id','lat','long'])
        government_df.to_csv(config.GOVERNMENT_BOREHOLES_WITH_ID_PATH, index=False)

    # Step 3: Layer 2 links
    ks_per_m = scenario_dict.get('ks_per_m', config.KS_PER_M_DEFAULT)
    radius_by_type = scenario_dict.get('radius_by_type', config.RADIUS_BY_TYPE_DEFAULT)
    all_links = []
    batch_size = int(scenario_dict.get('link_batch_size', 1000))
    if len(private_df) > 0:
        all_links.append(fio_transport.link_sources_to_boreholes(df_with_loads, private_df, 'private', ks_per_m, radius_by_type['private'], batch_size))
    if len(government_df) > 0:
        all_links.append(fio_transport.link_sources_to_boreholes(df_with_loads, government_df, 'government', ks_per_m, radius_by_type['government'], batch_size))
    if all_links:
        combined_links = pd.concat(all_links, ignore_index=True)
    else:
        combined_links = pd.DataFrame(columns=['toilet_id','toilet_lat','toilet_long','borehole_id','borehole_type','distance_m','surviving_fio_load'])
    combined_links.to_csv(config.NET_SURVIVING_PATHOGEN_LOAD_LINKS_PATH, index=False)

    # Step 4: Q + Layer 3
    flow_prefs = scenario_dict.get('flow_preference_order', config.FLOW_PREFERENCE_ORDER)
    q_defaults = scenario_dict.get('Q_defaults_by_type', config.Q_DEFAULTS_BY_TYPE)
    q_maps = []
    if len(private_df) > 0:
        q_maps.append(fio_transport.build_borehole_Q_map(private_df, 'private', q_defaults, flow_prefs))
    if len(government_df) > 0:
        q_maps.append(fio_transport.build_borehole_Q_map(government_df, 'government', q_defaults, flow_prefs))
    combined_q = pd.concat(q_maps, ignore_index=True) if q_maps else pd.DataFrame(columns=['id','borehole_type','Q_L_per_day'])

    concentration_links, borehole_concentrations = fio_transport.compute_borehole_concentrations(combined_links, combined_q)

    # Dashboard exports (include coordinates for markers/heatmaps)
    if not borehole_concentrations.empty:
        priv = borehole_concentrations[borehole_concentrations['borehole_type']=='private'].copy()
        gov = borehole_concentrations[borehole_concentrations['borehole_type']=='government'].copy()

        # Join coordinates from borehole source tables
        priv_coords = private_df[['id','lat','long']].rename(columns={'id':'borehole_id'}) if not private_df.empty else pd.DataFrame(columns=['borehole_id','lat','long'])
        gov_coords = government_df[['id','lat','long']].rename(columns={'id':'borehole_id'}) if not government_df.empty else pd.DataFrame(columns=['borehole_id','lat','long'])
        priv = priv.merge(priv_coords, on='borehole_id', how='left')
        gov = gov.merge(gov_coords, on='borehole_id', how='left')

        if len(priv) > 20000:
            priv = priv.nlargest(20000, 'concentration_CFU_per_L')
        if len(gov) > 20000:
            gov = gov.nlargest(20000, 'concentration_CFU_per_L')
        priv.to_csv(config.DASH_PRIVATE_BH_PATH, index=False)
        gov.to_csv(config.DASH_GOVERNMENT_BH_PATH, index=False)
    else:
        pd.DataFrame().to_csv(config.DASH_PRIVATE_BH_PATH, index=False)
        pd.DataFrame().to_csv(config.DASH_GOVERNMENT_BH_PATH, index=False)

    hh = pathogen_load_df[['id','lat','long','fio_load']].dropna(subset=['lat','long']).copy()
    markers = hh.nlargest(min(30000, len(hh)), 'fio_load') if len(hh) > 0 else hh
    heat = hh[['lat','long','fio_load']].copy()
    if len(heat) > 80000:
        heat = heat.nlargest(80000, 'fio_load')
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

