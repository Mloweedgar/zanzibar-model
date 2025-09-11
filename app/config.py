from pathlib import Path

# Root
ROOT_DIR = Path(__file__).resolve().parents[1]

# Data dirs
DATA_DIR = ROOT_DIR / 'data'
INPUT_DIR = DATA_DIR / 'input'
OUTPUT_DIR = DATA_DIR / 'output'

# Ensure output dir exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
