# Zanzibar Water Quality Dashboard — Quick Guide (Non‑Technical)

This short guide explains how to open the dashboard, switch layers, and read the colors and buckets during a presentation.

## 1) Launch the dashboard
1. From the repo root, run the FIO pipeline once (gives the maps data):
   ```
   python main.py pipeline --model fio --scenario baseline_2025
   ```
2. Start the dashboard:
   ```
   streamlit run app/dashboard.py
   ```
3. Open the URL Streamlit prints (usually http://localhost:8501).

## 2) Basic navigation
- Left sidebar controls everything:
- **View**: Pathogen Risk, Nitrogen Load, Phosphorus Load, Toilet Inventory.
  - **Scenario**: choose an intervention and read its description.
  - **Intervention sliders**: adjust OD reduction, pit→septic upgrades, FSM coverage, Stone Town WWTP. Press “Run with Custom Parameters” to recompute.
  - **Settings**: map style (Light/Dark/Satellite/Road), visualization type (Scatterplot/Heatmap), optional Wards layer.

## 3) Understanding the maps
- **Colors**: show relative risk/load; darker/brighter = higher.
- **Shapes**: circles mark boreholes/toilets; heatmaps show density or intensity.
- **Wards overlay** (toggle in Settings): outlines administrative boundaries. Hover inside a ward to see Ward, District, Region names.

### Pathogen Risk buckets (risk_score 0–100)
- 🔵 Safe **(0–25)**
- 🟢 Moderate **(25–50)**
- 🟡 High **(50–60)**
- 🟠 Very High **(60–90)**
- 🔴 Critical **(>90)**

Why these cut points?
- The model’s risk_score is `20 * log10(concentration + 1)`, clipped 0–100 (so a 10× jump in concentration adds ~20 points). It’s a compressed, log-scale “thermometer” that keeps low values visible and prevents extreme values from dominating.
- 0–25: “safe/low” keeps visually quiet areas genuinely calm.
- 25–50: early rise but still moderate; good for showing emerging hotspots.
- 50–60: narrow band to highlight the transition into “high”.
- 60–90: sustained high signal without overwhelming the map.
- >90: extreme outliers get their own band so they stand out immediately.

What is a risk_score and why use it?
- It translates raw concentration (CFU/100 mL) into a 0–100 scale that audiences recognize as a “risk gauge”.
- The log scaling mirrors how contamination spans orders of magnitude: each 10× jump adds ~20 points, so both low and high sites stay visible.
- Capping at 100 prevents a few extreme values from drowning out the rest of the map and keeps legends stable across scenarios.
- Why the “20 ×”? It mirrors a decibel-style transform: `20 * log10(x)` converts multiplicative changes into roughly linear point changes where 10× ≈ +20 points and 100× ≈ +40 points. Using 20 (instead of, say, 10) gives a comfortable 0–100 range for the concentrations we see, making the scale intuitive without needing to memorize raw CFU values.

Example:  
- 10 CFU/100mL → risk_score ≈ 20*log10(11) ≈ 20.8 → 🔵 Safe.  
- 100 CFU/100mL → ≈ 40 → 🟢 Moderate.  
- 1,000 CFU/100mL → ≈ 60 → 🟠 Very High.  
- 10,000 CFU/100mL → ≈ 80 → 🟠 Very High.  
- >100,000 CFU/100mL → ≈ 100 → 🔴 Critical.

### Nitrogen load buckets (data‑driven)
- Uses the 33rd and 67th percentiles of the current data.
- Labels show the numeric breakpoints, e.g.:
  - 🟢 Low (≤X)
  - 🟡 Moderate (X–Y)
  - 🔴 High (>Y)
- If all points are similar, everything shows as “Moderate (~uniform)”.

### Phosphorus load buckets (data‑driven)
- Same logic as nitrogen, with breakpoints printed in the labels:
  - 🔵 Low (≤X)
  - 🟣 Moderate (X–Y)
  - 🟤 High (>Y)
- If data is nearly uniform, everything is “Moderate (~uniform)”.

Why percentile-based for N/P?
- Loads vary per scenario; fixed thresholds would be misleading across runs.
- Using the 33rd/67th percentiles creates “Low/Moderate/High” buckets that adapt to each run while still keeping a balanced split.
- Example: if phosphorus load percentiles are 0.12 and 0.45 kg/yr, labels show 🔵 Low (≤0.120), 🟣 Moderate (0.120–0.450), 🟤 High (>0.450). In a different scenario the numbers change automatically.

How to read Nitrogen/Phosphorus loads
- Units: kg/year per point (no log transform).
- Buckets are relative to the current scenario: they show where a point sits within this run’s distribution, not against an external standard.
- “High” = top third of this scenario (useful for prioritizing hotspots), not necessarily “unsafe” in an absolute sense.
- If you see “Moderate (~uniform)”, the data are tightly clustered and slicing into thirds would be arbitrary.

## Calibration metric (RMSE in log space)
- The dashboard and calibration use `rmse_log` = `sqrt(mean((ln(pred+1) - ln(obs+1))^2))`.
- We add `+1` before the log so zeros (or very low values) don’t blow up the calculation; `ln(0)` is undefined, and `ln(1)` = 0 keeps near-zero values in-bounds.
- Interpret multiplicatively: `rmse_log` of 3 ≈ `exp(3)` ≈ 20× typical error; results are directional, not precise.
- A better fit is closer to 1 (≈ 2.7× error) or lower.

## 4) Presentation tips
- Start on **Pathogen Risk** with the Wards layer on to give geographic context.
- Mention the bucket ranges so the audience links colors to numbers.
- Switch map styles (Light/Dark/Satellite) if contrast is poor on a projector.
- Use the heatmap view to highlight clusters; switch back to scatter to show individual sites.
- For “what‑if” stories, adjust sliders, click **Run with Custom Parameters**, and show before/after changes. 
