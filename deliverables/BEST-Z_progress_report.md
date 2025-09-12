### World Bank – Tanzania Country Office
### BEST-Z (Protecting Zanzibar’s groundwater, coastal and marine resources from poorly managed sanitation for blue economy dividends)
### Progress Report — Geospatial Programming Specialist (Modeller)

Report date: September 12, 2025  
Coverage period: Inception to date  
Prepared by: Geospatial Programming Specialist (Modeller)

---

## Executive summary

This progress report presents the work completed to quantify sanitation‑related fecal contamination risks in Zanzibar’s groundwater and to prepare decision‑ready, neutral outputs. In practical terms, we now have an island‑wide risk map identifying where groundwater is most exposed from nearby sanitation sources, together with a calibrated baseline against which sanitation investments can be compared.

Key achievements:
- Completed a high‑resolution, island‑wide groundwater risk model covering approximately 19,000 private wells and 60 government boreholes.
- Established a calibrated baseline reflecting current sanitation conditions and groundwater use.
- Enabled scenario testing for priority investments (reduce open defecation, upgrade pit latrines, improve centralized and fecal sludge treatment).
- Produced neutral, presentation‑ready outputs for dashboards and briefings (minimal text, clear indicators, safety benchmarks).

So what: These tools identify relative high‑risk areas and wells for monitoring and targeted sanitation investments, directly supporting the project objective to reduce wastewater impacts on groundwater and, by extension, coastal and marine ecosystems.

Status at a glance:
- Completed: Model build, baseline, initial insights, first set of visuals
- In progress: Scenario co‑design with specialists, training materials
- Upcoming: Stakeholder workshop, expanded scenario runs, results packaging

---

## 1. Mandate and scope (from TOR)

Role focus: design and implement geospatial processing, develop a practical GIS‑based modelling tool for pathogen flows to groundwater, simulate baseline and intervention scenarios, and prepare clear visual and written outputs with capacity‑building support.

This report is self-contained. All necessary context and results are summarized here for immediate review.

---

## 2. Progress against TOR deliverables

| TOR deliverable | Status | Outputs summary |
|---|---|---|
| Automated geospatial data workflows (cleaning, integration, preprocessing) | Completed | Reproducible preprocessing and enrichment steps for sanitation and borehole data |
| Processed, ready‑to‑use datasets | Completed | Cleaned and enriched datasets prepared for analysis and summaries |
| GIS‑based model for pathogen flows to groundwater | Completed | Island‑wide model estimating leakage, transport and dilution at each well |
| Baseline and intervention scenario capability | Completed (baseline); Ready (scenarios) | Calibrated baseline; scenarios configured for OD reduction, pit upgrades, treatment improvements |
| Visualizations and reporting tools | Completed (initial) | Neutral, minimal‑text summaries and dashboard‑ready layers |
| Capacity building materials | In progress | Draft presenter guidance and outline for training session |
| Comprehensive technical documentation | Completed (current scope) | Methods, calibration approach, scenario definitions and reproducibility notes |
| Presentations (briefings/decks) | In progress | Executive briefing visuals prepared; to expand for stakeholder sessions |
| Workshop/meeting reports and written responses | Ongoing/Pending | To be produced within required timelines following convenings |

---

## 3. Progress against team workplan (modeller contributions)

- **Activity 2.1–2.3 (Data collection and analysis)**: Completed initial cleaning and analysis of sanitation and borehole datasets; prepared working tables for modelling and summaries.
- **Activity 3.1 (High‑resolution geospatial model)**: Completed island‑wide groundwater model for fecal contamination risk (coverage: ~19,000 private wells and 60 government boreholes).
- **Activity 3.2 (Baseline scenario)**: Completed a calibrated baseline; model ranking aligns with available lab data.
- **Activity 3.3 (Investment scenarios)**: Set up realistic intervention scenarios ready for simulation and comparison.
- **Activity 3.4 (Training workshop)**: Draft materials and narrative prepared; scheduling pending.
- Activities 3.5–3.7 (sanitation solutions design/validation) are led by sanitation specialist; modelling will support targeting and impact projections.

---

## 4. Technical approach and accomplishments

- Modular architecture
  - Source loading: estimate releases based on households and containment performance.
  - Spatial transport: distance‑decay survival from source to well with type‑specific influence zones.
  - Concentration/dilution: convert surviving loads to concentrations using typical abstraction volumes.
- Calibration and evaluation
  - Rank‑based agreement with available laboratory data; limitations acknowledged due to many non‑detects.
  - Sensitivity analysis highlights transport parameter as a key driver.
- Automation and performance
  - Scripted orchestration of end‑to‑end runs; caching of neighbor relationships for speed.
  - Scenario parameterization enables rapid comparison of investment options.
- Decision‑ready outputs
  - Dashboard summaries for government and private wells; consistent categories and neutral presentation.
  - Baseline and scenario deltas to quantify improvements.

---

## 5. Early insights (so what?)

- Government boreholes tend to be cleaner than private wells, consistent with deeper drilling, better siting and higher pumping (more dilution).
- Around 15% of private wells appear at very high risk under current conditions; these areas are candidates for targeted sanitation upgrades and water safety actions.
- The single most impactful island‑wide measure is upgrading basic pit latrines in dense areas to better‑performing systems; open defecation reductions also help in specific locations.

### Management decisions enabled now
- Prioritize monitoring and water safety actions for the highest‑risk private wells and neighborhoods.
- Sequence sanitation investments to focus first on dense areas with clustered basic pit latrines near wells.
- Use the baseline as a reference to quantify expected improvements from proposed investments and report results consistently.

### Evidence of progress (selected outputs)
- Baseline summaries for government and private wells, including concentration distributions and risk categories.
- Scenario‑ready structure for OD reduction, pit upgrades and treatment improvements.
- Calibration summary and figures suitable for executive briefings.
- Dashboard‑ready tables and simple visuals aligned to neutral presentation standards.

---

## 6. How this supports project objectives

- It provides a neutral, evidence‑based map of where sanitation is most likely affecting groundwater quality today and how that could change with investments.
- It strengthens climate resilience planning by highlighting areas where improved sanitation protects groundwater quality and coastal ecosystems.
- It supports neutral, minimal‑text dashboards aligned with World Bank presentation standards and Government expectations.

### What I built and delivered (in plain terms)
- A practical, island‑wide groundwater risk map linked to sanitation patterns.
- A calibrated baseline representing today’s conditions.
- A scenario simulator to compare investment options and coverage levels.
- Clear, presentation‑ready summaries and visuals to brief decision‑makers.

---

## 7. Next steps (4–8 weeks)

- Co‑design detailed intervention scenarios with the sanitation and marine teams; run the comparisons and summarize results by hotspot and administrative units.
- Prepare clean stakeholder maps and short summaries (for example, where wells exceed simple safety benchmarks) to guide triage.
- Finalize and deliver a training session on how to interpret and use the model results.
- Plan linkage to marine exposure and habitat layers in collaboration with colleagues.

### Support requested
- Agreement on the 2–3 priority scenarios to run first (coverage levels and locations).
- Confirmation of preferred reporting benchmarks for “high risk” classification in briefings.
- Scheduling of the first training session with government counterparts.

---

## 8. Risks and mitigations

### Data and measurement risks
- Limited laboratory data (many non‑detects): Prioritize rank‑based validation and hotspot identification now; design a targeted sampling plan (add 15–20 sentinel sites with monthly sampling) to strengthen calibration in the next phase.
- Detection limit variability and lab QA/QC: Standardize detection limits across labs and document QA/QC procedures; use censoring‑aware statistics for analysis and report uncertainty bands alongside point estimates.
- Temporal mismatch (sampling vs. modeled steady‑state): Align future sampling windows with representative average conditions; flag out‑of‑season samples in analyses; conduct paired dry/wet season sampling to quantify seasonal effects.
- Sanitation type misclassification: Perform spot audits in high‑risk clusters; cross‑validate categories with photos/field notes where available; adjust containment assumptions locally where systematic misclassification is found.
- Geolocation accuracy (toilets and wells): Re‑validate coordinates for outliers and dense clusters; apply spatial jitter thresholds and plausibility checks; request corrections for flagged records from field teams.

### Model and parameter risks
- Containment efficiency values (literature‑based averages): Treat as priors; run sensitivity ranges by sanitation type; update values where field audits justify local adjustments; clearly label scenario results as conditional on these assumptions.
- Uniform household population per facility (due to missing counts): Apply conservative default with sensitivity analysis (±30–50%); prioritize collecting household size in hotspot clusters to localize estimates.
- Borehole abstraction rates (defaults/approximations): Use tiered defaults (private vs. government) with sensitivity ranges; request operator logs for major government boreholes to refine dilution estimates.
- Influence radii simplification (35 m private, 100 m government): Validate with targeted tracer/monitoring where feasible; explore variable radius scaling with pumping rate and hydrogeologic setting in an advanced phase.
- Uniform decay coefficient across soils/seasons: Report results as comparative (rank‑focused) rather than absolute; test alternative decay rates representative of wet/dry seasons and soil variability.
- Steady‑state assumption; no explicit groundwater flow direction: Document as a scoping simplification; plan optional flow‑informed weighting where hydrogeologic data become available; prioritize persistent hotspots for action irrespective of flow direction.
- Pathogen class differences (bacteria vs. viruses) not represented: State model scope (FIO as indicators); plan extension to include virus persistence parameters if policy questions require it.
- Non‑human sources excluded (livestock, agriculture, stormwater): Acknowledge scope; in mixed‑use areas, flag results as sanitation‑dominant only where corroborated; consider ancillary layers or field verification where non‑human sources are suspected.
- Distance metric simplification (surface distance, not 3D): Note simplification; where well depth and screened interval data are available, plan refinement to account for vertical separation effects.

### Scenario and interpretation risks
- Scenario coverage uncertainty (uptake, siting, O&M realism): Present results as ranges with conservative/base/ambitious coverage; co‑design scenarios with sector specialists and Government to reflect implementable pathways.
- Over‑interpretation of absolute concentrations: Emphasize ranking and comparative use for prioritization; pair maps with simple categories and clear caveats; include “do/don’t” guidance in briefing materials.
- Equity and inclusion: Data gaps may under‑represent vulnerable groups; include an equity lens in hotspot triage (schools/health facilities, low‑income areas); plan targeted data collection to close gaps.
- Climate/seasonality effects on loads: Flag baseline as average‑conditions; where policy requires, run seasonal sensitivity cases; avoid using average results alone to make monsoon‑season operational decisions.
- Regulatory thresholds alignment: Clearly state which benchmarks are used (e.g., WHO guidance); where national thresholds differ, produce dual‑threshold views to avoid confusion.

### Operational and integration risks
- Integration dependencies (marine module, habitat overlays): Define interface contracts and data hand‑offs; sequence work so groundwater deliverables proceed while marine integration is prepared in parallel.
- Data governance and availability: Establish a shared data catalog, access controls and versioning; agree update cadence with Government counterparts to prevent drift.
- Capacity and continuity: Prepare training materials and a handover plan (roles, contacts, SOPs); schedule at least one live session and one recorded walkthrough.
- Computational performance and reproducibility: Lock environment versions; document one‑click run steps; maintain cached neighbor relationships to ensure timely reruns.
- Field sampling logistics and procurement: Coordinate early with TTL and procurement; pre‑identify labs and backup providers; design simple chain‑of‑custody to protect data integrity.
- Change management and version control: Maintain a changelog of parameter updates and scenario definitions; tag milestones used in reports to ensure traceability.

---

## 9. Reproducibility and handover

- All analyses are fully reproducible; underlying scripts and environment are prepared for internal handover.
- Detailed technical documentation is available to the team and can be shared with counterparts as needed.
- A brief technical appendix or live walk‑through can be provided on request to support review.

---

## 10. Contact

Prepared by: Geospatial Programming Specialist (Modeller)  
Availability: As per contract; responses to document requests within 5 business days


