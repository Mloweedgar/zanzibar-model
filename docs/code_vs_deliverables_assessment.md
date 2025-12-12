# Allocation & TOR vs. Code – Deep Assessment

Sources reviewed: `docs/days_allocation_matrix.md`, `docs/modelling_tor.md`, full code/data in this repo (Feb 2026 snapshot). Evidence is limited to artifacts visible in the repository.

## 1) Allocation Matrix Activities vs. Code Evidence

| Activity (allocation matrix) | Days (alloc/claimed) | Evidence in repo | Status | What’s missing / risk |
| --- | --- | --- | --- | --- |
| Automated geospatial data workflows (clean/integrate/preprocess) | 6 / 8 | Sanitation standardization + intervention logic in `app/engine.py:77-199`; relies on pre-made derived inputs in `data/derived/*.csv`. | ⚠️ Partial | No reproducible ETL for borehole enrichment/adjacency caches; sanitation standardization is skipped when derived file exists, so there is no end-to-end rebuild from `data/input/*.csv`. |
| Processed & ready geospatial/time-series datasets | 6 / 6 | Processed CSVs in `data/derived/` and model outputs in `data/output/`. | ⚠️ Partial | Datasets are shipped, but regeneration scripts and provenance are absent; no time-series handling visible. |
| GIS-based model(s) for nutrient & pathogen flows | 9 / 12 | FIO load→transport→concentration pipeline in `app/engine.py:206-269`; nitrogen/phosphorus load calculators in same file; scenarios in `app/config.py:79-152`; calibration grid search + RF CV in `app/calibrate_runner.py:17-175`; CLI hooks in `main.py`; Streamlit dashboard in `app/dashboard.py`. | ⚠️ Partial | Nitrogen/phosphorus lack transport/dilution layers; marine/sewer network not modelled; calibration tests are stale (`tests/test_calibration.py` expects `obs_df` that does not exist), so validation is unproven. |
| Documented scenarios with maps/visuals (baseline vs scenario results) | 4 / 7 | Scenario definitions in `app/config.py:79-152`; scenario outputs `data/output/fio_baseline.csv`, `fio_scenario1.csv`, `fio_scenario2.csv`, `fio_scenario3.csv`; comparison charts `data/output/chart_mean_contamination.png`, `chart_high_risk_reduction.png`; dashboard views in `app/dashboard.py`; narrative docs `docs/scenario_feasibility_review.md`, `docs/sanitation_solutions_scenarios.md`. | ⚠️ Partial | Visuals depend on locally running Streamlit/CLI with pre-run data; no packaged map exports or written baseline-vs-scenario summaries; `analysis_runner` uses existing CSVs but is not tied to automated pipeline runs. |
| Comprehensive final report | 2 / 2 | No consolidated report artifact. | ❌ Not evident | Only supporting notes; nothing that reads as a final deliverable. |
| Training materials (manuals) | 2 / 0 | Quick dashboard guide `docs/dashboard_walkthrough.md`; setup/use basics in `README.md`. | ⚠️ Partial | No full user manual, training deck, or exercises; no troubleshooting/installation guide for stakeholders. |
| PowerPoint presentations (model development & application) | 2 / 2 | Legacy inception deck `docs/Inception Meeting Presentation on WB sanitation grant to Zanzibar_August 2024 (1).pdf`. | ⚠️ Partial | No deck reflecting current model, scenarios, results, or calibration. |
| Workshop/meeting reports (48h turnaround) | 2 / 0 | None. | ❌ Not evident | No workshop notes/templates in repo. |
| Written responses on team documents / project summary | 2 / 1 | None (only a drafting prompt `docs/ruth_response_prompt.md`). | ❌ Not evident | No actual responses or summary memos. |
| Contribute to final project report / journal article | 1 / 0 | None. | ❌ Not evident | No draft sections/outlines. |
| Bi-weekly progress reports | 2 / 1 | None. | ❌ Not evident | No progress logs. |
| Timesheets | 2 / 1 | None. | ❌ Not evident | No timesheet exports/templates. |

## 2) TOR Deliverables vs. Code Evidence

| TOR deliverable | Evidence in repo | Status | What’s missing / risk |
| --- | --- | --- | --- |
| Automated geospatial data workflows (clean/integrate/preprocess) | Sanitation standardization + scenario levers in `app/engine.py:77-199`; uses shipped derived borehole files. | ⚠️ Partial | No reproducible ETL from raw inputs to enriched boreholes/adjacency; manual preprocessing steps are opaque. |
| Processed and ready-to-use geospatial/time-series datasets | Shipped `data/derived/*.csv` and model outputs under `data/output/`. | ⚠️ Partial | Provenance undocumented; no time-series processing or refresh scripts. |
| GIS-based model(s) for nutrient & pathogen flow analysis | FIO transport model with BallTree decay + risk scoring, nitrogen/phosphorus load calculators, scenario toggles, calibration routines, dashboard (`app/engine.py`, `app/calibrate_runner.py`, `app/config.py`, `app/dashboard.py`). | ⚠️ Partial | Nutrient loads have no spatial transport; marine pathway not represented; calibration not exercised in tests; hard-coded assumptions for population/flow. |
| Well-documented model scenarios with maps/visualizations (baseline vs scenarios) | Scenario configs, scenario CSV outputs, comparison charts, Streamlit maps, scenario narrative docs. | ⚠️ Partial | No published map exports or written interpretation of scenario results; outputs rely on manual runs. |
| Comprehensive final report | None. | ❌ Not evident | Needs consolidated methodology + results + recommendations document. |
| Training materials (manuals) for stakeholders | Only the dashboard quick guide and README setup instructions. | ⚠️ Partial | No hands-on training manual, slides, or exercises. |
| PowerPoint presentations (model development & application) | Legacy inception PDF only. | ❌ Not evident | No up-to-date deck on the current model and findings. |
| Workshop/meeting reports | None. | ❌ Not evident | No reporting templates or completed reports. |
| Written responses on team documents / project summary | None. | ❌ Not evident | No responses or summaries stored here. |
| Contribution to final project report / joint journal article | None. | ❌ Not evident | No drafts/outlines visible. |
| Bi-weekly progress reports | None. | ❌ Not evident | No progress artifacts. |
| Timesheets | None. | ❌ Not evident | No timesheet files. |

## 3) Scenario Feasibility vs. Code (from `docs/sanitation_solutions_scenarios.md`)

| Scenario (intended actions) | Code evidence | Status | Gaps / proxies |
| --- | --- | --- | --- |
| 1) Targeted borehole protection + FSM rehab + CLTS | Scenario config `scenario_1_targeted` in `app/config.py:101-117`; targeted protection logic upgrades toilets within 35m of top-5% risk boreholes to septic with 0.8 efficiency (`app/engine.py:165-199`); runs through FIO pipeline; dashboard can visualize outputs. | ⚠️ Partial | FSM plant rehab and CLTS campaigning are not modeled; relies on pre-existing baseline run for risk ranking; no reporting artifacts beyond CSVs/Streamlit views. |
| 2) CWIS expansion (pit→septic upgrades, decentralized FSTPs, regulated emptying) | Scenario config `scenario_2_cwis` in `app/config.py:118-134` sets 95% OD reduction, 90% pit upgrades to septic, 90% FSM treatment; `apply_interventions` converts categories and bumps containment (`app/engine.py:140-159`); nitrogen/phosphorus loads computed (no transport); dashboard shows loads. | ⚠️ Partial | Decentralized treatment and regulated emptying are only represented as higher containment (0.8); no spatial targeting by wards/corridors; no plant capacity/logistics; nutrient transport/dilution absent. |
| 3) Stone Town centralized WWTP + CWIS complement | Scenario config `scenario_3_stone_town` in `app/config.py:135-152`; Stone Town bounding box toilets converted to sewer with treatment efficiency (`app/engine.py:201-218`); centralized treatment flag boosts sewer efficiency globally; CWIS-style upgrades also included. | ⚠️ Limited | Marine outfall removal and ocean water-quality impacts not modeled; sewer network/interceptor hydraulics absent; load reduction is the only proxy; dashboard cannot show marine plume effects. |

## 4) What’s Needed to Make Scenarios Fully Feasible (for additional days)

| Scenario | Current feasibility (per `scenario_feasibility_review.md`) | What’s needed to be fully feasible | Dependencies / risks (ties to day requests) |
| --- | --- | --- | --- |
| 1) Targeted borehole protection + FSM rehab + CLTS | Groundwater risk reduction is supported by current FIO model. | - Re-run baseline to refresh top-5% risk boreholes; package protection-zone upgrades as reproducible CLI step.<br>- Collect targeted private-well samples in predicted hotspots to validate improvements.<br>- Document/visualize before/after risk maps for reporting. | Needs field sampling and validation time; relies on fresh baseline run; FSM plant rehab/CLTS impacts remain qualitative (not modeled). |
| 2) CWIS expansion (pit→septic upgrades, decentralized FSTPs, regulated emptying) | Supported via containment-efficiency upgrades; no plant/logistics modeling. | - Parameterize regional/ward targeting instead of island-wide percentages.<br>- Add proxy levers for “managed emptying” (higher containment, reduced leakage) with sensitivity runs.<br>- Produce scenario write-up + map exports (N/P/FIO) to evidence benefits. | Requires data on actual upgrade/emptying coverage; nutrient transport still absent so N/P impacts are load-only; additional time to script exports and documentation. |
| 3) Stone Town centralized WWTP + CWIS complement | Only load-reduction proxy is feasible; marine plumes not modeled. | - Frame outputs as “sanitation load reduction” (FIO/N/P) for Stone Town; quantify tonnes/year avoided.<br>- Add simple sewer coverage toggle by ward instead of bbox heuristic; re-run scenarios accordingly.<br>- Provide narrative caveat: marine quality not simulated; treatment/transport hydraulics out of scope. | No pathway to true marine impact without new model; depends on accurate Stone Town boundary data; needs time for proxy reporting and comms materials. |

## 5) Data Required to Make the Model Reliable (from `docs/model_recommendations.md`)

| Data need | Purpose | Status in repo | Impact if missing | Action / owner |
| --- | --- | --- | --- | --- |
| Karst flow paths, directions, travel speeds (dye tests / hydro studies) | Replace isotropic decay with realistic conduits for FIO transport. | Not present. | Spatial ranking may be wrong where fractures dominate; risk hotspots may shift. | Commission tracer tests / compile existing hydro reports; encode toilet→well path lengths in transport layer. |
| Per-well pumping volumes and duty cycles (private + government) | Calibrate dilution (`Q_L_per_day`) and flow multipliers by borehole. | Not present (defaults 20k L/day gov, none for private). | Concentrations may be biased high/low; calibration ceiling capped by wrong dilution. | Collect meter readings / operator logs; update borehole tables with L/day and seasonal multipliers. |
| Household population per toilet + containment quality by type (lining, failure rate, emptying) | Scale loads and leakage realistically; differentiate pits/septics. | Not present (defaults: 10 ppl/HH; coarse containment map). | Loads nearly uniform; weak signal for spatial ranking and scenario effects. | Field survey / merge sanitation inventory with population and containment attributes; refresh `sanitation_standardized.csv`. |
| Expanded water-quality samples from private wells in predicted hotspots | Validate model ranking beyond gov wells; calibrate against real hotspots. | Not present (gov wells only, sparse positives). | Cannot verify/adjust hotspot predictions; risk comms less credible. | Targeted sampling campaign; geotag results to merge with model outputs. |
| Historical/expanded ZAWA/government lab data with GPS | Broaden calibration set; enable temporal checks. | Not present in repo (only bundled CSV). | Calibration metrics unstable; missing temporal variability. | Request full lab history with coordinates and dates; parse into calibration inputs. |
| Optional: background concentration floor and shehia-level rollups | Improve robustness when flows are near-zero; aggregate to planning units. | Not implemented. | Zero-flow wells may collapse to zero; high noise at point level. | Add small background term; compute shehia summaries post-run for reporting. |

## 6) Data We Have vs. Data We Need (evidence-driven)

| Data asset (raw) | What’s in the repo (evidence from `data/input`) | Reliability gaps / baked-in assumptions (code refs) | What’s still needed to make model reliable |
| --- | --- | --- | --- |
| Sanitation inventory (279,934 rows) | `data/input/sanitation_type.csv` columns: `fid, Latitude, Longitude, ..., Type, Descpt`; **no population column**. | `load_and_standardize_sanitation` injects default `household_population = 10` (`app/engine.py:99-105`); containment assigned from coarse map `{1:0.99, 2:0.10, 3:0.50, 4:0}` (`app/config.py:55-61`); no lining/emptying/failure info. | Collect/merge real household counts per toilet; add containment quality (lining, emptying frequency, failure rates); include these in raw input and re-standardize. |
| Private boreholes (18,916) | `data/input/private_boreholes.csv` with location fields and “Volume of tank being used in Liters (observation)” (no lab results). | `Q_L_per_day` in derived is inferred from tank volume (143–25,000 L/day) without pumping hours/duty cycle; no quality samples; no flow paths. Capture radius/decay fixed globally (`app/config.py:65-68`, `app/config.py:38-42`). | Gather measured pumping rates (L/day, hours/day, seasonality); sample private wells in hotspots; map flow directions/paths to replace isotropic decay; allow per-well radius/decay. |
| Government boreholes (60) | `data/input/government_boreholes.csv` has `Total Coli` + chemistry columns and lat/long; Q not in raw (fixed to 20,000 L/day in enrichment/engine). | Lab positives sparse (48/58 Total Coli); no pumping volumes, screened depth, or timestamps/history; Q fixed in code when missing (`app/engine.compute_concentration`). | Obtain full ZAWA lab history with GPS/timestamps/detection limits; measured pumping volumes/duty cycles; well construction (depth, screen). |
| Wards boundaries | `data/input/wards.geojson` (259 features). | Not used for targeting; Stone Town sewer uses bbox heuristic. | Use wards for Stone Town boundary, ward-level targeting/rollups, and reporting. |
| Baseline/outputs (FIO/N/P) | `data/output/fio_concentration_layer3.csv`, `nitrogen_load_layer1.csv`, `phosphorus_load_layer1.csv`. | Based on defaults: EFIO=1e7, ks=0.01, radius=10 m; population=10; containment coarse; gov Q fixed 20k, private Q inferred without provenance. | Re-run after raw data upgrades; record parameters with outputs; recalibrate with expanded observations. |

## 7) TOR-Aligned Plan to Lift Ranking/RMSE to Acceptable Levels

Targets: move Spearman toward ≥0.4 and log RMSE toward ≤2 (current best grid: Spearman 0.22, RMSE_log 3.10; RF upper bound: RMSE_log 2.25, Spearman 0.09).

| Focus area (TOR tie) | Concrete actions | Expected impact on metrics | Effort (days) |
| --- | --- | --- | --- |
| Data: dilution realism (processed datasets) | Collect per-well pumping volumes/duty cycles (gov + private); replace default Q in borehole tables; allow seasonal multipliers. | Reduces dilution bias; should lower RMSE_log and stabilize ranks. | 1–2 (if data provided), more if field collection needed. |
| Data: source strength realism (automated workflows) | Add household counts and containment quality to sanitation inventory; refresh `sanitation_standardized.csv`; update containment map by type/quality. | Introduces variance in loads → stronger spatial signal; improves rank correlations. | 2–3 (data ingest/clean + integration). |
| Data: validation signal (GIS model + calibration) | Expand lab samples: full ZAWA history + targeted private wells in hotspots; ensure geotags; rerun calibration. | More matched pairs increases ceiling for Spearman/Kendall; refines RMSE_log. | 1–2 once data available. |
| Model: parameter integration (GIS-based model) | Wire new Q and population/efficiency into pipeline; rerun baseline + scenarios; rerun calibration grid + RF CV. | Moves metrics toward targets if data variance exists; exposes true ceiling. | 2–3 (code adjustments + runs). |
| Reporting: scenario outputs (documented scenarios) | Regenerate maps/scorecards with updated runs; document provenance and confidence. | Communicates improved reliability; flags residual limits. | 1–2. |

If new data cannot be obtained, note explicitly that tightening assumptions alone is unlikely to lift Spearman >0.3 or RMSE_log <2.5; outputs should be framed as low-confidence. 
