"""Central configuration for Zanzibar FIO/Nitrogen/Phosphorus Model.

This module consolidates all constants, file paths, and scenario definitions.
"""

from pathlib import Path
from typing import Dict, Any

# --- File Paths ---
# Root is assumed to be where main.py is, or one level up from app/
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / 'data'
INPUT_DATA_DIR = DATA_DIR / 'input'
OUTPUT_DATA_DIR = DATA_DIR / 'output'
DERIVED_DATA_DIR = DATA_DIR / 'derived'

# Input Files
SANITATION_RAW_PATH = INPUT_DATA_DIR / 'sanitation_type.csv'
PRIVATE_BOREHOLES_PATH = INPUT_DATA_DIR / 'private_boreholes.csv'
GOVERNMENT_BOREHOLES_PATH = INPUT_DATA_DIR / 'government_boreholes.csv'
WARDS_GEOJSON_PATH = INPUT_DATA_DIR / 'wards.geojson'

# Derived/Intermediate Files
SANITATION_STANDARDIZED_PATH = DERIVED_DATA_DIR / 'sanitation_standardized.csv'
PRIVATE_BOREHOLES_ENRICHED_PATH = DERIVED_DATA_DIR / 'private_boreholes_enriched.csv'
GOVERNMENT_BOREHOLES_ENRICHED_PATH = DERIVED_DATA_DIR / 'government_boreholes_enriched.csv'
SPATIAL_ADJ_CACHE_PREFIX = 'spatial_adj_{scenario}_{bh_type}_{radius_m}m.csv'

# Output Files
FIO_LOAD_PATH = OUTPUT_DATA_DIR / 'fio_load_layer1.csv'
FIO_CONCENTRATION_PATH = OUTPUT_DATA_DIR / 'fio_concentration_layer3.csv'
NET_NITROGEN_LOAD_PATH = OUTPUT_DATA_DIR / 'nitrogen_load_layer1.csv'
NET_PHOSPHORUS_LOAD_PATH = OUTPUT_DATA_DIR / 'phosphorus_load_layer1.csv'

# --- Constants ---
EARTH_RADIUS_M = 6371000
# Model Constants
# Calibrated on 2025-11-21 after unit fix and expanded grid search
# CRITICAL: Unit bug fixed in engine.py:234 (was *100, now /10)
# Best params from 42-combo search: decay=0.05, EFIO=1e7
# Note: These are "least bad" fits, not physically validated values
EFIO_DEFAULT = 1.5e7        # CFU/person/day (Calibrated for Q=20k, R=100m)
KS_PER_M_DEFAULT = 0.05     # Decay rate per meter

# Nitrogen Constants
PROTEIN_PER_CAPITA_DEFAULT = 0.060  # kg/person/day (approx 60g)
PROTEIN_TO_NITROGEN_CONVERSION = 0.16  # 16% of protein is nitrogen

# Phosphorus Constants (detergent-based)
PHOSPHORUS_DETERGENT_CONSUMPTION_G_PER_CAPITA = 10.0  # g/person/day
PHOSPHORUS_DETERGENT_PHOSPHORUS_FRACTION = 0.05       # fraction (5% P content)

HOUSEHOLD_POPULATION_DEFAULT = 10

# Containment Efficiencies (1 - leakage)
# 1: Sewer, 2: Pit, 3: Septic, 4: OD
CONTAINMENT_EFFICIENCY_DEFAULT = {
    1: 0.50, # Sewered systems
    2: 0.10, # Basic pit latrines
    3: 0.30, # Septic/improved
    4: 0.00  # Open defecation
}

# Borehole Radii (meters)
RADIUS_BY_TYPE_DEFAULT = {
    'private': 35.0,
    'government': 100.0 # Increased to 100m to capture larger influence zone
}

# Column Mapping for Raw Data
SANITATION_COLUMN_MAPPING = {
    'fid': 'id',
    'Latitude': 'lat',
    'Longitude': 'long',
    'Category': 'toilet_category_id',
    'population': 'household_population'
}

# --- Scenarios ---
SCENARIOS = {
    'crisis_2025_current': {
        'label': 'Current situation (status quo)',
        'description': 'No interventions applied.',
        'pop_factor': 1.0,
    'EFIO_override': EFIO_DEFAULT,
    'ks_per_m': KS_PER_M_DEFAULT,
    'radius_by_type': RADIUS_BY_TYPE_DEFAULT.copy(),
    'flow_multiplier_by_type': {
        'private': 1.0,
        'government': 1.0
    },
    'phosphorus_detergent_consumption_override': PHOSPHORUS_DETERGENT_CONSUMPTION_G_PER_CAPITA,
    'phosphorus_detergent_fraction_override': PHOSPHORUS_DETERGENT_PHOSPHORUS_FRACTION,
    'od_reduction_percent': 0.0,
    'infrastructure_upgrade_percent': 0.0,
    'centralized_treatment_enabled': False,
        'fecal_sludge_treatment_percent': 0.0,
    },
    'crisis_2025_optimistic': {
        'label': 'Optimistic Future',
        'description': '50% reduction in OD, 50% pit upgrade.',
        'pop_factor': 1.0,
    'EFIO_override': EFIO_DEFAULT,
    'ks_per_m': KS_PER_M_DEFAULT,
    'radius_by_type': RADIUS_BY_TYPE_DEFAULT.copy(),
    'flow_multiplier_by_type': {
        'private': 1.0,
        'government': 1.0
    },
    'phosphorus_detergent_consumption_override': PHOSPHORUS_DETERGENT_CONSUMPTION_G_PER_CAPITA,
    'phosphorus_detergent_fraction_override': PHOSPHORUS_DETERGENT_PHOSPHORUS_FRACTION,
    'od_reduction_percent': 50.0,
    'infrastructure_upgrade_percent': 50.0,
    'centralized_treatment_enabled': True,
        'fecal_sludge_treatment_percent': 20.0,
    }
}
