from pathlib import Path

# Constants
P_C = 64  # daily protein consumption per capita (g/day)
PTN = 0.16  # protein to nitrogen conversion factor

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
