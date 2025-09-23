## FIO Pathogen Model — Quick Start

### 1) Setup
- Python 3.10+
- Install deps:
```bash
pip install -r requirements.txt
```

### 2) Required inputs
Place the following CSVs in `data/input/`:
- `private_boreholes.csv` (raw private boreholes; used to derive Q and produce the enriched file)
- `government_boreholes.csv` (must include `Q_L_per_day`)
- `sanitation_type.csv` (household sanitation inventory)

### 3) Preprocess boreholes (derive Q_L_per_day)
Derive and save `Q_L_per_day` to enriched files used by the pipeline:
```bash
python main.py derive-private-q
python main.py derive-government-q
```
This writes:
- `data/derived/private_boreholes_enriched.csv`
- `data/derived/government_boreholes_enriched.csv`

Optional (for inspection only):
```bash
python main.py inspect-private-q
```
Writes unique value summaries to `data/output/`.

### 4) Run the pipeline
```bash
python main.py pipeline --scenario crisis_2025_current
```
- `--scenario` accepts either a scenario name defined in `app/fio_config.py` or a JSON string with overrides.

Key outputs (written to `data/output/` unless noted):
- Borehole concentrations: `fio_concentration_at_boreholes.csv`
- Toilet markers (net loads): `dashboard_toilets_markers.csv`
- Toilet heatmap data: `dashboard_toilets_heatmap.csv`
- Link table (loads with distance decay): `net_surviving_pathogen_load_links.csv`
- Enriched private boreholes (preprocess step): `data/derived/private_boreholes_enriched.csv`

### 5) Launch the dashboard
```bash
python main.py dashboard
```
Opens a Streamlit app (defaults to port 8502). Use the sidebar to adjust interventions and rerun.

### Notes
- The pipeline requires:
  - `data/derived/private_boreholes_enriched.csv` (from step 3)
  - `data/derived/government_boreholes_enriched.csv` (from step 3)
- If inputs are missing, the pipeline will fail fast with a clear error message.

### Troubleshooting
- Missing Q for government boreholes: ensure the file has a positive `Q_L_per_day` column.
- No links found: increase linking radius in the dashboard scenario, or verify coordinates.


