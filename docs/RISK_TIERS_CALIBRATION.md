# Risk Tier Classification: Observed vs Model Predictions

## Summary

The Zanzibar FIO model systematically **overpredicts by 3.3×** even after fixing the unit conversion bug. Therefore, we use **different risk tier thresholds** for model predictions vs field measurements.

---

## Risk Tiers

### For Field Measurements (Observed Data)

Based on WHO drinking water guidelines for Total Coliforms:

| Tier | Range (CFU/100mL) | Label | Action |
|------|-------------------|-------|--------|
| **Low** | 0-10 | Safe | Routine monitoring, chlorination OK |
| **Medium** | 10-50 | Treatment Recommended | Enhanced monitoring, point-of-use treatment |
| **High** | >50 | Unsafe | Boil water advisory, find alternative source |

**Color coding:** 🟢 Green (Safe) → 🟠 Orange (Caution) → 🔴 Red (Danger)

---

### For Model Predictions (Calibrated)

Adjusted for 3.3× systematic overestimation:

| Tier | Range (CFU/100mL) | Corresponds to Actual | Action |
|------|-------------------|----------------------|--------|
| **Low** | 0-33 | ~0-10 actual | Continue routine monitoring |
| **Medium** | 33-165 | ~10-50 actual | **Priority for field sampling** to confirm |
| **High** | >165 | ~>50 actual | **Urgent field validation**, intervention planning |

**Why higher thresholds?**
- Model median prediction: 81 CFU/100mL
- Observed median: 24.5 CFU/100mL
- Ratio: 81 ÷ 24.5 = 3.3

So a model prediction of **33 CFU/100mL** likely corresponds to an actual value of **~10 CFU/100mL** (the Low/Medium boundary).

---

## Validation Results

Even with calibrated thresholds, performance remains poor:

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Tier Accuracy** | 19% | Model correctly classifies only 1 in 5 wells |
| **Top-20% Precision** | 17% | Of wells flagged as high-risk, only 17% truly are |
| **Top-20% Recall** | 17% | Model finds only 17% of actual high-risk wells |

**Conclusion:** Calibrated thresholds account for magnitude bias but **cannot fix fundamental ranking errors**.

---

## Implementation

### Files Created/Modified

- `app/risk_tiers.py` - NEW: Risk tier configuration module
- `app/post_calibration.py` - UPDATED: Uses calibrated thresholds for predictions

### Usage Example

```python
from app.risk_tiers import get_risk_tier, get_risk_color

# For model predictions
pred = 85  # CFU/100mL from model
tier = get_risk_tier(pred, is_predicted=True)  # → "Medium"
color = get_risk_color(pred, is_predicted=True)  # → Orange [255, 165, 0, 200]

# For field measurements
obs = 28  # CFU/100mL from lab
tier = get_risk_tier(obs, is_predicted=False)  # → "Medium"
color = get_risk_color(obs, is_predicted=False)  # → Orange
```

---

## Bottom Line

Use calibrated thresholds for **visual communication** and **relative comparisons**, not for **absolute well-level decisions**. The model can show "this area looks riskier than that area" but cannot reliably say "this specific well is unsafe."
