"""Configuration and parameters for FIO pathogen model."""

from pathlib import Path

# === CORE PARAMETERS ===

# FIO excretion rate (CFU·person⁻¹·day⁻¹)
EFIO_DEFAULT = 1.28e10  # from notebook

# Household population default (persons/household)
HOUSEHOLD_POPULATION_DEFAULT = 10  # from notebook

# Spatial decay constant (m⁻¹)
KS_PER_M_DEFAULT = 0.001

# === CONTAINMENT EFFICIENCY MAP ===
# Pathogen containment efficiency (η) by toilet category
CONTAINMENT_EFFICIENCY_DEFAULT = {
    1: 0.80,  # High efficiency sanitation
    2: 0.20,  # Basic pit latrines  
    3: 0.90,  # Septic/improved systems
    4: 0.00   # No containment (open defecation)
}

# === BOREHOLE PARAMETERS ===

# Search radii by borehole type (meters)
RADIUS_BY_TYPE_DEFAULT = {
    "private": 30,
    "government": 100
}

# Default Q values when not inferable (L/day)
Q_DEFAULTS_BY_TYPE = {
    "private": 2000.0,
    "government": 20000.0
}

# Flow column preference order for Q inference
FLOW_PREFERENCE_ORDER = [
    # Already in L/day
    'Q_L_per_day',
    'flow_L_per_day',
    # L/s (multiply by 86400)
    'discharge_Lps', 
    'Q_Lps',
    # m³/day (multiply by 1000)
    'yield_m3_per_day',
    'Q_m3_per_day'
]

# === COLUMN MAPPING ===
# Standard column mapping for sanitation data
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
    "Village_Na": "village_name"
}

# === SCENARIO TEMPLATES ===

SCENARIOS = {
    'crisis_2025_current': {
        'pop_factor': 1.0,
        'EFIO_override': None,
        'ks_per_m': KS_PER_M_DEFAULT,
        'radius_by_type': RADIUS_BY_TYPE_DEFAULT.copy(),
        'od_reduction_percent': 0.0,
        'infrastructure_upgrade_percent': 0.0,
        'centralized_treatment_percent': 0.0,
        'fecal_sludge_treatment_percent': 0.0
    },
    'crisis_2030_no_action': {
        'pop_factor': 1.25,  # 25% population growth
        'EFIO_override': None,
        'ks_per_m': KS_PER_M_DEFAULT,
        'radius_by_type': RADIUS_BY_TYPE_DEFAULT.copy(),
        'od_reduction_percent': 0.0,
        'infrastructure_upgrade_percent': 0.0,
        'centralized_treatment_percent': 0.0,
        'fecal_sludge_treatment_percent': 0.0
    },
    'crisis_2050_catastrophic': {
        'pop_factor': 2.48,  # Nearly 2.5x population
        'EFIO_override': None,
        'ks_per_m': KS_PER_M_DEFAULT,
        'radius_by_type': RADIUS_BY_TYPE_DEFAULT.copy(),
        'od_reduction_percent': 0.0,
        'infrastructure_upgrade_percent': 0.0,
        'centralized_treatment_percent': 0.0,
        'fecal_sludge_treatment_percent': 0.0
    },
    'intervention_2030': {
        'pop_factor': 1.25,
        'EFIO_override': None,
        'ks_per_m': KS_PER_M_DEFAULT,
        'radius_by_type': RADIUS_BY_TYPE_DEFAULT.copy(),
        'od_reduction_percent': 50.0,  # 50% OD reduction
        'infrastructure_upgrade_percent': 30.0,  # 30% upgrade to septic
        'centralized_treatment_percent': 20.0,  # Some treatment plants
        'fecal_sludge_treatment_percent': 40.0  # FSM improvements
    }
}

# === PATHS ===
# Base directory paths - handle the BEST-Z/scripts structure
try:
    script_dir = Path(__file__).resolve().parent  # BEST-Z/scripts
    best_z_dir = script_dir.parent  # BEST-Z  
    ROOT_DIR = best_z_dir.parent  # zanzibar-model root
except NameError:
    # Fallback for when __file__ is not available (e.g., exec contexts)
    ROOT_DIR = Path('/home/runner/work/zanzibar-model/zanzibar-model')

CONTEXT_DIR = ROOT_DIR / 'context'
INPUT_DATA_DIR = CONTEXT_DIR / 'input_data'
DERIVED_DATA_DIR = CONTEXT_DIR / 'derived_data'

# Ensure derived data directory exists
DERIVED_DATA_DIR.mkdir(exist_ok=True)

# Input file paths
SANITATION_RAW_PATH = INPUT_DATA_DIR / 'sanitation_type.csv'
PRIVATE_BOREHOLES_PATH = INPUT_DATA_DIR / 'private_boreholes.csv'
GOVERNMENT_BOREHOLES_PATH = INPUT_DATA_DIR / 'government_boreholes.csv'

# Output file paths  
SANITATION_STANDARDIZED_PATH = DERIVED_DATA_DIR / 'sanitation_type_with_population.csv'
NET_PATHOGEN_LOAD_PATH = DERIVED_DATA_DIR / 'net_pathogen_load_from_households.csv'
PRIVATE_BOREHOLES_WITH_ID_PATH = DERIVED_DATA_DIR / 'private_boreholes_with_id.csv'
GOVERNMENT_BOREHOLES_WITH_ID_PATH = DERIVED_DATA_DIR / 'government_boreholes_with_id.csv'
NET_SURVIVING_PATHOGEN_LOAD_LINKS_PATH = DERIVED_DATA_DIR / 'net_surviving_pathogen_load_links.csv'
NET_SURVIVING_PATHOGEN_CONCENTRATION_LINKS_PATH = DERIVED_DATA_DIR / 'net_surviving_pathogen_concentration_links.csv'
FIO_CONCENTRATION_AT_BOREHOLES_PATH = DERIVED_DATA_DIR / 'fio_concentration_at_boreholes.csv'