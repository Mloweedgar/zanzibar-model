from pathlib import Path

# Constants
P_C = 64  # daily protein consumption per capita (g/day)
PTN = 0.16  # protein to nitrogen conversion factor

# FIO Constants
EFIO = 2e10  # per-capita FIO excretion factor (cfu person⁻¹ day⁻¹)

# Directories
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT_DIR / 'data_raw'
OUTPUT_DIR = ROOT_DIR / 'outputs'

SCENARIOS = {
    'baseline_2022': {
        'pop_factor': 1.0,
        'nre_override': {}
    },
    'improved_removal': {
        'pop_factor': 1.0,
        'nre_override': {'1': 0.80, '2': 0.80, '3': 0.80, '4': 0.80}
    },
    'pop_growth_2030': {
        'pop_factor': 1.2,
        'nre_override': {}
    }
}

# FIO Sanitation Type Mapping (toilet_type_id -> FIO category)
FIO_SANITATION_MAPPING = {
    '1': 'SewerConnection',    # Flush to sewer system
    '2': 'SepticTank',         # Flush to septic tank
    '3': 'SepticTank',         # Flush to covered pit
    '4': 'None',               # Flush to somewhere else (no containment)
    '5': 'PitLatrine',         # VIP latrine
    '6': 'PitLatrine',         # Pit with slab and lid
    '7': 'PitLatrine',         # Pit with slab without lid
    '8': 'PitLatrine',         # Pit with non-washable slab
    '9': 'PitLatrine',         # Pit without slab/open pit
    '10': 'None',              # Bucket
    '11': 'None'               # Open defecation
}

# FIO Removal Efficiencies by sanitation category
FIO_REMOVAL_EFFICIENCY = {
    'None': 0.00,
    'PitLatrine': 0.20,
    'SepticTank': 0.20,
    'SewerConnection': 0.55
}

# FIO Scenarios
FIO_SCENARIOS = {
    'baseline_2022': {
        'pop_factor': 1.0,
        'fio_removal_override': {},
        'od_reduction_percent': 0.0
    },
    'improved_sanitation': {
        'pop_factor': 1.0,
        'fio_removal_override': {'PitLatrine': 0.40, 'SepticTank': 0.40},
        'od_reduction_percent': 0.0
    },
    'reduce_open_defecation_50': {
        'pop_factor': 1.0,
        'fio_removal_override': {},
        'od_reduction_percent': 50.0
    }
}
