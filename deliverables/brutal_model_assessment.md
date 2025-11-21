## Brutal Model Assessment — Zanzibar FIO Groundwater Model

### A. Verdict
**NO** – with current data and structure, code-only changes cannot make the model decision‑useful.

### B. Evidence (code + data)
- Magnitude driven by assumptions, not measurements: `household_population` is defaulted to 10 for every record (`app/engine.py:83`), inflating total load to ~2.8M assumed people without evidence. EFIO fixed at `1e7 CFU/person/day` (`app/config.py:41`) and applied uniformly (`app/engine.py:156-164`).
- Dilution is synthetic: government wells all assigned `Q_L_per_day = 20000` L/day (`app/preprocess_boreholes.py:129-139` → `data/derived/government_boreholes_enriched.csv`), not measured. Private flows are heuristics from tank volume × refill phrases.
- Transport ignores hydrogeology: contamination is purely isotropic distance decay within 35–100 m using haversine distance (`app/engine.py:181-222`), no flow direction, gradients, or karst conduits.
- Output units: concentration computed correctly as `(aggregated_load / Q_L_per_day) / 10` to CFU/100 mL (`app/engine.py:226-237`), so mismatch is not a units bug.
- Calibration metrics show no signal: Pearson r 0.147, Spearman ρ −0.077, RMSE_log (ln) 3.17, bias_log +0.86 on 58 matched samples (`app/calibration_engine.py:57-93` run on current files). Parameter sweeps for radius 20–1500 m and ks 0.001–0.05 kept Spearman in [−0.19, −0.02], confirming no recoverable trend.
- Outputs order-of-magnitude off: government wells median model 81 vs median obs 24.5 CFU/100 mL; private wells 99th percentile 132,848 CFU/100 mL (`data/output/fio_concentration_layer3.csv`), showing spread driven by assumptions, not observed gradients.
- Observation parsing collapses low values to zero (`app/calibration_utils.py:6-55`), already making log-metrics lenient; low correlation persists regardless.

### C. Dominant root causes
1) No hydrogeologic connectivity: Euclidean decay within 35–100 m cannot capture karst conduits or preferential flow; rank signal is absent (Spearman ≈ 0).  
2) Unmeasured source and dilution: uniform population=10 and EFIO=1e7, plus fixed/pseudo flows, set scale and spread arbitrarily.  
3) Weak target and sparsity: only 58 Total Coliform samples; many zeros; target organism differs from modeled generic FIO.  
4) Fragile preprocessing: references to undefined `GOVERNMENT_Q_L_PER_DAY_DEFAULT` in `app/preprocess_boreholes.py` would break reproducibility if rerun.

### D. Pragmatic code-only changes (will not fix core signal, but improve transparency/use)
- **Expose assumptions loudly**: Raise/ log warnings when `household_population` is filled with defaults and when Q is missing (`app/engine.py:60-236`); ensure `GOVERNMENT_Q_L_PER_DAY_DEFAULT` exists to keep scripts runnable. Benefit: stakeholders see where numbers come from; no accuracy gain. Test: rerun pipeline; check warnings and no runtime errors.
- **Post-hoc bias correction**: Fit `log(obs+1) ~ a*log(pred+1)+b` on the 58 pairs with 5-fold CV; apply as a correction layer before writing outputs (e.g., wrapper after `compute_concentration`). Benefit: reduces scale error; preserves ranks (which are already weak). Risk: overfitting tiny, noisy dataset; cannot fix ranking. Test: report CV RMSE_log and Spearman.
- **Rank-focused reporting**: Add tiering based on quantiles rather than absolute CFU (e.g., top 10/20/30% of model predictions) and label as “screening only.” Benefit: pragmatic communication; avoids pretending to deliver absolute accuracy. Test: compute top-20% overlap; expect low, but transparent.
- **Broader parameter search with rank objective**: Extend `app/calibrate_runner.py` to optimize Spearman instead of RMSE; log results to show lack of improvement. Benefit: documents futility; may find slightly less-bad bias. Risk: time cost; likely no gain. Test: output best Spearman; if still <0.2, document failure.

### E. Validation plan and thresholds
- Metrics to regenerate after any tweak: Pearson r, Spearman ρ, RMSE_log (ln) on matched 58 samples; top-20% overlap (precision/recall) of predicted vs observed.  
- Success thresholds for “decision-useful” (regional risk ranking): Spearman ρ ≥ 0.4, Pearson r ≥ 0.4, RMSE_log ≤ 1.5, top-20% precision/recall ≥ 0.5. Current results are far below.  
- Plots: log–log scatter of obs vs pred; residuals vs distance-to-nearest-toilet; rank histogram for tiers.

### F. Why code alone cannot salvage
- Missing essential data: no groundwater flow directions, gradients, or fracture network; no true pumping rates; household populations unknown. The predictor space lacks information that drives observed contamination in a karst aquifer.  
- Target mismatch and noise: 58 Total Coliform samples are sparse and weakly related to modeled FIO dynamics; many read as zeros.  
- Budget/field reality in Zanzibar: acquiring hydrogeologic characterization, pumping tests, or tracer studies is expensive and slow; without minimal directional flow data or better flow estimates, algorithms cannot infer conduit connectivity from sanitation density alone.

### G. Minimal data that would change the answer (if budget appears)
- Measured or even coarse directional flow/gradient per well (heads or inferred from topography/hydro maps) to weight upstream sources.  
- Actual pumping rates or mean daily abstraction per well type to anchor dilution.  
- Any tracer or dye tests identifying conduit paths for a subset of wells to validate connectivity assumptions.  
- Household counts or service population per sanitation point to replace the blanket “10 people” default.

### Practical recommendation (given budget constraints)
Use the current model only as a sanitation-density proximity screener, clearly labeled as “non-calibrated risk heuristic,” and prioritize data collection on flows and heads before further model tuning. Investing in transparent communication of uncertainties is more valuable than additional code tweaks under present constraints.
