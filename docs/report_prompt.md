Title: Commission a detailed Zanzibar FIO pathogen modelling report and presentation

You are a senior technical writer and data modeller. Using the codebase and outputs in this repository, produce two deliverables: a) a ready-to-submit detailed technical report for stakeholders (World Bank sanitation grant context) and b) a concise executive presentation for decision-makers. Follow the structure and tone of the template documents indicated below, while keeping findings neutral and evidence-led.

Ground rules and style
- Audience: mixed. Executives (WB/government), WASH/health specialists, and technical reviewers.
- Tone: neutral, factual, decision-useful; avoid prescriptive labels (no “hotspots”/“priority areas”). State what the numbers are; let readers infer good/bad. Cite assumptions and limitations clearly.
- Units: concentrations always in CFU/100mL. Loads in CFU/day. Distances in meters. Radii in meters.
- Maps/figures: use neutral legends; categories described below. Use semi-dynamic scales when needed to preserve contrast.
- Reproducibility: include clear steps to re-run the pipeline and calibration from this repo.

Source materials you must use
1) Repository content (pull paths and details directly):
   - app/fio_core.py (Layer 1: standardization, interventions, fio_load)
   - app/fio_transport.py (Layer 2/3: spatial links and concentrations)
   - app/fio_runner.py (orchestration, outputs)
   - app/fio_config.py (defaults, scenarios, paths)
   - app/dashboard.py (map UI logic, marker semantics, categories)
   - app/calibrate.py (rmse_log grid search; trend search: Spearman/Kendall/Pearson(log))
   - app/preprocess_boreholes.py (Q derivations)
   - data/output/ (dash_* CSVs, last_scenario.json, calibration_* results if present)
   - data/derived/ (enriched boreholes, standardized sanitation)
2) Stakeholder templates (match structure and emphasis):
   - docs/Inception Meeting Presentation on WB sanitation grant to Zanzibar_August 2024 (1).pdf
   - docs/Draft_QII (BEST-Z) workplan_2025.xlsx - Draft WPlan.pdf (modeler responsibilities)
3) Scientific framing (contextual citations; do not copy text):
   - Environmental Pollution (2024) “A spatial framework for improved sanitation…” (Fiji case). Key notions to reference: limited emptying/maintenance, on‑site lateral travel distances (~30–35 m), WWTP underperformance episodes, emphasis on relative patterns and limitations.

Core model description you must cover (from repo)
- Inputs: sanitation inventory (toilet category id), lat/long, household population default, enriched borehole Q (L/day).
- Layer 1 (app/fio_core.py):
  - fio_load = population × EFIO × (1 − containment efficiency η)
  - Interventions supported: od_reduction_percent, infrastructure_upgrade_percent, centralized_treatment_enabled, fecal_sludge_treatment_percent (row-splitting with mass preservation).
  - Efficiency map defaults (config.CONTAINMENT_EFFICIENCY_DEFAULT): 1: 0.55, 2: 0.15, 3: 0.55, 4: 0.00; scenario overrides allowed.
- Layer 2 linking (app/fio_transport.py):
  - Haversine/BallTree neighbor search; radius_m by borehole type.
  - Surviving load per link: fio_load × exp(−ks_per_m × distance_m).
- Layer 3 concentration (app/fio_transport.py):
  - Borehole concentration_CFU_per_100mL = sum(surviving loads to borehole) / (Q_L_per_day / 100).
- Radii: defaults in config.RADIUS_BY_TYPE_DEFAULT; currently private = 35 m, government = 100 m.
- Scenario in config.SCENARIOS["calibrated_trend_baseline"] (as of this repo):
  - EFIO_override = 1.0e7; ks_per_m = 0.06; radius private=35 m, government=100 m; efficiency_override {1:0.50, 2:0.10, 3:0.30, 4:0.0}.
- Dashboard semantics (app/dashboard.py):
  - Marker distinction: private = pin icon “tint”; government = pin icon “university”.
  - Concentration categories (by modeled CFU/100mL): low <10; moderate 10–99; high 100–999; very high ≥1000.

Calibration and evaluation methods you must compute and report
- Log-space RMSE: sqrt(mean((log10(model+1) − log10(lab+1))^2)).
- Rank correlation: Spearman ρ and Kendall τ across boreholes.
- Pearson correlation on log10(x+1).
- Optional: apply lab floor (lab=0→1 CFU/100mL) for sensitivity, and optionally restrict to lab ≥10 to focus on non‑censored points; report impact on metrics.
- Record n (boreholes with both modeled and lab values).

Figures and tables you must include (generate from data/output/*.csv)
- Map views (static exports or screenshots; if not available, include representative mockups with clear captions):
  - Modeled concentrations by borehole (private vs government pins), category legend included.
- Tables:
  - Summary of scenario parameters actually used (from data/output/last_scenario.json).
  - Per-borehole table (government): borehole_id, Q_L_per_day, modeled CFU/100mL, lab E. coli CFU/100mL (if available), absolute and log10 differences.
  - Top 10 highest modeled concentrations; top 10 largest abs log10 differences.
- Charts:
  - Modeled vs lab scatter (CFU/100mL, symlog axes); annotate 1:1 line; show Spearman/Kendall/Pearson(log) on chart.
  - Distribution comparison (private vs government modeled concentrations), log-count histograms.
- Sensitivity grid (if calibration results exist): small table of ks_per_m and EFIO combinations with rmse_log, and trend search results with Spearman.

Limitations and assumptions (explicitly address)
- Data quality and coverage; lab non-detects and censoring; on-site Q uncertainty; misclassification risk between “septic” and “permeable tanks”.
- Spatial linkage radius choices (35 m private, 100 m government) and ks decay parameter; absence of hydrological/plume modelling.
- WWTP performance variability; overflow events; seasonality; groundwater pathways not modelled.
- Model intent: relative prioritization and scenario exploration; not regulatory compliance assessment.

Policy/use-case framing (align to WB/grant context)
- How results inform relative risk patterns and where sanitation improvements may yield benefits.
- Scenario levers: OD reduction, pit upgrades, centralized treatment, fecal sludge treatment; expected qualitative effect paths.
- Implementation considerations: maintenance, emptying rates, enforcement, data needs.

Reproducibility section (must include exact commands)
- Environment: Python 3.10+, packages in requirements.txt.
- Preprocessing:
  - python man.py derive-private-q
  - python man.py derive-government-q
- Run pipeline with chosen scenario:
  - python man.py pipeline --scenario calibrated_trend_baseline
  - or any scenario name in app/fio_config.py, or inline JSON scenario.
- Calibration (if desired):
  - python man.py calibrate
  - python man.py trend

Deliverable A: Detailed technical report (target 15–25 pages plus appendix)
Use this chapter structure and fill with repository-specific content, figures, and tables:
1) Executive summary (1–2 pages): purpose, key findings (neutral), actionable next steps.
2) Background and objectives: Zanzibar sanitation context; what the model does/does not do; alignment to WB grant goals.
3) Data sources and preprocessing: sanitation inventory; borehole datasets; Q derivation; lab data; data dictionary.
4) Methods: Layer 1–3; equations; interventions; scenario configuration; parameter values; assumptions.
5) Calibration and evaluation: metrics (rmse_log, Spearman/Kendall, Pearson(log)); results; sensitivity; interpretation.
6) Results: maps, tables, distributions; private vs government comparison.
7) Scenario analysis: describe at least 2–3 contrasting scenarios and deltas vs baseline.
8) Limitations and uncertainties: candid discussion.
9) Recommendations and next steps: monitoring, data improvements, targeted interventions.
10) Reproducibility and how to run the model: step-by-step.
Appendix: Extended tables (per-borehole), parameter grids, scenario JSONs, code references.

Deliverable B: Executive presentation (10–15 slides)
Slide outline (each slide must be self-explanatory):
1) Title and purpose.
2) What we model (one-picture overview of Layer 1–3 and inputs/outputs).
3) Data and assumptions (bulleted, neutral).
4) How we link toilets to boreholes and compute concentrations.
5) Scenario used (parameters from last_scenario.json) and why.
6) Modeled concentrations map (legend included; private vs government pins).
7) Modeled vs lab: one scatter with metrics.
8) Private vs government distributions.
9) Key findings (neutral; patterns, not judgments).
10) Sensitivities and limitations (one slide).
11) Suggested next steps (data, interventions, monitoring).
12) Backup (optional): calibration grid, per-borehole table excerpt.

Acceptance criteria
- All metrics computed from current data/output CSVs; any missing data handled explicitly and stated.
- Units consistent; categories applied as specified.
- All figures/tables labeled and captioned; legends neutral.
- Reproducibility section contains exact commands and file paths from this repo.
- Presentation mirrors the report and is concise for executives.

What to include verbatim vs. paraphrase
- Include equations and parameter values exactly as used by the code (app/fio_core.py, app/fio_transport.py, app/fio_config.py).
- Paraphrase context/literature with citations; do not copy external text.

If something is missing
- If a specific file is absent, note it clearly, proceed with available data, and flag as a limitation.

Output format
- Report: well-structured Markdown or DOCX (preferred), with tables and embedded figures; provide a PDF export if possible.
- Slides: PowerPoint (PPTX) or Google Slides link; if not possible, provide a Markdown/Reveal.js deck or a slide-by-slide outline with figure placeholders.

Checklist before you finish
- [ ] Metrics computed and shown with n.
- [ ] Map legend and marker semantics explained.
- [ ] Scenario parameters table included (from last_scenario.json).
- [ ] Limitations/assumptions section present.
- [ ] Commands to reproduce runs included.
- [ ] Executive summary and recommendations are neutral and actionable.


