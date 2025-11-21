## Zanzibar Water Quality Model — Quick Start

Supports three sibling pipelines that share the same sanitation inputs and scenario logic:
- **FIO (pathogen)**: load + transport + concentration at boreholes  
- **Nitrogen (N)**: annual load per sanitation point  
- **Phosphorus (P)**: annual load per sanitation point (detergent-based)

### 1) Setup
- Python 3.10+
- (Recommended) create a virtualenv
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### 2) Inputs (bundled in this repo)
- `data/input/sanitation_type.csv`
- `data/derived/private_boreholes_enriched.csv`
- `data/derived/government_boreholes_enriched.csv`
- These derived/enriched files are already included. If you replace the raw inputs, regenerate enriched versions with your own scripts (no CLI command is exposed in `main.py`).

### 3) Run a pipeline
Choose a model and scenario defined in `app/config.py` (`crisis_2025_current`, `crisis_2025_optimistic` by default):
```bash
# Pathogen (FIO)
python main.py pipeline --model fio --scenario crisis_2025_current

# Nitrogen
python main.py pipeline --model nitrogen --scenario crisis_2025_current

# Phosphorus
python main.py pipeline --model phosphorus --scenario crisis_2025_current
```

Key outputs (written to `data/output/`):
- FIO: `fio_load_layer1.csv`, `fio_concentration_layer3.csv`
- Nitrogen: `nitrogen_load_layer1.csv`
- Phosphorus: `phosphorus_load_layer1.csv`

### 4) Launch the dashboard
```bash
python main.py dashboard
```
Use the sidebar to select the view (Pathogen Risk, Nitrogen Load, Phosphorus Load, Toilet Inventory) and rerun scenarios.

### 5) Troubleshooting
- If pipelines fail on missing files, verify the enriched inputs in `data/derived/` exist. They are bundled; replace only if you have updated raw data and your own enrichment step.
- Scenario names must exist in `app/config.py`.
- For testing, install `pytest` via `pip install -r requirements.txt` and run `python -m pytest`.
