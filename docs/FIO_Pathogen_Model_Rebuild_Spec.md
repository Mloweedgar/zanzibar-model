## BEST-Z Pathogen Model (FIO) — Fresh Rebuild from context/, Layered Formulation, Scenario-Ready

### 1) Objective
- Build a fresh, self-contained pathogen model using the layered formulation described in `context/fio_modeling.md` and the concrete pipeline demonstrated in `context/model.ipynb`.
- Implement the full pipeline end-to-end so it runs without errors, writes deterministic outputs, and is ready for scenario simulation.
- Use the existing codebase as a guide for structure and style only; do not depend on legacy raw data or prior outputs.

### 2) Layered Model (authoritative math)
- Layer 1 — Source load: L [CFU/day] = Pop × EFIO × (1 − η)
- Layer 2 — Survival/transport (spatial): L_d = L × e^(−k_s · d)
- Layer 3 — Dilution: C [CFU/L] = L_t / Q

### 3) Deliverables
- New Python modules under `BEST-Z/scripts/`:
  - `fio_config.py`: all defaults, parameter maps, scenario templates.
  - `fio_core.py`: data standardization; interventions; Layer 1 loads.
  - `fio_transport.py`: linking toilets→boreholes; Q inference; Layers 2–3 concentrations.
  - `fio_runner.py`: CLI orchestrator to execute the full pipeline.
- Deterministic CSV outputs written under `context/derived_data/`:
  - `sanitation_type_with_population.csv`
  - `net_pathogen_load_from_households.csv`
  - `private_boreholes_with_id.csv`
  - `government_boreholes_with_id.csv`
  - `net_surviving_pathogen_load_links.csv`
  - `net_surviving_pathogen_concentration_links.csv`
  - `fio_concentration_at_boreholes.csv`

### 4) Data and Schemas (use notebook as canonical reference)
- Inputs (from `context/input_data/`):
  - `sanitation_type.csv`
  - `private_boreholes.csv`
  - `government_boreholes.csv`
- Derived schema for `sanitation_type_with_population.csv` (build from raw):
  - Column mapping:
    - `fid → id`
    - `Latitude → lat`
    - `Longitude → long`
    - `Toilets wi → toilet_type_name`
    - `Type → toilet_type_id`
    - `Descpt → toilet_category_name`
    - `Category → toilet_category_id`
    - `Region_Nam → region_name`
    - `Dist_Nam → district_name`
    - `Ward_Nam → ward_name`
    - `Village_Na → village_name`
  - Add fields:
    - `pathogen_containment_efficiency` (η; mapped by `toilet_category_id`)
    - `household_population` (default constant; configurable)
- Derived schema for `net_pathogen_load_from_households.csv`:
  - `id, lat, long, fio_load` (CFU/day), where `fio_load = household_population × EFIO × (1 − η)`
- Borehole files with IDs:
  - `private_boreholes_with_id.csv`, `government_boreholes_with_id.csv` must contain `id, lat, long` and optionally flow columns for Q inference.

### 5) Parameters and Defaults (override via scenarios when needed)
- EFIO default: 1.28e10 CFU·person⁻¹·day⁻¹ (from notebook). Allow override.
- Household population default: 10 persons/household (from notebook). Allow override.
- Containment efficiency `η` by category (example from notebook step; adapt if provided in data):
  - `{1: 0.80, 2: 0.20, 3: 0.90, 4: 0.00}`
- Spatial decay constant: `KS_PER_M = 0.001` (default). Allow override.
- Borehole search radii: `RADIUS_BY_TYPE = {"private": 30, "government": 100}` meters. Allow override.
- Q inference preference order (use first present; convert units):
  - Already L/day: `Q_L_per_day`, `flow_L_per_day`
  - L/s: `discharge_Lps`, `Q_Lps` → × 86400
  - m³/day: `yield_m3_per_day`, `Q_m3_per_day` → × 1000
- Q defaults when not inferable: `{"private": 2000.0, "government": 20000.0}` L/day.

### 6) Inference and Assumptions Policy
- Column presence: If expected columns are absent but equivalents exist (name variations, cases, spaces), infer using fuzzy-but-safe mapping guided by the notebook examples.
- Types: Coerce numeric fields with `errors='coerce'`; fill NA with safe defaults only where the notebook implies them.
- Units: Detect units by column name, apply conversions as above. When ambiguous, prefer conservative assumptions and log the choice.
- IDs: If `id` is missing in boreholes, create deterministic IDs: `privbh_###` / `govbh_###`.
- Radii and decay: If not provided by scenario, use defaults; ensure links are within the selected radius.

### 7) Module Responsibilities and Function Contracts
- `fio_config.py`
  - Hold constants, defaults, and example `SCENARIOS` dicts.

- `fio_core.py`
  - `standardize_sanitation_table(raw_path: str, out_path: str, category_eff_map: dict, household_population_default: int) -> pd.DataFrame`
    - Apply column mapping; coerce numerics; map `η`; add `household_population`; save `out_path`.
    - Validate presence of `id, lat, long, toilet_type_id` post-mapping.
  - `apply_interventions(df: pd.DataFrame, scenario: dict) -> pd.DataFrame`
    - Implement open-defecation reduction and sanitation upgrades by splitting rows for converted populations and reducing source rows; order: OD reduction → upgrades.
  - `compute_layer1_loads(df: pd.DataFrame, EFIO: float) -> pd.DataFrame`
    - Add `fio_load` and persist `net_pathogen_load_from_households.csv`.
  - `build_or_load_household_tables(context_dir: Path, scenario: dict) -> Tuple[pd.DataFrame, pd.DataFrame]`
    - If `sanitation_type_with_population.csv` absent, build from raw; then apply interventions; compute Layer 1.

- `fio_transport.py`
  - `load_boreholes_with_ids(path_in: str, path_out: str, prefix: str) -> pd.DataFrame`
    - Ensure `id` exists; save `*_with_id.csv` deterministically.
  - `haversine_m(lat1: float, lon1: float, lat2_arr: np.ndarray, lon2_arr: np.ndarray) -> np.ndarray`
    - Vectorized great-circle distance (meters).
  - `link_sources_to_boreholes(toilets_df: pd.DataFrame, bores_df: pd.DataFrame, borehole_type: str, ks_per_m: float, radius_m: float) -> pd.DataFrame`
    - For each toilet record, compute distances to boreholes, filter by radius, compute `surviving_fio_load = fio_load × exp(−ks_per_m × distance_m)`.
    - Output cols: `toilet_id, toilet_lat, toilet_long, borehole_id, borehole_type, distance_m, surviving_fio_load`.
  - `pick_Q_L_per_day(df: pd.DataFrame, flow_prefs: list) -> pd.Series`
    - Implement unit preference and conversions; return Series aligned to df.
  - `build_borehole_Q_map(df: pd.DataFrame, borehole_type: str, defaults_by_type: dict) -> pd.DataFrame`
    - Output: `id, borehole_type, Q_L_per_day` (coerced numerics, defaults filled).
  - `compute_borehole_concentrations(links_df: pd.DataFrame, bh_q_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]`
    - Join Q; compute `concentration_CFU_per_L = surviving_fio_load / Q_L_per_day` per link; aggregate per borehole with sum of `surviving_fio_load` and first Q.
    - Persist `net_surviving_pathogen_concentration_links.csv` and `fio_concentration_at_boreholes.csv`.

- `fio_runner.py`
  - `run_scenario(scenario: dict | str = 'crisis_2025_current') -> None`
    - Paths:
      - Inputs: `context/input_data/` (raw)
      - Derived: `context/derived_data/` (create if missing)
    - Steps:
      1) Build/load standardized sanitation table → apply interventions → compute Layer 1 loads.
      2) Ensure borehole `_with_id.csv` files exist for private and government inputs.
      3) Build link tables for private and government; concat and save `net_surviving_pathogen_load_links.csv`.
      4) Build Q map from borehole files; compute link-level concentrations and borehole aggregates; write both outputs.
    - Log rows read/written; print a brief summary of top-5 boreholes by concentration.

### 8) Scenario Structure (flexible, minimal)
```python
scenario_example = {
  "pop_factor": 1.0,                       # scales household_population
  "EFIO_override": None,                   # use default if None
  "ks_per_m": 0.001,                       # spatial decay
  "radius_by_type": {"private": 30, "government": 100},
  # Interventions (applied before Layer 1 calculation)
  "od_reduction_percent": 0.0,             # % of OD converted to pit latrine
  "infrastructure_upgrade_percent": 0.0,   # % of pit latrine upgraded to septic
  "centralized_treatment_percent": 0.0,    # optional: boosts sewer efficiency if applicable
  "fecal_sludge_treatment_percent": 0.0    # optional: boosts septic efficiency if applicable
}
```

### 9) Validation and Error Handling
- Validate required columns at each stage; if missing, raise a clear error naming the file and columns.
- Be robust to column variants (cases/underscores/spaces) by normalizing names when possible; log the mapping used.
- Coerce numerics with `pd.to_numeric(..., errors='coerce')`; fill with defaults only where specified.
- If no boreholes fall within the radius, still produce valid empty link CSVs; do not crash.
- If Q cannot be inferred from any column, fill with type default and log the fallback.

### 10) Acceptance Tests (must pass with `context/` data)
- Running the CLI with the default scenario produces all seven CSV outputs listed in Deliverables, without exceptions.
- `net_pathogen_load_from_households.csv`: `fio_load` > 0 where `household_population > 0` and `η < 1`.
- `net_surviving_pathogen_load_links.csv`: distances ≤ configured radius; `surviving_fio_load` decreases as distance increases for identical source records.
- `fio_concentration_at_boreholes.csv`: for two boreholes with different Q, concentration is lower where Q is larger, holding load constant.
- No NaNs in critical numeric outputs: `fio_load`, `surviving_fio_load`, `Q_L_per_day`, `concentration_CFU_per_L`.

### 11) CLI Usage
```bash
python -m BEST-Z.scripts.fio_runner
```
```bash
python -m BEST-Z.scripts.fio_runner --scenario '{"pop_factor": 1.25, "od_reduction_percent": 10}'
```

### 12) Logging and Traceability
- At each stage, log: files read/written, row counts, key columns present/mapped, defaults applied, scenario parameters resolved.
- Summarize: total surviving load to all boreholes; top-5 boreholes by `concentration_CFU_per_L`.

### 13) Non-Functional Requirements
- Deterministic outputs for fixed inputs.
- Reasonable performance with vectorized operations; avoid per-row Python loops where possible.
- No heavy new dependencies; rely on `pandas` and `numpy`.

### 14) Optional Future Integration (dashboard)
- Expose a simple function returning a GeoDataFrame of borehole concentrations for easy overlay in the dashboard (future work). Do not modify the existing dashboard now.


