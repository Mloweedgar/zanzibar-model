"""Configuration and parameters for FIO pathogen model (app version)."""

from pathlib import Path
from . import config as appcfg

# === CORE PARAMETERS ===
EFIO_DEFAULT = 8.96e9
HOUSEHOLD_POPULATION_DEFAULT = 10
KS_PER_M_DEFAULT = 0.003

# === NITROGEN PARAMETERS ===
PROTEIN_PER_CAPITA_DEFAULT = 0.08  # kg protein per person per day
PROTEIN_TO_NITROGEN_CONVERSION = 0.16  # kg N per kg protein

# === CONTAINMENT EFFICIENCY MAP ===
CONTAINMENT_EFFICIENCY_DEFAULT = {
    1: 0.50, # Sewered systems (calibrated)
    2: 0.10, # Basic pit latrines (calibrated)
    3: 0.30, # Septic/improved (calibrated)
    4: 0.00  # No containment (open defecation)
}

# === BOREHOLE PARAMETERS ===
RADIUS_BY_TYPE_DEFAULT = {"private": 35, "government": 100}
Q_DEFAULTS_BY_TYPE = {"private": 2000.0, "government": 20000.0}


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
    # Baseline
    'crisis_2025_current': {
        'label': 'Current situation (status quo)',
        'description': 'No interventions applied.',
        'pop_factor': 1.0,
        'EFIO_override': EFIO_DEFAULT,
        'ks_per_m': KS_PER_M_DEFAULT,
        'radius_by_type': RADIUS_BY_TYPE_DEFAULT.copy(),
        'od_reduction_percent': 0.0,
        'infrastructure_upgrade_percent': 0.0,
        'centralized_treatment_enabled': False,
        'fecal_sludge_treatment_percent': 0.0,
    },

    # Interventions reflecting report themes
    'stone_town_wsp_kisakasaka': {
        'label': 'Stone Town WSP (Kisakasaka) – outfall mitigation',
        'description': 'Pilot centralized treatment to reduce sea outfalls.',
        'pop_factor': 1.0,
        'EFIO_override': EFIO_DEFAULT,
        'ks_per_m': KS_PER_M_DEFAULT,
        'radius_by_type': RADIUS_BY_TYPE_DEFAULT.copy(),
        'od_reduction_percent': 10.0,
        'infrastructure_upgrade_percent': 30.0,
        'centralized_treatment_enabled': True,
        'fecal_sludge_treatment_percent': 30.0,
    },
    'fsm_scale_up': {
        'label': 'Faecal Sludge Management (FSM) scale-up',
        'description': 'Increase sludge collection and treatment capacity.',
        'pop_factor': 1.0,
        'EFIO_override': EFIO_DEFAULT,
        'ks_per_m': KS_PER_M_DEFAULT,
        'radius_by_type': RADIUS_BY_TYPE_DEFAULT.copy(),
        'od_reduction_percent': 10.0,
        'infrastructure_upgrade_percent': 20.0,
        'centralized_treatment_enabled': False,
        'fecal_sludge_treatment_percent': 60.0,
    },
    'open_defecation_reduction': {
        'label': 'Open Defecation reduction',
        'description': 'Reduce open defecation through behavior change and basic facility provision.',
        'pop_factor': 1.0,
        'EFIO_override': EFIO_DEFAULT,
        'ks_per_m': KS_PER_M_DEFAULT,
        'radius_by_type': RADIUS_BY_TYPE_DEFAULT.copy(),
        'od_reduction_percent': 30.0,
        'infrastructure_upgrade_percent': 0.0,
        'centralized_treatment_enabled': False,
        'fecal_sludge_treatment_percent': 0.0,
    },
}

# === PATHS ===
INPUT_DATA_DIR = appcfg.INPUT_DIR
OUTPUT_DATA_DIR = appcfg.OUTPUT_DIR
DERIVED_DATA_DIR = appcfg.DERIVED_DIR
TILES_DATA_DIR = appcfg.OUTPUT_DIR / 'tiles'

BOREHOLE_TILES_DIR = TILES_DATA_DIR / 'boreholes'
NITROGEN_TILES_DIR = TILES_DATA_DIR / 'nitrogen'

SANITATION_RAW_PATH = INPUT_DATA_DIR / 'sanitation_type.csv'
PRIVATE_BOREHOLES_PATH = INPUT_DATA_DIR / 'private_boreholes.csv'
GOVERNMENT_BOREHOLES_PATH = INPUT_DATA_DIR / 'government_boreholes.csv'
PRIVATE_BOREHOLES_ENRICHED_PATH = DERIVED_DATA_DIR / 'private_boreholes_enriched.csv'
GOVERNMENT_BOREHOLES_ENRICHED_PATH = DERIVED_DATA_DIR / 'government_boreholes_enriched.csv'

# Default assumptions for enrichment/preprocessing
GOVERNMENT_Q_L_PER_DAY_DEFAULT = 20000.0

SANITATION_STANDARDIZED_PATH = DERIVED_DATA_DIR / 'sanitation_type_with_population.csv'
NET_PATHOGEN_LOAD_PATH = DERIVED_DATA_DIR / 'net_pathogen_load_from_households.csv'
NET_NITROGEN_LOAD_PATH = DERIVED_DATA_DIR / 'net_nitrogen_load_from_households.csv'
PRIVATE_BOREHOLES_WITH_ID_PATH = DERIVED_DATA_DIR / 'private_boreholes_with_id.csv'
GOVERNMENT_BOREHOLES_WITH_ID_PATH = DERIVED_DATA_DIR / 'government_boreholes_with_id.csv'
NET_SURVIVING_PATHOGEN_LOAD_LINKS_PATH = OUTPUT_DATA_DIR / 'net_surviving_pathogen_load_links.csv'
NET_SURVIVING_PATHOGEN_CONCENTRATION_LINKS_PATH = OUTPUT_DATA_DIR / 'net_surviving_pathogen_concentration_links.csv'
FIO_CONCENTRATION_AT_BOREHOLES_PATH = OUTPUT_DATA_DIR / 'fio_concentration_at_boreholes.csv'

# Spatial adjacency cache (toilets→boreholes id pairs within radius)
SPATIAL_ADJ_CACHE_PREFIX = 'adjacency__{scenario}__{bh_type}__r{radius_m}m.csv'

# Dashboard optimized
DASH_PRIVATE_BH_PATH = OUTPUT_DATA_DIR / 'dashboard_private_boreholes.csv'
DASH_GOVERNMENT_BH_PATH = OUTPUT_DATA_DIR / 'dashboard_government_boreholes.csv'
DASH_TOILETS_MARKERS_PATH = OUTPUT_DATA_DIR / 'dashboard_toilets_markers.csv'
DASH_TOILETS_HEATMAP_PATH = OUTPUT_DATA_DIR / 'dashboard_toilets_heatmap.csv'
