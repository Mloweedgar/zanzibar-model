### Objective

Make the Streamlit app in `app/dashboard.py` load quickly and reliably on Streamlit Cloud without breaking current functionality or UX. Keep behavior identical locally. Eliminate long startup and WebSocketClosedError issues by avoiding heavy work before first render, using progressive loading, caching, and graceful fallbacks.

### Context

- Entry point: `app/dashboard.py`
- Data: CSVs under `data/output/` and `data/derived/` with paths provided by `app/fio_config.py` and `app/config.py`.
- Mapping: `pydeck` with Mapbox (fallback to Carto when no token).
- Known Cloud issues observed:
  - Health check timing out (~60s) on first load.
  - WebSocketClosedError due to long blocking operations early in script execution.
  - Missing Mapbox token can hard-stop the app (must not).

### Do Not Break (Invariants)

- Keep all current toggles, legend, categories, and color semantics for borehole concentration categories.
- Preserve thresholds logic: prefer calibrated thresholds from `data/output/calibration_mapping.json`; use defaults if missing/invalid.
- Preserve file paths and data contracts from `app/fio_config.py`.
- Preserve UI labels and layout (sidebar form, toggles, legend). No new tabs, no redesign.
- Do not introduce new required services or credentials. Mapbox token must remain optional.
- No breaking dependency changes; do not remove existing packages. Only use packages already in `requirements.txt`.

### Performance Goals (Acceptance Criteria)

- First visible render (skeleton + sidebar) within 3–5s on Streamlit Cloud with cold start.
- Initial map paint within 10–15s using a limited dataset. No WebSocketClosedError in logs during/after first render.
- Background upgrade to full dataset after first paint, with the chart updating in-place without a full rerun.
- Health check (`/script-health-check`) responds in < 15s consistently after deploy.
- App does not hard-stop when `MAPBOX_API_KEY` is missing; shows a fallback basemap with an info note.

### Implementation Requirements

1) Robust imports
- In `app/dashboard.py`, ensure it imports `app.fio_config` and `app.fio_runner` whether executed as a script or a package. If `__package__` is empty, add the parent directory to `sys.path` and import via `from app import ...`.

2) Mapbox fallback
- Keep the current fallback: if `MAPBOX_API_KEY` is not present in `st.secrets` or env (`MAPBOX_API_KEY`/`MAPBOX_TOKEN`), use `map_provider='carto'` and `map_style='light'` and show a small `st.info` message. Do not stop the app.

3) Progressive loading (fast first paint)
- Load a small subset first (e.g., 5,000 rows per dataset) to render the map fast. After the first paint, load the full CSVs in the background and update the existing chart instance.
- Use a placeholder for the map: `placeholder = st.empty(); placeholder.pydeck_chart(deck_subset)` and later `placeholder.pydeck_chart(deck_full)`.
- Use environment variables to tune performance without code changes:
  - `FIO_MAX_POINTS` (default 8000): cap points rendered per layer.
  - `FIO_READ_NROWS` (default unset/None): optional row cap when reading CSVs. For first paint, pass an explicit smaller `nrows` (e.g., 5000), then load full.

4) CSV read performance and memory
- Only read columns needed for the map: `borehole_id,borehole_type,lat,long,concentration_CFU_per_100mL,lab_total_coliform_CFU_per_100mL,lab_e_coli_CFU_per_100mL,Q_L_per_day`.
- Use `engine='pyarrow'` if available, else fall back to pandas default with `low_memory=False`.
- Keep types consistent; provide a dtype map for numeric columns.

5) Caching
- Use `@st.cache_data(show_spinner=False)` on the CSV load function. Cache both the first-paint subset and the full load.
- Cache calibrated thresholds with `functools.lru_cache`. On failure/missing calibration, use default thresholds `(1e2, 1e3, 1e4)` and show a small info/warning, not an error.

6) Vectorized map prep
- Avoid per-row Python loops. Compute concentration categories and colors vectorized (e.g., via `pd.cut`) and map colors from a dict. Avoid building per-row HTML strings; use pydeck tooltip tokens instead.

7) Lazy heavy layers
- Only load `wards.geojson` when the “Ward boundaries” toggle is enabled. Do not read or parse it at startup otherwise.

8) UI responsiveness
- Wrap map rendering in `st.spinner('Rendering map...')` for first paint. Keep sidebar UI functional immediately.
- Ensure no blocking I/O (like large CSV loads) happens before the first few visible elements render.

9) Chart updating
- Use a placeholder pattern for progressive updates (see 3). Do not trigger a full rerun to update the map after loading full data.

10) Error handling and logging
- Swallow non-critical exceptions in background load/update paths and continue with the subset map.
- Do not log stack traces to the UI for expected fallback cases (missing token, missing calibration). Prefer `st.info`/`st.warning` with concise messages.

### Files You May Edit

- Required: `app/dashboard.py`
- Optional: None. Do not change other files unless absolutely necessary for correctness. If you must, explain why in comments near the change.

### What Not to Change

- Do not alter the scenario form behavior or scenario pipeline call except for performance wrappers (spinners). No async/threads.
- Do not alter CSV output formats or column names.
- Do not change color scheme or legend semantics.
- Do not add new heavy dependencies or services.

### Testing Instructions

Local quick test:
```bash
export MAPBOX_API_KEY=YOUR_TOKEN   # optional
export FIO_MAX_POINTS=6000
streamlit run app/dashboard.py
```
- Verify sidebar and legend appear within ~2–3s.
- Verify map renders within ~10s with subset; then updates to full within ~20–30s without page rerun.
- Toggle “Ward boundaries” and verify it loads only on demand.

Cloud test (Streamlit Cloud):
- Deploy on branch `main` with main module `app/dashboard.py`.
- Confirm health check returns < 15s and no `WebSocketClosedError` in logs.
- Confirm that missing Mapbox token uses Carto with an info note.

### Acceptance Checklist

- [ ] First UI render < 5s; initial map < 15s; no WebSocketClosedError.
- [ ] Progressive load updates map in place without full rerun.
- [ ] Works with and without `MAPBOX_API_KEY`.
- [ ] No changes to existing data contracts, toggles, legend, or colors.
- [ ] No new dependencies, no linter/type errors.

### Notes

- Keep code clear and readable. Prefer vectorized pandas operations and avoid deep nesting.
- Use guard clauses and minimal try/except blocks around optional features and background updates.

