## Zanzibar Water Quality Model (FIO / Nitrogen / Phosphorus)

### What it does
- Pathogen (FIO) pipeline: sanitation load → distance-decay transport → borehole concentrations.
- Nitrogen and phosphorus pipelines: annual loads per sanitation point (no transport).
- Streamlit dashboard to view pathogen risk, N load, P load, and toilet inventory.

### Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run a pipeline (scenarios in app/config.py)
```bash
python main.py pipeline --model fio --scenario crisis_2025_current
python main.py pipeline --model nitrogen --scenario crisis_2025_current
python main.py pipeline --model phosphorus --scenario crisis_2025_current
```
Outputs go to `data/output/`:
- FIO: `fio_load_layer1.csv`, `fio_concentration_layer3.csv`
- Nitrogen: `nitrogen_load_layer1.csv`
- Phosphorus: `phosphorus_load_layer1.csv`

### Dashboard
Run the FIO pipeline first so the dashboard has data:
```bash
python main.py pipeline --model fio --scenario baseline_2025
```
Then launch Streamlit:
```bash
streamlit run app/dashboard.py
# or: python -m streamlit run app/dashboard.py
```
Open the URL Streamlit prints (default http://localhost:8501). Use the sidebar to switch views (Pathogen Risk, Nitrogen Load, Phosphorus Load, Toilet Inventory) and rerun scenarios.

### Calibration
To run the calibration suite (grid search + random forest cross-validation):
```bash
python main.py calibration
```
This will:
1. Run a grid search over physical parameters (EFIO, decay rate, radius).
2. Save the best parameters to `data/output/calibration_grid_results.csv`.
3. Run a Random Forest cross-validation to estimate the theoretical best performance.


### Inputs
- Derived/bundled inputs already in `data/derived/`: `private_boreholes_enriched.csv`, `government_boreholes_enriched.csv`, `sanitation_standardized.csv`.
- If you swap raw inputs, regenerate these yourself (no derive CLI shipped).

### Tests
```bash
python -m pytest
```
