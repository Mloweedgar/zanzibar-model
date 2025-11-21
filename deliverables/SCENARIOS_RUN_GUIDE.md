# Scenario Run Guide (Current Code)

This guide matches the current CLI (only `pipeline` and `dashboard` commands). Built-in scenarios live in `app/config.py` (`crisis_2025_current`, `crisis_2025_optimistic` by default).

## Prerequisites
- Python 3.10+
- (Recommended) virtualenv:
  - `python -m venv .venv`
  - `source .venv/bin/activate`  *(Windows: `.venv\Scripts\activate`)*
- Install deps: `pip install -r requirements.txt`

## Inputs
- Bundled derived inputs:
  - `data/derived/private_boreholes_enriched.csv`
  - `data/derived/government_boreholes_enriched.csv`
  - `data/derived/sanitation_standardized.csv`
- If you replace the raw inputs, regenerate derived/enriched files with your own scripts (no derive CLI shipped in `main.py`).

## Run pipelines
Pick a scenario from `app/config.py` (examples below use `crisis_2025_current`):
```bash
# FIO pathogen (with transport + concentration)
python main.py pipeline --model fio --scenario crisis_2025_current

# Nitrogen load
python main.py pipeline --model nitrogen --scenario crisis_2025_current

# Phosphorus load (detergent-based)
python main.py pipeline --model phosphorus --scenario crisis_2025_current
```

Outputs (all to `data/output/`):
- FIO: `fio_load_layer1.csv`, `fio_concentration_layer3.csv`
- Nitrogen: `nitrogen_load_layer1.csv`
- Phosphorus: `phosphorus_load_layer1.csv`

## Dashboard
```bash
python main.py dashboard
```
Use the sidebar to pick the view (Pathogen Risk, Nitrogen Load, Phosphorus Load, Toilet Inventory) and rerun scenarios.

## Notes
- Scenario names must match `app/config.py`.
- If you see missing-file errors, confirm the derived inputs exist in `data/derived/` (bundled with the repo).
- Testing: `python -m pytest` (after installing requirements).
