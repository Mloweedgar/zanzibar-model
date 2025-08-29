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


## 4. Assumptions

- FIOs decay exponentially (well-established for bacteria and viruses).
- Population shedding rate is uniform (real-world: varies by health, diet, infection status).
- Removal fraction (\(\eta\)) represents sanitation effectiveness; must be site-specific.
- Hydrological mixing is assumed complete; partial mixing may lead to hotspots.

---



## 5. Conclusion

This layered model provides a **transparent, adaptable framework** for estimating FIO contamination. It balances simplicity and rigor, making it useful for:
- Environmental health assessments
- Water safety planning
- Urban sanitation interventions

The model can be extended with **stochastic elements** (Monte Carlo simulations), **GIS spatialization**, or **empirical calibration** with local field data.

---