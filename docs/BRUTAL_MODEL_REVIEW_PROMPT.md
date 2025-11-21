# BRUTAL MODEL ASSESSMENT

**FOR AI EDITOR: You are my senior technical reviewer. Your job is to brutally and honestly assess whether this model can be made useful using only code changes. Do NOT try to please me. If the model is not salvageable with the data we have, say so clearly and explain why. If it IS salvageable, say so clearly and explain why.**

---

## Context

* **Repo/source code**: `/Users/edgar/zanzibar/zanzibar-model`
* **Model goal (what it should predict)**: Predict fecal indicator organism (FIO) concentration in groundwater wells based on spatial proximity to pit latrines and septic tanks, accounting for pathogen decay and groundwater flow in a karst aquifer.
* **Outputs I'm comparing to reality**:
  * **Observed field name + units**: `fio_obs` (Total Coliforms, units = CFU/100mL, from `government_boreholes.csv`)
  * **Model prediction field name + units**: `model_conc` (field: `concentration_CFU_per_100mL`, units = CFU/100mL, from pipeline output)
* **Calibration results I'm seeing**:
  * **Samples**: 58 (60 government boreholes, 2 dropped due to missing Total Coli values)
  * **Correlation**: 0.15
  * **RMSE (log)**: 11.99
  * **Scatter shows**: Huge spread in predicted values even when observed values are low. Model predicts concentrations across 6+ orders of magnitude for similar observed values.
* **Data constraint**: We can't collect or change data. This is all the data we have.
* **Control constraint**: We can only change the source code, parameters, preprocessing, postprocessing, and calibration logic.

---

## Model Architecture Summary (for context)

1. **Inputs**:
   - Sanitation census (`data/input/sanitation_type.csv`): ~19,000 households with toilet types and locations
   - Borehole locations (`data/input/private_boreholes.csv`, `data/input/government_boreholes.csv`)
   
2. **Pipeline Steps** (see `app/engine.py`):
   - **Layer 1**: Calculate FIO load per household = `Population × EFIO × (1 - Containment_Efficiency)`
   - **Layer 2**: Use BallTree spatial search to find toilets within radius (35m government, 35m private), apply exponential decay: `Load × exp(-k × distance)`
   - **Layer 3**: Convert aggregated load to concentration: `Concentration = Aggregated_Load / Q_L_per_day × 100`

3. **Calibrated Parameters** (via grid search on 2025-11-20):
   - `EFIO_DEFAULT = 1e9` (CFU/person/day)
   - `KS_PER_M_DEFAULT = 0.05` (decay rate per meter)

4. **Known Issues**:
   - Flow rate `Q_L_per_day` may be missing/defaulted for many boreholes
   - Karst aquifers are highly heterogeneous (fractures create preferential flow paths not captured by the model)
   - Model assumes porous media transport, but reality includes conduit flow

---

## Your Tasks (do all, in order)

### 1. Understand the model pipeline in code
* Identify where inputs come from, how they're preprocessed, and where `model_conc` is computed.
* Map the full path from raw inputs → intermediate variables → final output.

### 2. Check dimensional / unit consistency end-to-end
* Track units through the code.
* Confirm that observed and predicted quantities are the same physical meaning (concentration vs load, per-day vs per-sample, log vs linear, etc.).
* If there is any mismatch, point to exact code locations and describe the mismatch plainly.

### 3. Reproduce (mentally or by reasoning) the calibration computation
* Locate code for RMSE/log transform/correlation.
* Verify log handling (especially zeros or near-zeros).
* Tell me if the metric implementation itself could be inflating error.

### 4. Find the dominant failure mode
* Is it systematic bias (always high/low)?
* Is it scaling/units (orders of magnitude mismatch)?
* Is it numerical instability / outliers?
* Is the model insensitive to key drivers?
* Back each claim with specific code evidence (file + function + line or snippet).

### 5. Assess salvageability under our constraints
* Given the fixed dataset and the current code structure, answer:
  **"Can code-only changes make this model decision-useful?"**
* Give a **yes/no** verdict up front.
* Then justify it with hard evidence from steps 1–4, not vibes.

### 6. If salvageable: propose concrete code changes
* Provide a prioritized list of fixes **we can actually implement in code**, e.g.:
  * unit conversion fixes
  * output rescaling / bias correction
  * log(x + ε) handling for both obs/pred
  * clipping / robust loss to reduce outlier dominance
  * parameter recalibration routines (grid search / optimization) using existing data
  * sensitivity analysis to find parameters that control magnitude
  * post-hoc calibration layer (e.g., monotonic regression / linear correction) with cross-validation
* For each fix:
  * explain **why it should help**
  * show **where in code to change**
  * mention **risk / downside**
  * say **how we test success**

### 7. If not salvageable: say it clearly
* Explain **exactly what blocks usefulness** given fixed data.
* Separate "code-fixable issues" from "data-limited issues."
* Tell me what minimum kind of new data would be required *in theory* (even though we don't have it), so I understand the ceiling.

### 8. Define a validation plan
* Tell me what plots/metrics I should regenerate after fixes.
* Give success thresholds (e.g., correlation target, RMSE-log target, visual trend expectations).
* Include cross-validation or holdout logic if possible with 58 samples.

---

## Output Format You MUST Follow

### A. Verdict (one sentence, YES or NO)
### B. Evidence (bullet points with code references)
### C. Root cause(s) ranked by impact
### D. Fix plan (prioritized, code-only, with exact locations)
### E. Validation plan + success thresholds
### F. If NO: hard blockers and why code can't solve them

---

## Tone Rules

* Be direct.
* No motivational language.
* No "could be / maybe" unless you explain uncertainty.
* If something is bad, say it's bad.
* If you don't find evidence, say "I don't have evidence for that."

---

## Key Files to Review

1. `app/engine.py` - Core pipeline (load calculation, transport, concentration)
2. `app/config.py` - Parameters (EFIO, decay rate, flow defaults)
3. `app/calibration_engine.py` - Spatial matching and metrics calculation
4. `app/calibration_utils.py` - Data loading and parsing
5. `app/calibrate_runner.py` - Grid search implementation
6. `data/input/government_boreholes.csv` - Observed data
7. `data/output/fio_layer3_concentration.csv` - Model predictions

---

## Expected Use Case After Fixing

If salvageable, the model should be able to:
1. **Identify the top 10% riskiest shehias** for intervention targeting
2. **Distinguish high-risk zones from low-risk zones** at a regional level (not individual wells)
3. **Inform policy decisions** about setback distances and sanitation infrastructure upgrades

The model does NOT need to predict individual well concentrations to ±10 CFU accuracy. It needs to correctly rank risk regions.


NOw go ahead and implement the plan. your objective is to achieve  target RMSE_log < 2 and Spearman/Kendall > 0.4 for trend utility. do whater that is profesionally acceptable and resonable to achieve the goal, don't stop until you achieve the goal, if it is impossible say why, eitherway leave back a .md file document what you have done your decisions, assumptions and recommandations