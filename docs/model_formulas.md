# Model Formulas (FIO, Nitrogen, Phosphorus)

Simple reference for the core calculations used in the Zanzibar sanitation model.

## Common terms
- `pop`: household population at a sanitation point.
- `ce`: containment efficiency (fraction retained; leakage = 1 − ce).
- `Q`: daily flow at borehole (L/day); default 20,000 L/day if missing.
- `r`: distance (m) from a toilet to a borehole within the model radius.
- `ks`: decay rate per meter (FIO transport); default 0.01 /m.

## FIO (Faecal Indicator Organisms)
1) **Load at source (CFU/day)**
```
load = pop × EFIO × (1 − ce)
```
Default `EFIO = 1.0e7 CFU/person/day`.

2) **Transport/decay to each borehole within radius**
```
decayed_load = Σ_over_neighbors( load_i × exp(−ks × r_i) )
```
Radius defaults to 10 m (adjusted per scenario); `ks` defaults to 0.01 /m.

3) **Concentration at borehole (CFU/100 mL)**
```
conc = decayed_load / (Q × flow_multiplier) / 10
```
`flow_multiplier` defaults to 1.0; divide by 10 to convert CFU/L to CFU/100 mL.

4) **Risk score (0–100)**
```
risk_score = 20 × log10(conc + 1), capped at 0–100
```

## Nitrogen
1) **Load (kg/year)**
```
N_load = pop × protein_intake_per_capita × protein_to_N × (1 − ce) × 365
```
Defaults: `protein_intake_per_capita = 0.063 kg/person/day`, `protein_to_N = 0.16`.

## Phosphorus
1) **Load (kg/year)**
```
P_load = pop × detergent_use_g_per_capita × 365 × detergent_P_fraction × (1 − ce) / 1000
```
Defaults: `detergent_use_g_per_capita = 10 g/person/day`, `detergent_P_fraction = 0.05` (5% P).

## Scenario levers (how formulas change)
- **Containment efficiency (`ce`)**: upgraded by scenarios (e.g., OD/pit → managed septic) to reduce leakage for all pollutants.
- **Radius/decay (FIO only)**: scenarios can change borehole capture radius and decay rate (ks) to explore spatial influence.
- **Flow multiplier (FIO only)**: scales borehole flow `Q` to reflect pumping/usage assumptions.
- **Protein/P overrides (N/P)**: scenarios may adjust per-capita inputs/fractions if specified.***
