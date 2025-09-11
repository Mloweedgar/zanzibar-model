"""Configuration and parameters for FIO pathogen model (app version)."""

from pathlib import Path
from . import config as appcfg

# === CORE PARAMETERS ===
EFIO_DEFAULT = 1.28e10
HOUSEHOLD_POPULATION_DEFAULT = 10
KS_PER_M_DEFAULT = 0.001

# === CONTAINMENT EFFICIENCY MAP ===
CONTAINMENT_EFFICIENCY_DEFAULT = {1: 0.80, 2: 0.20, 3: 0.90, 4: 0.00}

# === BOREHOLE PARAMETERS ===
RADIUS_BY_TYPE_DEFAULT = {"private": 30, "government": 100}
Q_DEFAULTS_BY_TYPE = {"private": 2000.0, "government": 20000.0}

FLOW_PREFERENCE_ORDER = [
    'Q_L_per_day','flow_L_per_day','discharge_Lps','Q_Lps','yield_m3_per_day','Q_m3_per_day'
]

# === COLUMN MAPPING ===
SANITATION_COLUMN_MAPPING = {
    "fid": "id",
    "Latitude": "lat",
    "Longitude": "long",
    "Toilets wi": "toilet_type_name",
    "Type": "toilet_type_id",
    "Descpt": "toilet_category_name",
    "Category": "toilet_category_id",
    "Region_Nam": "region_name",
    "Dist_Nam": "district_name",
    "Ward_Nam": "ward_name",
    "Village_Na": "village_name",
}

# === SCENARIOS ===
SCENARIOS = {
    'crisis_2025_current': {
        'pop_factor': 1.0,
        'EFIO_override': None,
        'ks_per_m': KS_PER_M_DEFAULT,
        'radius_by_type': RADIUS_BY_TYPE_DEFAULT.copy(),
        'od_reduction_percent': 0.0,
        'infrastructure_upgrade_percent': 0.0,
        'centralized_treatment_percent': 0.0,
        'fecal_sludge_treatment_percent': 0.0,
    }
}

# === PATHS ===
INPUT_DATA_DIR = appcfg.INPUT_DIR
OUTPUT_DATA_DIR = appcfg.OUTPUT_DIR

SANITATION_RAW_PATH = INPUT_DATA_DIR / 'sanitation_type.csv'
PRIVATE_BOREHOLES_PATH = INPUT_DATA_DIR / 'private_boreholes.csv'
GOVERNMENT_BOREHOLES_PATH = INPUT_DATA_DIR / 'government_boreholes.csv'

SANITATION_STANDARDIZED_PATH = OUTPUT_DATA_DIR / 'sanitation_type_with_population.csv'
NET_PATHOGEN_LOAD_PATH = OUTPUT_DATA_DIR / 'net_pathogen_load_from_households.csv'
PRIVATE_BOREHOLES_WITH_ID_PATH = OUTPUT_DATA_DIR / 'private_boreholes_with_id.csv'
GOVERNMENT_BOREHOLES_WITH_ID_PATH = OUTPUT_DATA_DIR / 'government_boreholes_with_id.csv'
NET_SURVIVING_PATHOGEN_LOAD_LINKS_PATH = OUTPUT_DATA_DIR / 'net_surviving_pathogen_load_links.csv'
NET_SURVIVING_PATHOGEN_CONCENTRATION_LINKS_PATH = OUTPUT_DATA_DIR / 'net_surviving_pathogen_concentration_links.csv'
FIO_CONCENTRATION_AT_BOREHOLES_PATH = OUTPUT_DATA_DIR / 'fio_concentration_at_boreholes.csv'

# Dashboard optimized
DASH_PRIVATE_BH_PATH = OUTPUT_DATA_DIR / 'dashboard_private_boreholes.csv'
DASH_GOVERNMENT_BH_PATH = OUTPUT_DATA_DIR / 'dashboard_government_boreholes.csv'
DASH_TOILETS_MARKERS_PATH = OUTPUT_DATA_DIR / 'dashboard_toilets_markers.csv'
DASH_TOILETS_HEATMAP_PATH = OUTPUT_DATA_DIR / 'dashboard_toilets_heatmap.csv'
