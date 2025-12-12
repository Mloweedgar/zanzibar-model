# Prompt: Ruth Update and Additional Days Request (Zanzibar Model)

You are advising the STC Geospatial Programming Specialist to draft an email to Ruth (cc Victor, James) that responds to her three asks. Use the context below and produce the outputs in the requested structure.

## Context to ground your answer
- Timeline: Assignment runs Jul 1, 2025–Feb 28, 2026. By Fri Dec 12, 2025 Ruth wants: (1) confirmation of availability for a mid-Jan data validation workshop with Zanzibaris and a late-Feb full validation/sharing workshop; (2) confirmation that a draft report (plus training manual) can be finalized by late Jan and shared two weeks before the validation workshop; (3) an update on days used and additional days required to finish, including workshops.
- TOR deliverables (docs/modelling_tor.md): automated data workflows; processed datasets; GIS-based model(s); documented scenarios with maps/visuals; comprehensive final report; training materials/manuals; presentations; workshop reports within 48h; written responses; contribution to final report/journal article; bi-weekly progress reports; timesheets.
- Days allocation (docs/days_allocation_matrix.md): 40 days allocated, 40 claimed. Overruns: +2 data workflows, +3 GIS model, +3 scenarios. Zero balance on processed data and final report. Unused: training materials (2), workshop reports (2), written responses (1), journal article (1), bi-weekly reports (1), timesheets (1).
- Scenarios (docs/sanitation_solutions_scenarios.md): (1) Targeted borehole protection + FSM rehab + CLTS; (2) CWIS expansion (pit→septic upgrades, decentralized FSTPs, regulated emptying); (3) Stone Town centralized WWTP plus CWIS complement.
- Feasibility review (docs/scenario_feasibility_review.md): Scenario 1 & 2 fully supported by current groundwater-risk FIO model. Scenario 3: model cannot simulate marine dispersion or treatment plants/sludge logistics; can report load reduction as a proxy. Treatment plant performance and truck routing are out of scope.
- Model recommendations (docs/model_recommendations.md): main data gaps to improve rankings—(1) karst flow paths/directions and travel speeds, (2) per-well pumping volumes/duty cycles, (3) household population and containment quality. Nice-to-have: background concentration floor, shehia rollups. “Good enough” target: rank correlation >0.4, log RMSE <2 on 58 govt wells.
- Additional data asks: collect targeted groundwater quality samples from private wells (to validate high-risk predictions) and request more ZAWA/government water quality data, including historical series, with geotags to match boreholes.
- Workplan headline tasks (Draft_QII workplan): develop high-resolution geospatial model for nutrients/pathogens to marine and groundwater; use it to simulate sanitation investment scenarios; deliver training/sharing workshop on modelling approaches and preliminary results.
- Emphasis: the assistant should draw on a deep read of the current model code/limitations to justify any requested additional days for implementation and integration work.

## Tasks for the assistant
1) Map work done 1:1 to TOR deliverables, citing evidence from the docs and the allocation matrix (what was delivered, where time was spent for each TOR line item).
2) Identify remaining work 1:1 against TOR deliverables to finish by Feb 28: list concrete tasks (training materials/manual, workshop prep + reports, final report polish, scenario reruns/visuals, data upgrades/validation) with realistic day estimates and sequencing; call out dependencies/risks relevant to Zanzibar.
3) State what is needed to make all three scenarios fully feasible given current limits: specific data collection (including private-well samples and additional ZAWA/government historical water quality data), model tweaks, or proxies; emphasize the load-reduction framing for Scenario 3 and note out-of-scope items (marine water quality plumes, FSTP process modelling, sludge logistics).
4) Draft a concise email to Ruth (≤250 words) that: (a) confirms availability for mid-Jan and late-Feb workshops, (b) confirms plan to finalize draft report + training manual by late Jan and circulate two weeks before validation, (c) reports days used (40/40 with overruns on modelling/scenarios) and requests additional days with a brief justification tied to remaining tasks and workshop delivery. Keep tone practical and action-oriented.
5) Provide a table of data needs (what, why, format/attributes, source/responsible, due date) that can be delegated to a data person for collection; focus on what is needed to integrate and validate in the model.

## Output format
- Sections: Work Done; Remaining Work & Day Estimate; Making Scenarios Feasible; Draft Email to Ruth.
- Use numbered/bulleted lists, short sentences, and include day ranges where helpful. Be practical (Zanzibar constraints), not theoretical. Surface model limits (marine quality not simulated; treatment/transport not modelled) and propose pragmatic proxies (load reduction, containment-efficiency upgrades).
- Keep training/manual deliverables visible and scheduled; ensure timelines align with late-Jan draft and late-Feb validation.***
