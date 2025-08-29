# FIO Pathogen Modeling: A Layered Approach to Estimating Contamination

This document provides a structured explanation of how **faecal indicator organisms (FIOs)** can be modeled from source to environmental concentration. 

---

## 1. Introduction

**Goal:** Estimate how much faecal indicator organism (FIO) contamination from toilets reaches points of concern (e.g., wells, drains, beaches), and what levels a laboratory might measure there.

We use a **three-layered model**:
1. **Source load** (how much leaves people before environment).
2. **Survival/decay in environment** (loss over time and distance).
3. **Concentration at receptor** (dilution into receiving waters).

Each layer is mathematically defined and can be stacked together.


---

## 2. The Three Layers

### Layer 1 — Net Source Load

We first calculate the load of organisms leaving the population before environmental processes act:

$$
L \; [\text{CFU/day}] = \text{Pop} \times EFIO \times (1 - \eta)
$$

- **Pop** = number of people contributing (persons)
- **EFIO** = shedding rate (colony-forming units per person per day, CFU·person⁻¹·day⁻¹)
- **\( \eta \)** = engineered removal fraction (0–1), representing sanitation or treatment effectiveness

**Interpretation:** This is the total viable FIO released from sources per day before any natural decay.

---

### Layer 2 — Environmental Survival/Decay

As the FIOs travel, they undergo exponential decay:

$$
L_t = L \times e^{-k t}
$$

- **L** = initial load
- **t** = time in the environment (days)
- **k** = decay constant (day⁻¹), depends on environment (e.g., sunlight, temperature, pH)

Alternatively, if modeled spatially:

$$
L_d = L \times e^{-k_s d}
$$

- **d** = distance traveled (meters)
- **k_s** = spatial decay rate (m⁻¹)

**Interpretation:** Exponential decay captures how organisms lose viability as they persist in the environment.

---

### Layer 3 — Dilution into Receiving Waters

When FIOs enter water bodies, they are diluted:

$$
C = \frac{L_t}{Q}
$$

- **C** = concentration (CFU/L)
- **L_t** = viable load reaching the water body per day
- **Q** = discharge or water flux (L/day)

**Interpretation:** The larger the flow of the receiving water, the more diluted the organisms will be.

---

## 3. Combined Formula

By stacking the three layers, we obtain the final concentration at a receptor point:

$$
C = \frac{\text{Pop} \times EFIO \times (1 - \eta) \times e^{-k t}}{Q}
$$

This formula allows parameterization based on:
- population and sanitation coverage (\(\text{Pop}, \eta\))
- survival/decay dynamics (\(k, t\))
- hydrology (\(Q\))

---

## 4. Worked Example

**Scenario:**
- Population: 500 people
- Shedding rate (EFIO): $10^{9}$ CFU/person/day
- Removal fraction: $\eta = 0.5$ (50% removed by sanitation)
- Decay constant: $k = 0.7$ day⁻¹
- Travel time: $t = 1$ day
- River flow: $Q = 10^{7}$ L/day

**Step 1: Net source load**

$$
L = 500 \times 10^{9} \times (1 - 0.5) = 2.5 \times 10^{11} \; CFU/day
$$

**Step 2: After decay**

$$
L_t = 2.5 \times 10^{11} \times e^{-0.7 \times 1} \approx 1.24 \times 10^{11} \; CFU/day
$$

**Step 3: Final concentration**

$$
C = \frac{1.24 \times 10^{11}}{10^{7}} = 1.24 \times 10^{4} \; CFU/L
$$

**Result:** The expected concentration at the monitoring site is ~12,400 CFU/L.

---

## 5. Assumptions

- FIOs decay exponentially (well-established for bacteria and viruses).
- Population shedding rate is uniform (real-world: varies by health, diet, infection status).
- Removal fraction (\(\eta\)) represents sanitation effectiveness; must be site-specific.
- Hydrological mixing is assumed complete; partial mixing may lead to hotspots.

---

## 6. Geospatial Data Recommendations

To apply this model in **Zanzibar or similar regions**, recommended layers include:

- **Population density:** WorldPop, LandScan, or Tanzania Census data
- **Hydrology:** HydroSHEDS (rivers/streams), FAO AQUASTAT
- **Sanitation coverage:** DHS Program (household survey data)
- **Topography:** SRTM (Shuttle Radar Topography Mission) DEM for flow modeling
- **Land use:** OpenStreetMap (settlements, drainage, sewer networks)

These can be integrated into **GIS workflows** with tools like **PostGIS** or **QGIS**.

---

## 7. Mathematical Refresher

For readers less comfortable with mathematics:

1. **Exponential functions** ($e^{-k t}$): describe processes that shrink quickly at first, then more slowly. Common in decay, finance, and population growth.
2. **Logarithms**: inverse of exponentials. Useful for interpreting FIO data since contamination often spans orders of magnitude.
3. **Units and dimensional analysis**: Always track CFU/day vs CFU/L; consistency avoids errors.

**Suggested refresher topics:**
- Exponential and logarithmic functions
- Probability distributions (for uncertainty in parameters)
- Differential equations (for dynamic models)

---

## 8. Conclusion

This layered model provides a **transparent, adaptable framework** for estimating FIO contamination. It balances simplicity and rigor, making it useful for:
- Environmental health assessments
- Water safety planning
- Urban sanitation interventions

The model can be extended with **stochastic elements** (Monte Carlo simulations), **GIS spatialization**, or **empirical calibration** with local field data.

---

**Next Steps:**
- Apply the model to Zanzibar pilot sites.
- Collect local data on sanitation coverage and hydrology.
- Validate predictions against observed water quality.

