# BEST-Z Scenarios: How to Run

This guide explains how to prepare inputs and run the three BEST-Z report scenarios in the FIO model and view them on the dashboard.

Prerequisites
- Python 3.10+
- Create a virtual environment and install dependencies:
  - python -m venv .venv
  - source .venv/bin/activate    # on Windows: .venv\Scripts\activate
  - pip install -r requirements.txt

1) Prepare borehole flows (Q)
- Private wells: derives Q_L_per_day from the survey “volume” and “refill” fields
  - python main.py derive-private-q
- Government boreholes: assigns default Q_L_per_day from config
  - python main.py derive-government-q

2) Run the baseline (status quo)
- Generates baseline concentrations and adjacency caches used for targeted S1
  - python main.py pipeline --scenario crisis_2025_current

3) Scenario 1: Targeted Borehole Protection + FSM
Option A – Quick wins (global approximation)
- python main.py pipeline --scenario bestz_s1_targeted_bh_fsm
  What it simulates in this model:
  - CLTS-like OD reduction (global), pit→septic upgrades (global), FSM uplift (global). No spatial targeting.
  - Rapid, cost-effective approximations aligned with Scenario 1 intent (borehole protection + FSM rehab).

Option B – Targeted top 5% private BHs within 35 m (two-step)
- Step 1: Ensure the baseline has just been run (as in step 2)
- Step 2: Run targeted scenario (reads baseline concentration + adjacency cache):
  - python main.py pipeline --scenario bestz_s1_targeted_top5

4) Scenario 2: CWIS Expansion (programmatic upgrades + FSM)
- python main.py pipeline --scenario bestz_s2_cwis_expansion
  What it simulates in this model:
  - Large pit→septic conversion and strong FSM coverage across districts.
  - Decentralized FSTPs/WSPs are not explicitly modeled; their effect is proxied via the FSM percentage.

5) Scenario 3: Stone Town Centralized WWTP + CWIS
- Note: The model quantifies groundwater risk at boreholes. Marine outfalls are not modeled; centralized treatment is proxied by higher sewered containment.
  What it simulates in this model:
  - Raises sewered containment to 0.90 (proxy for centralized treatment) and pairs with CWIS upgrades/FSM for unsewered areas.
- python main.py pipeline --scenario bestz_s3_centralized_wwtp_cwis

6) Sensitivity: 2050 growth
- Apply to any scenario with pop_factor ≈ 2.47 (276,000 / 111,555):
  - python main.py pipeline --scenario '{"scenario_name":"S3_2050","pop_factor":2.47,"centralized_treatment_enabled":true,"sewer_efficiency_target":0.90,"infrastructure_upgrade_percent":20,"fecal_sludge_treatment_percent":40,"od_reduction_percent":10}'

7) View the dashboard
- python main.py dashboard
- Use the left sidebar to load scenario templates, adjust sliders, and re-run.

Notes and Tips
- Targeted S1 depends on the latest “baseline” run:
  - It reads data/output/fio_concentration_at_boreholes.csv and the adjacency cache data/derived/adjacency__crisis_2025_current__private__r35m.csv.
  - Always run the baseline just before bestz_s1_targeted_top5.
- Calibrated thresholds for map colors come from data/output/calibration_mapping.json. If missing or outdated, run:
  - python main.py calibrate
- If you see a scikit-learn import error during linking, ensure scikit-learn is installed (included in requirements.txt).
- Nitrogen model (optional):
  - Run: python main.py nitrogen-pipeline --scenario bestz_s2_cwis_expansion
  - Dashboard: python main.py nitrogen-dashboard

Phosphorus (planned)
- Status: Not yet implemented in the codebase. The current nutrient model covers nitrogen only.
- Proposed approach (to mirror nitrogen): add a phosphorus pipeline with per-capita P excretion and containment modifiers analogous to nitrogen, plus the same spatial transport if desired.
- Until implemented: use the nitrogen model as the nutrient load proxy in discussions, and the pathogen model for health risk targeting.
