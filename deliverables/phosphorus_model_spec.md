# Phosphorus Load Model (Parallel to Nitrogen)

Sibling specification to the nitrogen (N) load model. Structure, assumptions, and step ordering are identical to the N workflow; only compound-specific parameters change to reflect phosphorus (P) in household detergents.

---

## 1) Core Equation (annual household P load)

**P_h = Σ(Pop × D_c × 365 × P_d × (1 − PRE))**

Where:
- `Pop`: population served by the sanitation point (persons)
- `D_c`: daily detergent use per person (g/person/day)
- `P_d`: phosphorus content of detergents (fraction, 0–1)
- `PRE`: phosphorus removal efficiency for the sanitation type (fraction, 0–1)
- `P_h`: annual P released to the environment from that household (grams/year before unit conversion)

To stay consistent with the nitrogen outputs (kg/year), convert grams to kilograms at the end of the calculation: `P_h_kg = P_h / 1000`.

---

## 2) Inputs and Defaults (mirrors nitrogen inputs)

| Symbol | Description | Default / Source | Notes |
| --- | --- | --- | --- |
| `Pop` | Household population | `household_population` field after scenario pop factor | Same field used in N model |
| `D_c` | Daily detergent consumption (g/person/day) | 10 g/person/day | Configurable; keep units explicit |
| `P_d` | Phosphorus fraction in detergents | 0.05 (5%) | Configurable by scenario |
| `PRE` | Phosphorus removal efficiency | By sanitation type (see below) | Same sanitation categories as N |
| `toilet_category_id` | Sanitation technology ID | 1 sewer, 2 pit, 3 septic, 4 open defecation | Matches existing schema |
| `lat/long` | Point location | From sanitation census | Used for optional mapping |

**Phosphorus removal efficiency (`PRE`) by sanitation type (defaults aligned to nitrogen containment pattern):**
- Sewer (`1`): 0.50
- Pit latrine (`2`): 0.10
- Septic (`3`): 0.30
- Open defecation (`4`): 0.00

These mirror the nitrogen containment efficiencies so the workflow fits existing scenario overrides (e.g., upgrades, fecal sludge treatment) without new branching logic.

---

## 3) Step-by-Step Computation (same stages as nitrogen)

1. **Standardize + apply interventions**  
   - Load sanitation census, rename fields, drop bad coords (same as N).  
   - Apply `pop_factor` and toilet upgrades/efficiency overrides exactly as in the nitrogen pipeline so `Pop` and `PRE` reflect the scenario.

2. **Gross P generation (detergent-based)**  
   - `P_gross_g = Pop × D_c × 365 × P_d` (grams/year).  
   - Convert to kilograms for reporting: `P_gross_kg = P_gross_g / 1000`.

3. **Local removal/containment at the sanitation system**  
   - `P_captured_kg = P_gross_kg × PRE`.  
   - **Environmental release (net to environment)**: `P_env_kg = P_gross_kg × (1 − PRE)` (this matches the provided core equation).

4. **Optional pathway splitting (same pattern used for nitrogen’s “pathway tables”)**  
   - Define fractions by sanitation type that sum to 1:  
     - `f_gw`: fraction leaching to groundwater (default: sewer 0.10, septic 0.70, pit 0.90, OD 1.00)  
     - `f_coastal`: fraction routed to surface/coastal discharge (default: sewer 0.80 effluent share, septic 0.20 overflow, pit 0.05, OD 0)  
     - `f_soil`: fraction retained in soil/sediment (default: sewer 0.10, septic 0.10, pit 0.05, OD 0)  
   - Compute pathway loads:  
     - `P_gw_kg = P_env_kg × f_gw × (1 − soil_retention)`  
     - `P_coastal_kg = P_env_kg × f_coastal × (1 − coastal_treatment)`  
     - `P_soil_kg = P_env_kg × f_soil` (retained locally)  
   - Default attenuation factors: `soil_retention = 0.20`, `coastal_treatment = 0.30` (apply or set to 0 if not modeling attenuation beyond PRE).

5. **Aggregation (same outputs as nitrogen map layer)**  
   - Per-household record: keep `P_gross_kg`, `P_captured_kg`, `P_env_kg`, and optional `P_gw_kg`, `P_coastal_kg`, `P_soil_kg`.  
   - Spatial summary: sum by grid cell/shehia or export a point layer analogous to `nitrogen_load_layer1.csv`, e.g., `phosphorus_load_layer1.csv`.

---

## 4) Configurable parameters (defaults)

- `D_c` (daily detergent use): 10 g/person/day  
- `P_d` (P fraction in detergents): 0.05  
- `PRE` by sanitation type: sewer 0.50; pit 0.10; septic 0.30; OD 0.00  
- `f_gw`, `f_coastal`, `f_soil` by sanitation type: see Step 4 defaults  
- `soil_retention`: 0.20 (fraction retained before groundwater)  
- `coastal_treatment`: 0.30 (fraction removed in any coastal outfall treatment)  
- Scenario levers reused from nitrogen: `pop_factor`, `efficiency_override`, toilet upgrade fractions, fecal sludge treatment percent, centralized treatment flag.

---

## 5) Outputs (per sanitation point and aggregated)

- `P_gross_kg_per_yr`: annual P generated from detergents (pre-removal)
- `P_captured_kg_per_yr`: P held/removed at the sanitation system
- `P_env_kg_per_yr`: P released to the environment (net)
- Optional pathway fields: `P_gw_kg_per_yr`, `P_coastal_kg_per_yr`, `P_soil_kg_per_yr`
- Aggregated layers: sum over spatial units → `phosphorus_load_layer1.csv` (structure matches `nitrogen_load_layer1.csv` so dashboards/plots can swap data sources).

---

## 6) Pseudocode (mirrors nitrogen implementation style)

```python
for row in sanitation_points:
    pop = row.household_population
    dc = params.D_c  # g/person/day
    pd_frac = params.P_d
    pre = PRE_by_type[row.toilet_category_id]

    p_gross_g = pop * dc * 365 * pd_frac
    p_gross_kg = p_gross_g / 1000

    p_env_kg = p_gross_kg * (1 - pre)
    p_captured_kg = p_gross_kg * pre

    # Optional pathways
    f_gw, f_coastal, f_soil = pathway_fracs[row.toilet_category_id]
    p_gw_kg = p_env_kg * f_gw * (1 - soil_retention)
    p_coastal_kg = p_env_kg * f_coastal * (1 - coastal_treatment)
    p_soil_kg = p_env_kg * f_soil

    write_row(...)
```

---

## 7) Narrative-ready description (for reports)

We extend the existing nitrogen load engine to phosphorus without altering the workflow. Each sanitation point retains its population, location, and technology categorization. Gross phosphorus generation is tied to detergent use (`Pop × D_c × 365 × P_d`). Sanitation-type removal efficiency (`PRE`) reduces this load, producing the net annual phosphorus released to the environment. The same intervention levers used for nitrogen (population growth, toilet upgrades, fecal sludge treatment, centralized treatment) adjust populations and efficiencies before computing loads, so phosphorus scenarios can be analyzed alongside nitrogen.

For richer interpretation, the net phosphorus release can be partitioned into groundwater leaching, coastal discharge, and local soil retention using configurable fractions that mirror the nitrogen pathway setup. Outputs remain in kilograms per year and can drop into the same visualization and reporting slots as the nitrogen load layer, enabling side-by-side nutrient assessments without new code patterns.
