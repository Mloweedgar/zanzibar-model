# FIO Pathogen Modeling 


**What we’re estimating.** How much **faecal indicator organism (FIO)** contamination from toilets reaches places people care about (wells, drains, beaches), and what a lab would likely measure there.

---

## The Three Stackable Layers (source → survival → concentration)


### Layer 1 — Net source load before the environment acts

$\large L\,[\text{CFU/day}] = \text{Pop} \times EFIO \times (1 - \eta)$
**What this says in words:** Start with how many people are contributing, multiply by how many FIO a typical person sheds per day, then **reduce** that by how much the sanitation system removes **before** discharge.

**Symbols and units**

* **Pop** (persons): Number of people contributing to a given pathway or outfall.
  *Example:* people in households routed to a drain mouth or well.
* **EFIO** (CFU/person/day): Per‑person daily FIO shedding (order‑of‑magnitude 10^9–10^11).
  *Think of it as:* “daily FIO supply per person.”
* **$\eta$** (0–1): **Pathogen removal efficiency** inside the system (pit, septic, WWTP) **before** discharge.
  *Examples:* $\eta = 0$ means nothing removed; $\eta = 0.90$ means 90% removed.

**Why it matters:** This isolates **source control**. Improving $\eta$ (better containment/treatment) lowers L **linearly**.

---

### Layer 2 — Survival (die‑off) during travel to the control point

$\large L_{\text{out}}\,[\text{CFU/day}] = L \; e^{-k\,t}$
**What this says in words:** As FIO travel from the source to a beach/well/drain outlet, some die off. We model that with an exponential “survival fraction” controlled by **how fast they die** and **how long they travel**.

**Symbols and units**

* **k** (per day): **Die‑off (inactivation) rate**. Higher in **sunny/warm** conditions; lower in **cool/shaded/groundwater**.
* **t** (days): **Travel or retention time** from release to the control point.

**Helpful shortcuts**

* **Half‑life:** $t_{1/2} = \ln(2)/k$. “Time to cut by half.”
* **T90 (90% reduction time):** $T_{90} = 2.303/k$. “Time to 10% left.”

**Real‑world reading:**

* Sunny drain after rain → **larger** k (fast die‑off).
* Pipe or groundwater → **smaller** k (slower die‑off).
* Longer routes (bigger t) → more removal by nature.

**If there are multiple segments** (e.g., pit → drain → shore), we multiply survivals:
$L_{out} = L \; e^{-k_1 t_1} e^{-k_2 t_2} = L \; e^{-(k_1 t_1 + k_2 t_2)}$.

---

### Layer 3 — Convert surviving load to the concentration a lab reports

$\large C_{100\,\text{mL}}\,[\text{CFU/100 mL}] = \frac{L_{\text{out}}}{Q\,[\text{m}^3/\text{day}]} \times 10^{-4}$
**What this says in words:** Divide the surviving daily load by how much water passes the point each day (that gives **CFU per cubic meter**), then convert to the familiar **CFU per 100 mL** used by labs.

**Symbols and units**

* **Q** (m³/day): **Flow** past the control point (pipe/discharge/stream/near‑shore cell, or abstraction at a well).
* **10⁻⁴:** **Unit conversion** from per m³ to per 100 mL because **1 m³ = 10,000 × 100 mL**.
  *(Sanity check: 1 m³ = 1,000,000 mL; 100 mL is 1/10,000 of a m³.)*

**Why it matters:** **Dilution.** The same load looks **worse** (higher CFU/100 mL) when **Q is small** (dry season, small well) and **better** when **Q is large**.

> **Common pitfall:** Some notes use 10⁻⁵ by mistake. The correct factor is **10⁻⁴** because there are **10,000** portions of 100 mL in 1 m³.

---

## Bringing it to Zanzibar (how we’d use the layers)

* **Household data → Pop.** We know household locations and people per household, so we can total **Pop** feeding each relevant **control point** (ocean outfall, drain mouth, well/spring).
* **Toilet type → $\eta$.** Each sanitation pathway gets a **removal efficiency** reflecting *operational* performance in Unguja (to be confirmed together).
* **Pathway and distance → k and t.** We pick **k** and **t** based on the route: sunlit drains (higher k, short t), shaded channels (lower k), groundwater (very low k, longer t).
* **Local water flux → Q.** For a pipe or drain, Q comes from discharge estimates; for a well, Q is the **abstraction**; for near‑shore cells, Q reflects **exchange volume**. We can start with categories (low/medium/high) and refine.

---

## Worked micro‑example (with unit checks)

**Assume:** Pop = 100,000 persons; **EFIO = 2×10¹⁰ CFU/person/day**; **$\eta = 0.7$** (70% removed in the system). Sunlit reach with **k = 2.0/day**; travel time **t = 0.25 day (6 h)**. **Q = 50,000 m³/day.**

**Layer 1 (source):**
$L = 100{,}000 \times 2\times10^{10} \times (1-0.7) = 6\times10^{14} \;\text{CFU/day}$.

**Layer 2 (survival):**
$L_{out} = 6\times10^{14} \times e^{-2.0\times0.25} = 6\times10^{14}\times e^{-0.5} \approx 3.64\times10^{14} \;\text{CFU/day}$.

**Layer 3 (concentration):**
First, CFU per m³: $L_{out}/Q = 3.64\times10^{14} / 5.0\times10^{4} = 7.28\times10^{9} \;\text{CFU/m}^3$.
Convert to CFU/100 mL: multiply by **10⁻⁴** → **$7.28\times10^{5}$ CFU/100 mL**.

**Interpretation:**

* If **$\eta$** improves to 0.9 (e.g., better FSM/treatment), **Layer 1** drops by **×3**, and so does the final concentration (all else equal).
* If the reach is shaded/cool (**smaller k**), survival is **higher** → concentration increases.
* If **Q** drops by 10× (dry conditions), concentration rises **10×**.

---

## How to combine multiple sources and pathways (what happens in a ward)

Real places have **many households feeding the same point** and **multiple pathways**. We handle this by **summing loads** after applying the right $\eta, k, t$ for each group.

**Sum over contributing groups (g):**
$\large L_{out,\,node} = \sum_g \big(\text{Pop}_g \times EFIO \times (1-\eta_g)\big)\; e^{-k_g t_g}$
Then compute concentration at the node with the same **Layer 3** step using that node’s **Q**.

**Routing split example for pits/septic:** If some fraction **$\alpha$** of pit households overflow to drains and $(1-\alpha)$ infiltrate to groundwater, we make two groups with different **k, t, Q** and add them.

---

## Picking and validating the parameters (what we’ll decide together)

**EFIO (shedding):** Start around **2×10¹⁰ CFU/person/day** for E. coli; consider a low/central/high range (e.g., 1e10, 2e10, 5e10).
**$\eta$ (operational removal):** By pathway (OD, pit variants, septic practices, sewer without/with treatment). Keep **design** vs **operational** separate.
**k (die‑off) and t (travel time):** By pathway and **season**:

* Sunlit drains/shoreline: larger **k**, short **t** (hours).
* Shaded channels/pipes: smaller **k**, moderate **t**.
* Groundwater: very small **k**, longer **t** (days–weeks).
  **Q (flow):** Discharge/abstraction/exchange at each control point; use categories initially and refine.

**Good practice:** Publish each parameter with **units and a short note** (“sunlit, warm”, “shaded”, “karst groundwater”), and use **low/central/high** bands in maps and tables.

---

## Quick Zanzibar‑specific examples (to anchor discussion)

* **Ocean outfall near a popular beach:** Large **Pop** and low **$\eta$** (sewered but untreated) → big **L**; high sunlight (**higher k**) but short **t**; concentration depends strongly on near‑shore **Q** (exchange).
* **Drain mouth after storms:** Moderate **Pop**, mixed pathways; **t** short and **k** high (sunlit), but **Q** can be **very large** during storms → concentration may be lower than expected despite high loads (dilution).
* **Community well downslope of many pits:** **$\eta$** moderate; **k** low and **t** long; **Q** (abstraction) small → concentrations can be high even if loads seem modest.

---

## Common questions (and clear answers)

* **Why FIO instead of the pathogen itself?** FIO are faster and cheaper to measure and serve as an accepted **indicator** of faecal contamination and health risk.
* **Is exponential die‑off realistic?** It is the **standard first‑order** approximation. If we obtain better local data, we can refine with multi‑segment or temperature‑adjusted rates.
* **What if we don’t know Q well?** Start with **categories** (low/medium/high) and show how results change. Prioritize measuring **Q** at top hotspots.

---

## Mini glossary (units in brackets)

* **FIO:** Faecal Indicator Organisms (e.g., *E. coli*, enterococci).
* **CFU:** Colony‑forming units (lab count).
* **EFIO \[CFU/person/day]:** Per‑person daily shedding.
* **$\eta$ \[–]:** Fraction removed inside the system (0–1).
* **LRV \[log₁₀]:** Log removal; 1‑log = 90% removal.
* **k \[1/day]:** Die‑off rate.
* **t \[day]:** Travel/retention time.
* **Q \[m³/day]:** Flow past the control point (or abstraction at a well).
* **Control point:** Where we assess concentration (outfall/well/beach/drain mouth).

---

## Unit and conversion cheat‑box

* **1 m³ = 1,000,000 mL = 10,000 × 100 mL** → multiply by **10⁻⁴** to convert CFU/m³ to **CFU/100 mL**.
* **1 L/s = 86.4 m³/day** (useful for pipes/drains).
* **Half‑life ↔ k:** if half‑life = 6 h (0.25 day), then $k = \ln 2 / 0.25 ≈ 2.77 \;\text{per day}$.
* **T90 ↔ k:** if T90 = 24 h (1 day), then $k = 2.303 / 1 ≈ 2.30 \;\text{per day}$.

---

### Take‑home

These three formulas give a **transparent, parameter‑light** way to estimate and **discuss** pathogen exposure at the places that matter in Zanzibar. We can plug in **local values** for $EFIO, \eta, k, t, Q$, show **low/central/high** results, and quickly identify which **interventions** (containment, FSM, treatment, or managing flows) deliver the biggest reduction in **CFU/100 mL** at priority locations.
