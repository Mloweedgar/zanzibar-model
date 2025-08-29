# FIO Pathogen Modeling

Purpose. Shareable, code‑free guide to the formulas behind a FIO model, explicitly tied to what this repo does today and what we plan to add next. Use this document to lead a discussion with a sanitation expert to validate or replace assumptions before we wire more logic into the code.

Status in this codebase (today)

- Implemented (Layer 1 only — source load):
  - Per‑ward daily FIO load L [CFU/day] using population, per‑capita shedding, and removal efficiency.
  - Files: `BEST-Z/scripts/fio_load.py` (apply_scenario, aggregate_ward), `BEST-Z/scripts/config.py` (EFIO, mappings).
  - Current Zanzibar “reality” in code: all operational FIO removal efficiencies set to 0.00 in `config.FIO_REMOVAL_EFFICIENCY`.
- Not implemented yet (Layers 2–3 — survival and concentration):
  - No k (die‑off) or t (travel/retention) parameters by pathway/season.
  - No Q (flow) or conversion to CFU/100 mL at control points (wells/drains/beaches).
  - No routing splits (e.g., overflow to drain vs infiltration to groundwater), segments, or mixing rules.

How we intend to use this document

- Validate each symbol, unit, and formula with an expert.
- Replace defaults with locally defensible values (ranges: low/central/high).
- Decide the minimum viable model for Zanzibar we should implement now vs later.

---

## The three stackable layers (source → survival → concentration)

We build estimates in three steps. Each symbol is defined where it appears.

### Layer 1 — Net source load before the environment acts (implemented)

L [CFU/day] = Pop × EFIO × (1 − η)

What this means

- Start with how many people contribute (Pop), multiply by per‑person daily shedding (EFIO), then reduce by removal inside the sanitation system (η) before discharge.

Symbols and units

- Pop (persons): Number of people contributing to a pathway or node.
- EFIO (CFU/person/day): Per‑person daily FIO shedding; order‑of‑magnitude 1e9–1e11.
- η (0–1): Fraction removed before release (operational, not just design). LRV link: η = 1 − 10^(−LRV).

In this repo

- We compute ward‑level L today in `fio_load.py` as `population * config.EFIO * (1 - removal_efficiency)` and aggregate to `ward_total_fio_cfu_day`.
- Current defaults set η = 0 for all categories (None, PitLatrine, SepticTank, SewerConnection) to reflect current Zanzibar operational reality; scenarios can override.

Open validation points

- Is EFIO = 2×10^10 CFU/person/day appropriate for Zanzibar (E. coli)? Range to use? Seasonal variation?
- Practical, operational η by category in Unguja (OD, pit variants, septic practice, sewer w/o treatment). Distinguish design vs actual.

---

### Layer 2 — Survival (die‑off) during travel to the control point (not yet implemented)

L_out [CFU/day] = L × e^(−k t)

What this means

- As FIO travel from the source to a well/drain/shoreline, some die off. Exponential survival depends on die‑off rate k and travel/retention time t.

Symbols and shortcuts

- k [1/day]: Die‑off/inactivation rate (larger in sunlit/warm; smaller in shaded/cool/groundwater).
- t [day]: Travel/retention time.
- Half‑life: t_1/2 = ln(2)/k; T90: 2.303/k.

Pathway examples for k, t

- Sunlit drains/shoreline: higher k, short t (hours).
- Shaded channels/pipes: lower k, moderate t.
- Groundwater: very low k, longer t (days–weeks).

Segments and splits

- For multiple segments: multiply survivals, i.e., e^(−Σ k_i t_i).
- For routing splits (e.g., fraction α to drains, 1−α to groundwater): compute each branch and sum loads at the node.

In this repo (gap to fill)

- No k/t yet. We only compute L at ward level; no explicit nodes or pathways to apply survival.

Decisions needed from expert

- Typical k (low/central/high) for Zanzibar by environment (sunlit drains, shaded drains, pipes, groundwater) and by season.
- Typical t by pathway: distances/velocities/retention to beach outfalls, drains, and wells.
- How to partition flows by pathway for pits/septic (overflow vs infiltration) by setting α.

---

### Layer 3 — Convert surviving load to lab‑reported concentration (not yet implemented)

C_100mL [CFU/100 mL] = (L_out / Q [m³/day]) × 10^(−4)

What this means

- Divide the surviving daily load by daily water volume passing the point (CFU/m³), then convert to CFU/100 mL. 1 m³ = 10,000 × 100 mL, so multiply by 10^(−4).

Symbols

- Q [m³/day]: Flow at the control point (pipe/discharge/stream/near‑shore exchange, or abstraction at a well).

Why it matters

- Dilution: same L_out looks worse when Q is small (dry season, low well abstraction), better when Q is large. Common pitfall: use 10^(−4), not 10^(−5).

In this repo (gap to fill)

- We do not yet compute C_100mL. We only map `ward_total_fio_cfu_day`. No Q database and no control‑point geometry yet.

Decisions/data needed from expert

- Q categories or measurements for: drain mouths, ocean outfalls (by outfall), and typical community well abstraction.
- Near‑shore “exchange” volume or a pragmatic proxy we can defend.

---

## Bringing it to Zanzibar (how we’d wire this into the repo)

What we already do

- Household → Pop: handled via preprocessing and grouping by ward; FIO load computed with `config.EFIO` and category‑level η.
- Scenario levers we already have in `fio_load.apply_scenario`: population growth, open‑defecation reduction, pit→septic upgrades, and simple “improvement” placeholders for sewered/septic categories.

What we propose next (after expert validation)

- Define control points: list of drain mouths, ocean outfalls, and representative wells. Map wards/households to one or more control points with routing weights.
- Add pathway parameters: k, t by environment and season; α splits for pits/septic into drain vs groundwater.
- Add Q catalog: per control point; allow seasonal values or low/central/high.
- Compute concentration: produce C_100mL at control points and (optionally) aggregate indicators back to wards for visualization.
- Keep a transparent parameter table in `config.py` (or a CSV) with units and notes.

Pragmatic initial MVP (smallest step that’s defensible)

- Start with a few high‑priority control points (e.g., 3 main ocean outfalls, 2–3 busy beach sites, 2–3 wells).
- One seasonal split (dry vs wet): two sets of k, t, Q.
- Simple routing from nearby wards by distance or known drainage.

---

## Worked micro‑example (with unit checks)

Assume: Pop = 100,000; EFIO = 2×10^10 CFU/person/day; η = 0.7. Sunlit reach with k = 2.0/day; t = 0.25 day (6 h). Q = 50,000 m³/day.

Layer 1 (source)

- L = 100,000 × 2×10^10 × (1−0.7) = 6×10^14 CFU/day.

Layer 2 (survival)

- L_out = 6×10^14 × e^(−2.0×0.25) = 6×10^14 × e^(−0.5) ≈ 3.64×10^14 CFU/day.

Layer 3 (concentration)

- CFU/m³: L_out/Q = 3.64×10^14 / 5.0×10^4 = 7.28×10^9 CFU/m³.
- CFU/100 mL: × 10^(−4) → 7.28×10^5 CFU/100 mL.

Interpretation

- Improving η to 0.9 (better containment/treatment) reduces concentration ~3×.
- Smaller k (shaded/cool) increases concentration.
- Lower Q (dry season) increases concentration inversely.

---

## Validation questions for the expert (please mark up this list)


Shedding and indicators

- EFIO best‑estimate and plausible range (E. coli vs enterococci). Seasonal/temperature sensitivity worth modeling now?

Operational removal inside systems (η)

- Realistic operational removal efficiencies for Zanzibar today by category: None, PitLatrine types, SepticTank, SewerConnection. Distinguish design vs reality.
- Reasonable improvements under feasible near‑term interventions (FSM, basic treatment, partial sewer upgrades).

Survival parameters (k, t)

- Recommended k ranges for: sunlit drains, shaded drains, pipes, groundwater/karst. Seasonal values (wet/dry) if possible.
- Typical travel/retention times t to key control points. Any “typical” distances/velocities we can use.
- Whether to model multiple segments (e.g., pit→drain→shore) explicitly or collapse to a single effective k·t.

Routing and mixing

- Typical fraction α of pit/septic effluent that overflows to drains vs infiltrates to groundwater.
- Appropriate spatial units for routing (ward to nearest outfall? subcatchments?).

Flow/dilution (Q)

- Q for drain mouths and main ocean outfalls (typical and storm). For wells, typical abstraction rates.
- Near‑shore exchange or simple dilution proxies acceptable for first pass.

Outputs and thresholds

- Which indicator(s) to report (E. coli vs enterococci) at which locations.
- Reference thresholds to show alongside results (WHO/EU/US/TZ recreational, drinking).

Practicality and clarity

- Minimum viable set of parameters to publish with units and short notes (keep simple but defensible).
- Any parameters we should deliberately omit at first to avoid false precision.

---

## Implementation roadmap (once validated)


Small changes

- Add parameter tables (k, t, α, Q; low/central/high) to `config.py` or CSV under `data_raw/parameters/` with loader.
- Extend `fio_load.py` with optional survival and concentration calculation, gated by a feature flag.
- Add a minimal list of control points in `data_raw/` with IDs, type, lat/lon, and Q values.

Larger steps

- Routing from wards/households to control points (distance or predefined subcatchments).
- Multi‑segment survival and seasonal parameter sets.
- Dashboard maps for CFU/100 mL at control points and ward‑level summaries.

Quality checks

- Unit tests for: unit conversions (10^(−4) factor), segment chaining, routing splits, and edge cases (Q→0, k→0, η→1).
- Compare modeled concentrations against available Zanzibar measurements in `config.REAL_WORLD_CONTAMINATION` (sanity check only; indicator/species alignment needed).

---

## Mini glossary (units)

- FIO: Faecal Indicator Organisms (e.g., E. coli, enterococci).
- CFU: Colony‑forming units (lab count).
- EFIO [CFU/person/day]: Per‑person daily shedding.
- η [–]: Fraction removed inside the system (0–1). LRV [log10]: log removal; 1‑log = 90%.
- k [1/day]: Die‑off rate. t [day]: Travel/retention time. Q [m³/day]: Flow past the control point.
- Control point: Where concentration is assessed (outfall/well/beach/drain mouth).

Unit and conversion cheat‑box

- 1 m³ = 1,000,000 mL = 10,000 × 100 mL → multiply by 10^(−4) to convert CFU/m³ to CFU/100 mL.
- 1 L/s = 86.4 m³/day.
- If half‑life = 6 h (0.25 day): k = ln 2 / 0.25 ≈ 2.77 day⁻¹. If T90 = 1 day: k ≈ 2.30 day⁻¹.

---

Notes and caveats

- This draft is intentionally a strawman: some assumptions may be wrong. Please mark corrections directly in this file so we can implement the validated version.
- We will not implement Layers 2–3 until we have explicit parameter ranges and choices documented here.

Change log (fill during review)

- [ ] v0.1 (this draft): Source‑only model exists; survival/dilution pending expert input.
- [ ] v0.2: Parameters validated; implement MVP for a short list of control points.
- [ ] v1.0: Publish maps and tables with uncertainty bands.
