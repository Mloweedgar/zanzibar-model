# Zanzibar FIO Model – Recommendations

The current model structure (how it calculates and spreads contamination) is fine, but the inputs we have do not carry the signal we need. To make the model useful for ranking risky areas, we need a few concrete data upgrades. This note explains what, why, and how we would use them in simple terms.

## What already works
- The math steps are sensible: estimate germs released → fade with distance → dilute by how much water is pumped.
- The code is ready to accept better inputs; we can plug new tables in and rerun.

## What is missing (and examples)
1) **How water really moves underground**
   - What to collect: mapped fast paths and directions in the karst (from simple dye tracer tests or previous hydro studies), plus typical travel speeds.
   - Why: germs do not spread evenly in karst; they race along fractures. Knowing the paths lets the model decay germs along the real routes instead of in all directions.
   - Example: “Dye from Point A appeared at Well X in 6 hours, not at Well Y” → we draw a conduit from A to X and use that path length in the decay.

2) **How much each well pumps**
   - What to collect: average liters per day (or per week) per well, and how many hours per day it runs; rough seasonal multipliers if usage changes in dry season.
   - Why: more pumping = more dilution. Right now government wells are all fixed at 20,000 L/day and private wells around 2,000 L/day; that hides real differences.
   - Example: “Well X pumps 50,000 L/day; Well Y only 5,000 L/day” → X’s predicted concentration should be lower because it is more diluted.

3) **Realistic source strength at toilets**
   - What to collect: actual household population, toilet type, and how well each type contains waste (lining, emptying frequency, failure rate).
   - Why: we currently assume 10 people per household and coarse containment values, so most toilets look the same to the model.
   - Example: “Household has 4 people and a lined pit that rarely leaks” should count much less than “Household has 12 people and an unlined, overflowing pit.”


## Nice-to-have extras
- **Background floor:** add a small baseline concentration (e.g., median observed) so wells with near-zero flow do not collapse to zero in the model.
- **Shehia-level rollups:** if single wells stay noisy, we can average by shehia and compare ranks at that level for planning.

## How we would use the new data (no code detail)
- Flow paths and speeds: feed a table of “toilet → well → path length” into the transport step so decay follows the mapped conduits.
- Pumping volumes: place the measured liters/day directly in the borehole table; model will dilute accordingly.
- Source realism: update the toilet table with real populations and containment quality; the load step will scale emissions automatically.
- Timing: pick the right season or adjust multipliers when running the model to match the sampling dates.

## When we will call it “good enough”
- After plugging in the new data, we will check that rank correlations (Spearman/Kendall) exceed 0.4 and log RMSE drops below 2 on a simple 5-fold cross-check of the 58 government wells (or any future samples).
- Visual checks: a clearer upward trend on observed vs predicted (log scale) and residual maps without single wells dominating the errors.

## Bottom line
- The model code is ready; the blocker is missing field information. Priority ask: (1) karst flow paths and directions, (2) per-well pumping volumes/duty cycles, (3) better household counts and containment quality. With those, we can re-run and expect meaningful risk ranking; without them, further software tweaks will not create the needed signal. 
