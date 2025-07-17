---
description: Repository Information Overview
alwaysApply: true
---

# BEST-Z Nitrogen Model Information

## Summary
BEST-Z is a geospatial modelling toolkit that quantifies nitrogen (N) loads from on-site sanitation across Zanzibar. The project is being architected to support additional nutrients (P) and pathogens (FIO) in subsequent phases. It combines Python data-science libraries, lightweight GIS tooling, and a Streamlit dashboard to translate raw census and sanitation data into actionable hotspot maps and scenario analyses.

## Current Sanitation Context in Zanzibar
According to the 2025 World Bank report, Zanzibar faces critical sanitation challenges:

- **Population**: 1,889,773 (2022 census) growing at 3.7% annually, with 47.3% concentrated in Mjini Magharibi (893,169 people)
- **Geology**: Coral rag limestone and karst landscapes make groundwater highly vulnerable to contamination
- **Sewered Systems**: Only 18% of urban populations connected to sewers, primarily in Stone Town
- **Non-Sewered Systems**: 47% use septic tanks/soak pits, often poorly constructed; 11.7% practice open defecation
- **Discharge Points**: 25 concrete sea outfalls release approximately 12,000 m³/day of untreated sewage directly into the Indian Ocean
- **Treatment Facilities**: Three main treatment sites with limited capacity:
  - Kibele: Integrated facility (50m³/day capacity) using planted sludge drying beds and constructed wetlands
  - Kizimbani: FSTP with 10m³/day capacity (currently non-operational)
  - Matemwe: Informal disposal site with no treatment

## Pollution Hotspots
- **Stone Town Seafront**: High bacterial contamination (up to 10,000 CFU) and elevated nutrient levels
- **Coastal Hotel Belt**: Tourism-related wastewater discharge
- **Agricultural Areas**: Nutrient runoff from farming activities
- **Urban Districts**: Industrial and market area pollution

## Why It Matters
- **Environmental health**: Excess N threatens coral reefs, seagrass, and groundwater quality—critical to Zanzibar's tourism and fisheries.
- **Investment guidance**: Load estimates feed cost-benefit analyses for upgraded toilets, DEWATS pilots, and nature-based solutions.
- **Scalable architecture**: Modular codebase allows for adding phosphorus, fecal contamination, or climate-change stressors without rewrites.
- **Public health**: 80% of marine pollution originates from land-based sources (UNEP, 2021), creating significant health risks.

## Repository Structure
```
BEST-Z/
├── scripts/                # All Python modules
│   ├── ingest.py           # Load & validate source datasets
│   ├── preprocess.py       # Harmonise CRS, tidy fields
│   ├── n_load.py           # Core N-load calculators
│   ├── fio_load.py         # (stub) Pathogen calculator placeholder
│   ├── viz.py              # Shared plotting helpers
│   └── interactive_dashboard.py
├── data_raw/               # Immutable inputs (census, shapefiles)
├── data_interim/           # Cleaned, intermediate artifacts
├── outputs/                # Scenario results & rendered maps
├── Dockerfile              # Reproducible build
└── run_dashboard.py        # Streamlit entry-point
```

## Language & Runtime
**Language**: Python 3.11  
**Environment**: requirements.txt + environment.yml (conda optional)  
**Container base**: python:3.11-slim with GDAL & GEOS pinned  
**GIS tooling**: GeoPandas 0.14, Shapely 2.0, GDAL 3.8

## Dependencies
**Main Dependencies**:
- pandas/geopandas: Tabular & vector processing
- numpy/xarray: Fast numerics for raster-like arrays
- rasterio: On-demand raster read/write (roadmap)
- folium: Leaflet web maps inside dashboard
- streamlit: Interactive UI & scenario parameter sliders
- pytest: Unit tests for formula integrity

## Build & Installation
**Local Installation**:
```bash
git clone https://github.com/your-org/best-z.git
cd best-z
pip install -r requirements.txt  # or: conda env create -f environment.yml
python run_dashboard.py          # launches on http://localhost:8501
```

**Docker Deployment**:
```bash
# Development mode
docker-compose up --build

# Production mode
docker-compose -f docker-compose.prod.yml up --build -d
```
*Note: docker-compose.prod.yml adds a reverse proxy and mounts /outputs to persistent storage.*

## Data Processing Workflow
1. **Ingest**: Read census CSV, sanitation-efficiency table, and ward GeoJSON
2. **Clean**: Standardize column names, fix CRS to WGS 84 / EPSG:4326
3. **Join**: Merge population with toilet-type efficiency data
4. **Scenario Apply**: Adjust for growth rates, toilet upgrades, or removal-efficiency tweaks defined in config.py
5. **Compute**: Call n_load.calc_n_load() to generate kg N yr⁻¹ per ward
6. **Aggregate & Save**: Write ward-level GeoJSON + CSV summary to outputs/
7. **Visualize**: viz.make_folium_map() renders an interactive choropleth for the dashboard

*Calibration placeholder: hooks exist for comparing modelled loads to field N-concentration samples.*

## Proposed Interventions for Scenario Modeling

The BEST-Z model is designed to evaluate the impact of various sanitation interventions. Based on the 2025 World Bank report and recent assessments from sanitation and marine experts, the following real-world interventions can be modeled as scenarios:

### Infrastructure Improvements
1. **Waste Stabilization Ponds at Kisakasaka**: 
   - Located 12 km south of Stone Town
   - Designed to serve the entire Stone Town area (addressing 12,000 m³/day of untreated sewage)
   - Scenario parameters: Increased removal efficiency for connected areas, reduced direct discharge
   - Current status: Proposed in World Bank report as priority intervention

2. **Decentralized Wastewater Treatment Systems (DEWATS)**:
   - Constructed wetlands at strategic locations
   - Reduces operational costs (fuel for sludge trucks) compared to current long transportation distances
   - Scenario parameters: Localized treatment efficiency improvements, reduced transportation emissions
   - Current example: Kizimbani DEWAT (10m³/day capacity, needs rehabilitation)

3. **Rehabilitation of Existing Facilities**:
   - Upgrade of Kibele treatment plant (currently 50m³/day capacity)
   - Formalization and upgrade of Matemwe disposal site (currently informal with no treatment)
   - Scenario parameters: Increased capacity and improved removal efficiency at specific locations
   - Current status: Kibele uses planted sludge drying beds and constructed wetlands but needs expansion

4. **Sewer Network Rehabilitation**:
   - Repair of broken sections and manholes in Stone Town's 32km pipe network
   - Address 25 concrete sea outfalls currently discharging untreated sewage
   - Scenario parameters: Reduced leakage, improved collection efficiency
   - Current status: Frequent blockages due to solid waste, no treatment plants

### Policy and Management Changes
1. **Sludge Disposal Regulation Enforcement**:
   - Target the 11.7% open defecation rate (highest in Kusini Unguja)
   - Address informal dumping at locations like Matemwe
   - Scenario parameters: Reduced illegal dumping, increased proportion of waste reaching treatment facilities
   - Current status: Limited enforcement, only 13 vacuum trucks available (2 owned by city council)

2. **Sewage Redirection**:
   - Redirecting sewage from Stone Town to pumping stations en route to treatment facilities
   - Target the 25 outfalls along the 7km Stone Town shoreline
   - Scenario parameters: Changed flow patterns, reduced direct marine discharge
   - Current status: Combined stormwater and sewage system with direct ocean discharge

### Specific Pollution Hotspots to Target
1. **Stone Town Seafront**:
   - Current data: Bacterial contamination up to 10,000 CFU; elevated ammonia, nitrate, and phosphate levels
   - Priority area due to tourism, fishing, and recreational activities

2. **Coastal Hotel Belt**:
   - Tourism-related wastewater discharge
   - Economic importance for Zanzibar's blue economy

3. **Urban Districts (Mjini Magharibi)**:
   - Highest population density (893,169 people, 47.3% of total)
   - Industrial and market area pollution

### Detailed Scenario Modeling Approach

The BEST-Z model can translate these interventions into quantifiable scenarios through specific parameter adjustments. Each scenario represents a different combination of interventions with varying implementation levels.

#### Key Scenario Parameters

1. **Nitrogen Removal Efficiency (NRE) Adjustments**:
   - **Baseline**: Current toilet-specific removal efficiencies (e.g., pit latrines: 10-30%, septic tanks: 30-50%)
   - **Kisakasaka WSP Implementation**: Increase NRE to 70-85% for Stone Town connected areas
   - **DEWATS Implementation**: Increase NRE to 60-75% for areas with new constructed wetlands
   - **Facility Rehabilitation**: Increase NRE from 40% to 65-70% in Kibele and Matemwe service areas
   - **Combined Interventions**: Spatially-explicit NRE improvements based on intervention coverage

2. **Sanitation Type Distribution**:
   - **Baseline**: Current distribution from census data
   - **Sewer Connection Expansion**: Increase percentage of households connected to sewers in Stone Town from current levels to 60-80%
   - **Septic Tank Conversion**: Convert basic pit latrines to improved septic systems in targeted wards
   - **DEWATS Coverage**: Define percentage of population served by new decentralized systems

3. **Spatial Implementation Scenarios**:
   - **Centralized Approach**: Focus improvements on Stone Town and immediate surroundings
   - **Hotspot Targeting**: Prioritize interventions in wards with highest current N loads
   - **Tourism Protection**: Prioritize coastal areas with high tourism value
   - **Groundwater Protection**: Focus on areas with vulnerable aquifers
   - **Equity-Based**: Distribute interventions to maximize population coverage regardless of load

4. **Temporal Implementation Scenarios**:
   - **Immediate Action**: Model all interventions implemented simultaneously
   - **Phased Approach**: Model sequential implementation over 5-10 years
   - **Population Growth Adjustment**: Factor in 2-3% annual growth while interventions are implemented

#### Example Scenario Definitions

1. **Business-as-Usual (BAU)**:
   ```python
   scenario_bau = {
       'name': 'business_as_usual_2030',
       'pop_factor': 1.25,  # 25% population growth by 2030
       'nre_override': {},  # No efficiency improvements
       'sanitation_shift': {}  # No change in toilet types
   }
   ```

2. **Kisakasaka WSP Implementation**:
   ```python
   scenario_kisakasaka = {
       'name': 'kisakasaka_wsp_2030',
       'pop_factor': 1.25,
       'nre_override': {
           'stone_town_wards': 0.80,  # 80% N removal for connected areas
       },
       'sanitation_shift': {
           'stone_town_wards': {'sewer_connected': 0.70}  # 70% sewer connection
       }
   }
   ```

3. **Decentralized DEWATS Focus**:
   ```python
   scenario_dewats = {
       'name': 'dewats_focus_2030',
       'pop_factor': 1.25,
       'nre_override': {
           'target_rural_wards': 0.65,  # 65% N removal in DEWATS areas
       },
       'sanitation_shift': {
           'target_rural_wards': {'improved_pit': 0.60, 'septic': 0.30}
       },
       'transport_distance': 'reduced'  # Lower transportation emissions
   }
   ```

4. **Comprehensive Improvement**:
   ```python
   scenario_comprehensive = {
       'name': 'comprehensive_2030',
       'pop_factor': 1.25,
       'nre_override': {
           'stone_town_wards': 0.80,
           'kibele_service_area': 0.70,
           'matemwe_service_area': 0.70,
           'rural_dewats_zones': 0.65
       },
       'sanitation_shift': {
           'stone_town_wards': {'sewer_connected': 0.70},
           'urban_wards': {'septic': 0.50, 'improved_pit': 0.40},
           'rural_wards': {'improved_pit': 0.60}
       },
       'regulation_enforcement': 'high',  # Reduced illegal dumping
       'transport_distance': 'optimized'  # Optimized sludge transport
   }
   ```

#### Evaluation Metrics

Each scenario can be evaluated using multiple metrics:

1. **Environmental Impact**:
   - Total nitrogen load reduction (kg N/year)
   - Spatial distribution of load reductions
   - Hotspot elimination effectiveness
   - Groundwater and marine ecosystem protection

2. **Implementation Feasibility**:
   - Infrastructure requirements
   - Capital and operational costs
   - Implementation timeline
   - Technical capacity requirements

3. **Socioeconomic Factors**:
   - Population served by improved sanitation
   - Health outcome improvements
   - Tourism industry protection
   - Equity of intervention distribution

The model outputs can be visualized as comparative choropleth maps, difference maps between scenarios, cost-effectiveness charts, and multi-criteria decision analysis tables to support evidence-based sanitation planning.

#### Implementation Considerations and Challenges

After reviewing the actual codebase, several important considerations and challenges must be addressed to implement the proposed scenarios:

##### Code Structure Limitations and Required Extensions

1. **Current Scenario Parameter Limitations**:
   ```python
   # Current scenario structure in config.py
   SCENARIOS = {
       'baseline_2022': {
           'pop_factor': 1.0,
           'nre_override': {}
       },
       'improved_removal': {
           'pop_factor': 1.0,
           'nre_override': {'1': 0.80, '2': 0.80, '3': 0.80, '4': 0.80}
       }
   }
   ```
   
   - **Challenge**: The current implementation only supports global `pop_factor` and toilet-type based `nre_override`. The proposed scenarios require ward-specific parameters and sanitation type shifts.
   - **Solution**: Extend the scenario dictionary structure to include spatial targeting and sanitation distribution changes.

2. **Spatial Targeting Implementation**:
   - **Challenge**: The code doesn't currently support ward-specific interventions (e.g., "Stone Town wards" vs. "rural wards").
   - **Solution**: Create ward classification lookup tables and modify `apply_scenario()` to handle ward-specific parameter adjustments.

3. **Sanitation Type Shifts**:
   - **Challenge**: The current model calculates loads based on existing toilet distribution but doesn't model transitions between types.
   - **Solution**: Add a preprocessing step to redistribute population across toilet types based on scenario parameters before calculating loads.

##### Data Requirements and Assumptions

1. **Ward Classification Data**:
   - **Assumption**: We need to define which wards belong to "Stone Town", "urban", "rural", etc.
   - **Required Data**: Create a ward classification table with categories for targeting interventions.

2. **Service Area Definitions**:
   - **Assumption**: Kisakasaka WSP, Kibele, and Matemwe service areas need geographic definition.
   - **Required Data**: Define which wards would be served by each facility.

3. **Baseline Efficiency Values**:
   - **Assumption**: Current code uses a sanitation efficiency table with fixed values.
   - **Validation Needed**: Verify that baseline removal efficiencies match real-world conditions in Zanzibar.

4. **Population Projections**:
   - **Assumption**: Linear growth factor applied uniformly across all wards.
   - **Improvement**: Consider ward-specific growth rates based on urbanization patterns.

##### Implementation Roadmap

To enable these advanced scenarios, the following code changes are needed:

1. **Extended Scenario Structure**:
   ```python
   # Example of extended scenario structure
   scenario_extended = {
       'name': 'kisakasaka_wsp_2030',
       'pop_factor': 1.25,  # Global factor
       'pop_factor_by_ward': {  # Ward-specific overrides
           'urban_wards': 1.35,  # Higher growth in urban areas
           'rural_wards': 1.15   # Lower growth in rural areas
       },
       'nre_override': {  # Global toilet-type overrides
           '1': 0.60  # Improved efficiency for type 1 toilets everywhere
       },
       'nre_override_by_area': {  # Area-specific overrides
           'stone_town_wards': {'1': 0.80, '2': 0.80}  # Higher in Stone Town
       },
       'sanitation_shift': {  # Changes in toilet type distribution
           'stone_town_wards': {'sewer_connected': 0.70}
       }
   }
   ```

2. **Enhanced apply_scenario Function**:
   ```python
   def apply_scenario_enhanced(pop_df, scenario, ward_classifications):
       """Enhanced version that handles spatial targeting and sanitation shifts."""
       df = pop_df.copy()
       
       # Apply population factors (global and ward-specific)
       df['population'] = df['population'] * scenario.get('pop_factor', 1.0)
       
       # Apply ward-specific population factors
       if 'pop_factor_by_ward' in scenario:
           for area_type, factor in scenario['pop_factor_by_ward'].items():
               area_wards = ward_classifications[area_type]
               mask = df['ward_name'].isin(area_wards)
               df.loc[mask, 'population'] = df.loc[mask, 'population'] * factor
       
       # Apply sanitation shifts before efficiency calculations
       if 'sanitation_shift' in scenario:
           df = apply_sanitation_shifts(df, scenario['sanitation_shift'], 
                                       ward_classifications)
       
       # Apply removal efficiencies (similar to current implementation but extended)
       df['nre'] = df['nitrogen_removal_efficiency'].astype(float)
       
       # Global toilet-type overrides
       for ttype, val in scenario.get('nre_override', {}).items():
           mask = df['toilet_type_id'].str.lower() == ttype
           df.loc[mask, 'nre'] = float(val)
       
       # Area-specific overrides
       for area_type, overrides in scenario.get('nre_override_by_area', {}).items():
           area_wards = ward_classifications[area_type]
           for ttype, val in overrides.items():
               mask = (df['ward_name'].isin(area_wards) & 
                      (df['toilet_type_id'].str.lower() == ttype))
               df.loc[mask, 'nre'] = float(val)
       
       # Calculate load (same as current implementation)
       df['n_load_kg_y'] = (
           df['population'] * config.P_C * 365 * config.PTN * (1 - df['nre'])
       ) / 1000
       
       return df
   ```

3. **Ward Classification System**:
   ```python
   # Example ward classification dictionary
   ward_classifications = {
       'stone_town_wards': ['Stone Town', 'Mji Mkongwe', ...],
       'urban_wards': ['Kiembe Samaki', 'Magomeni', ...],
       'rural_wards': ['Kinyasini', 'Mwera', ...],
       'kibele_service_area': [...],
       'matemwe_service_area': [...]
   }
   ```

##### Critical Assumptions

1. **Nitrogen Production Rate**:
   - The model uses fixed values for protein consumption (P_C = 64 g/day) and protein-to-nitrogen conversion (PTN = 0.16).
   - **Assumption**: These values are appropriate for Zanzibar's population and diet.
   - **Sensitivity**: Results are directly proportional to these values; a 10% change in P_C means a 10% change in all loads.

2. **Removal Efficiency Reality**:
   - **Assumption**: The proposed improved removal efficiencies (60-85%) are achievable with the suggested technologies.
   - **Validation Needed**: Field testing to confirm actual performance in Zanzibar's climate and operating conditions.

3. **Implementation Feasibility**:
   - **Assumption**: The proposed sanitation shifts (e.g., 70% sewer connection in Stone Town) are achievable.
   - **Reality Check**: Consider physical, financial, and social constraints to implementation.

4. **Spatial Uniformity**:
   - **Assumption**: Interventions affect all households in a ward equally.
   - **Limitation**: In reality, implementation would likely be patchy within wards.

By addressing these considerations and implementing the suggested code extensions, the BEST-Z model can effectively evaluate the proposed interventions and provide valuable insights for sanitation planning in Zanzibar.

## Practical Implementation Assessment for Zanzibar Context

After reviewing the available data and code structure, here's a practical assessment of what's realistically implementable in the Zanzibar context, categorized by feasibility:

### Immediately Implementable Scenarios (Low-Hanging Fruit)

1. **Population Growth Projections** (PRACTICAL)
   - **Current Data**: Census data already available
   - **Implementation**: Simple modification to existing `pop_factor` parameter
   - **Zanzibar Context**: Population growth is well-documented; 2-3% annual growth rate can be applied
   - **Code Changes Needed**: None, already supported

2. **Global Toilet Efficiency Improvements** (PRACTICAL)
   - **Current Data**: Sanitation efficiency table already exists with toilet types
   - **Implementation**: Use existing `nre_override` parameter
   - **Zanzibar Context**: Realistic for policy planning to model uniform improvements
   - **Code Changes Needed**: None, already supported

3. **Basic Stone Town vs. Rural Distinction** (PRACTICAL)
   - **Current Data**: Ward names in census data can be manually classified
   - **Implementation**: Create a simple lookup dictionary of Stone Town wards
   - **Zanzibar Context**: Clear geographic distinction exists between Stone Town and other areas
   - **Code Changes Needed**: Minor - create ward classification dictionary

### Moderately Complex Scenarios (Requires Some Extension)

1. **Kisakasaka WSP Implementation** (MODERATELY PRACTICAL)
   - **Current Data**: Ward boundaries exist, but service area definition needed
   - **Implementation**: Define Stone Town wards, apply higher removal efficiency
   - **Zanzibar Context**: Planned infrastructure with known location
   - **Code Changes Needed**: Moderate - extend scenario structure for area-specific overrides
   - **Data Gaps**: Need to define which wards would be served by Kisakasaka WSP

2. **Existing Facility Rehabilitation** (MODERATELY PRACTICAL)
   - **Current Data**: Kibele and Matemwe locations known but service areas undefined
   - **Implementation**: Define service areas, apply improved efficiency
   - **Zanzibar Context**: Existing facilities with known locations
   - **Code Changes Needed**: Moderate - same as above
   - **Data Gaps**: Service area boundaries for existing facilities

3. **Regulation Enforcement Modeling** (MODERATELY PRACTICAL)
   - **Current Data**: Current toilet distribution available
   - **Implementation**: Model as increased effective removal efficiency
   - **Zanzibar Context**: Realistic policy option with local government support
   - **Code Changes Needed**: Minor - can use existing parameters as proxy

### Ambitious Scenarios (Requires Significant Extension)

1. **Sanitation Type Shifts** (AMBITIOUS)
   - **Current Data**: Current toilet distribution available but no transition model
   - **Implementation**: Requires new code to redistribute population across toilet types
   - **Zanzibar Context**: Realistic long-term goal but implementation challenging
   - **Code Changes Needed**: Major - new function to handle sanitation shifts
   - **Data Gaps**: Realistic adoption rates, cost constraints

2. **Decentralized DEWATS Network** (AMBITIOUS)
   - **Current Data**: No existing data on potential DEWATS locations
   - **Implementation**: Requires spatial targeting and new efficiency parameters
   - **Zanzibar Context**: Promising but requires detailed site assessment
   - **Code Changes Needed**: Major - spatial targeting system
   - **Data Gaps**: Potential DEWATS locations, service area boundaries

3. **Combined Multi-Intervention Scenarios** (AMBITIOUS)
   - **Current Data**: Insufficient for interaction effects
   - **Implementation**: Requires complex parameter interactions
   - **Zanzibar Context**: Most realistic for long-term planning
   - **Code Changes Needed**: Major - enhanced scenario engine
   - **Data Gaps**: Intervention interaction effects

### Impractical Scenarios (Data Limitations)

1. **Household-Level Targeting** (IMPRACTICAL)
   - **Current Data**: Only ward-level aggregation available
   - **Implementation**: Would require household-level data
   - **Zanzibar Context**: Too granular for current planning capacity
   - **Data Gaps**: Household-level geolocation data (unlikely to be available)

2. **Groundwater Transport Modeling** (IMPRACTICAL)
   - **Current Data**: No hydrogeological data in current dataset
   - **Implementation**: Would require complex groundwater model integration
   - **Zanzibar Context**: Important but beyond current project scope
   - **Data Gaps**: Hydrogeological surveys, groundwater flow data

3. **Economic Cost-Benefit Analysis** (IMPRACTICAL WITHOUT EXTENSION)
   - **Current Data**: No cost data in current model
   - **Implementation**: Would require new economic module
   - **Zanzibar Context**: Critical for decision-making but separate modeling effort
   - **Data Gaps**: Implementation costs, economic valuation of benefits

### Recommended Practical Implementation Plan

Based on this assessment, here's a practical implementation plan that balances immediate value with realistic development effort:

#### Phase 1: Quick Wins (1-2 weeks)
1. Create a simple ward classification system (Stone Town, urban, rural)
2. Implement basic scenarios using existing parameters:
   - Business-as-usual with population growth
   - Uniform efficiency improvements
   - Stone Town focused improvements

```python
# Example of immediately implementable scenarios
scenarios = {
    'baseline_2022': {
        'pop_factor': 1.0,
        'nre_override': {}
    },
    'baseline_2030': {
        'pop_factor': 1.25,  # 25% population growth
        'nre_override': {}
    },
    'improved_efficiency_2030': {
        'pop_factor': 1.25,
        'nre_override': {'1': 0.50, '2': 0.50, '3': 0.40, '4': 0.40}
    }
}

# Simple ward classification
stone_town_wards = ['Stone Town', 'Mji Mkongwe']  # Add actual ward names
```

#### Phase 2: Core Extensions (2-4 weeks)
1. Extend the scenario structure to support area-specific parameters
2. Implement the Kisakasaka WSP scenario with Stone Town targeting
3. Add service area definitions for Kibele and Matemwe

```python
# Extended scenario structure
def apply_scenario_targeted(pop_df, scenario, ward_classifications):
    """Apply scenario with area targeting."""
    df = pop_df.copy()
    
    # Apply population factor
    df['population'] = df['population'] * scenario.get('pop_factor', 1.0)
    
    # Apply removal efficiencies
    df['nre'] = df['nitrogen_removal_efficiency'].astype(float)
    
    # Global toilet-type overrides
    for ttype, val in scenario.get('nre_override', {}).items():
        mask = df['toilet_type_id'].str.lower() == ttype
        df.loc[mask, 'nre'] = float(val)
    
    # Area-specific overrides (if ward is in stone_town_wards)
    if 'stone_town_override' in scenario:
        for ttype, val in scenario['stone_town_override'].items():
            mask = (df['ward_name'].str.lower().isin([w.lower() for w in stone_town_wards]) & 
                   (df['toilet_type_id'].str.lower() == ttype))
            df.loc[mask, 'nre'] = float(val)
    
    # Calculate load
    df['n_load_kg_y'] = (
        df['population'] * config.P_C * 365 * config.PTN * (1 - df['nre'])
    ) / 1000
    
    return df
```

#### Phase 3: Advanced Features (If Resources Allow)
1. Implement sanitation type shifts for more realistic transition modeling
2. Add DEWATS spatial targeting with rural focus
3. Develop visualization tools for scenario comparison

### Data Collection Priorities

Based on the World Bank report and our analysis, these data collection efforts would be most valuable:

1. **High Priority**:
   - Ward classification table (Stone Town, urban, rural)
   - Service area boundaries for Kisakasaka WSP, Kibele, and Matemwe
   - Baseline field measurements of nitrogen concentrations for model validation
   - Wastewater generation data (current estimate: 12,000 m³/day from Stone Town)

2. **Medium Priority**:
   - Realistic sanitation transition rates based on local adoption patterns
   - Potential DEWATS locations based on geographic suitability
   - Implementation cost estimates for different intervention types
   - Monitoring data for the 25 sea outfalls along Stone Town's 7km shoreline

3. **Lower Priority**:
   - Household-level geolocation data
   - Detailed hydrogeological data (coral rag limestone and karst landscapes)
   - Economic valuation of environmental benefits
   - Watershed delineation for runoff modeling

### Known Data Gaps from World Bank Report

The 2025 World Bank report identified several critical data gaps that affect modeling accuracy:

1. **Monitoring System Gaps**:
   - No regular monitoring of groundwater quality in high-risk areas
   - Limited seawater quality data (bacterial and nutrient levels)
   - No systematic tracking of faecal sludge volumes and disposal locations

2. **Infrastructure Documentation Gaps**:
   - Incomplete mapping of the 32km sewer network in Stone Town
   - Unknown condition assessment for many sections of the network
   - Limited data on actual treatment capacity utilization at Kibele and Kizimbani

3. **Population and Behavior Data**:
   - Limited data on actual population served by different sanitation types
   - No comprehensive survey of sanitation practices in informal settlements
   - Incomplete data on seasonal population variations due to tourism

This practical assessment provides a realistic roadmap for implementing the BEST-Z model in the Zanzibar context, focusing on what can be achieved with existing data while identifying key data gaps for future enhancement.

## Features Status
| Feature | Status |
|---------|--------|
| Streamlit dashboard | Working (baseline & two demo scenarios) |
| Custom CSV/GeoJSON upload | Working |
| Nitrogen load calculator | v1 complete |
| Phosphorus load modelling | Planned (module skeleton present) |
| FIO/pathogen load modelling | Planned |
| Offline static map export (.png) | Beta |
| Dockerised deployment | Stable |
| CI pipeline (GitHub Actions) | Planned |

## Current Progress Highlights (July 2025)
- Refactored n_load.py to a vectorised implementation (~4× speed-up)
- Added population growth slider to dashboard (+/- 10%)
- Integrated ward boundary shapefile v2024 from MoWEM
- Drafted FIO parameter table (log-removal efficiencies) for next phase

## Roadmap
- Unit-test suite, CI/CD, FIO load module, field-data calibration hooks
- Add phosphorus routines; performance profiling; caching with parquet
- Scenario manager upgrade
- Public release & comprehensive documentation