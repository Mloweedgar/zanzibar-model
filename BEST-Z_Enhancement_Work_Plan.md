# BEST-Z Model Enhancement Work Plan
## Implementing Realistic Zanzibar Sanitation Intervention Scenarios

**Date**: January 27, 2025  
**Project**: BEST-Z Nitrogen Model for Zanzibar Sanitation Planning  
**Repository**: `/Users/edgar/zanzibar/zanzibar-model/`  

---

## EXECUTIVE SUMMARY

Based on comprehensive analysis of the current BEST-Z model codebase and the detailed Zanzibar sanitation report, this work plan outlines a structured approach to enhance the nitrogen load model to support evidence-based intervention planning. The current model correctly assumes zero nitrogen removal efficiency as baseline, which aligns with the reality that most sanitation systems in Zanzibar provide no treatment.

**Key Insight**: The model baseline is accurate - we need to focus on modeling realistic intervention scenarios that show the potential improvements from proposed infrastructure and policy changes.

**Current Model Status**:
- ✅ Baseline correctly set at zero removal efficiency
- ✅ Basic scenario framework exists in `config.py`
- ✅ Nitrogen load calculations working in `n_load.py`
- ✅ Streamlit dashboard functional in `interactive_dashboard.py`
- ❌ Missing wastewater volume calculations
- ❌ No spatial targeting (Stone Town vs rural)
- ❌ Limited intervention scenarios
- ❌ Phosphorus load calculations not implemented
- ❌ Pathogen (FIO) load calculations not implemented
- ❌ Agricultural and livestock load sources not integrated
- ❌ Multi-nutrient scenario analysis not available

---

## CURRENT CODEBASE ANALYSIS

### File Structure Overview
```
BEST-Z/
├── scripts/
│   ├── config.py              # Scenarios and constants
│   ├── n_load.py              # Core nitrogen calculations
│   ├── interactive_dashboard.py # Streamlit UI
│   ├── ingest.py              # Data loading
│   └── preprocess.py          # Data cleaning
├── data_raw/
│   ├── Zanzibar_Census_Data2022.csv
│   ├── sanitation_removal_efficiencies_Zanzibar.csv
│   └── unguja_wards.geojson
└── outputs/                   # Generated results
```

### Current Scenario Structure (config.py)
```python
SCENARIOS = {
    'baseline_2022': {
        'pop_factor': 1.0,
        'nre_override': {}
    },
    'improved_removal': {
        'pop_factor': 1.0,
        'nre_override': {'1': 0.80, '2': 0.80, '3': 0.80, '4': 0.80}
    },
    'pop_growth_2030': {
        'pop_factor': 1.2,
        'nre_override': {}
    }
}
```

### Current Nitrogen Load Function (n_load.py)
```python
def apply_scenario(pop_df: pd.DataFrame, scenario: dict) -> pd.DataFrame:
    """Return DataFrame with nitrogen load columns for a scenario."""
    df = pop_df.copy()
    df['population'] = df['population'] * scenario['pop_factor']
    df['nre'] = df['nitrogen_removal_efficiency'].astype(float)
    for ttype, val in scenario['nre_override'].items():
        mask = df['toilet_type_id'].str.lower() == ttype
        df.loc[mask, 'nre'] = float(val)
    df['n_load_kg_y'] = (
        df['population'] * config.P_C * 365 * config.PTN * (1 - df['nre'])
    ) / 1000
    return df
```

### Census Data Structure
```
Columns: reg_name, H_DISTRICT_NAME, H_COUNCIL_NAME, H_CONSTITUENCY_NAME, 
         H_DIVISION_NAME, ward_name, TOILET, SEX, AGE, ...
Toilet Types: 1-11 (mapped to removal efficiencies)
Geographic Levels: Region > District > Council > Constituency > Division > Ward
```

### Sanitation Efficiency Data
```
toilet_type_id: 1-11
nitrogen_removal_efficiency: Currently 0 for all types (realistic baseline)
phosphorus_removal_efficiency: Available (0.0-0.15 range)
pathogen_removal_efficiency_log10: Available (0.0-1.5 log reduction range)
system_category: septic_tank_sewer, septic_tank, pit_latrine, open_defecation
```

### Multi-Nutrient Model Framework
The BEST-Z model is designed to calculate loads for multiple pollutants:

**Household Sources:**
- **Nitrogen (N)**: From human excreta - `Pop * P_c * 365 * PtN * (1 - NRE)`
- **Phosphorus (P)**: From detergents and excreta - `Pop * D_c * 365 * P_d * (1 - PRE)`
- **Pathogens (FIO)**: From human excreta - `Pop * EFIO * (1 - PRE_pathogen)`

**Additional Sources (Future Integration):**
- **Agricultural**: Fertilizer runoff - `F_N/P * A * L_N/P`
- **Livestock**: Animal excreta - `N_animals * EF_N/P`

---

## PHASE 1: IMMEDIATE QUICK WINS (Start Today)
*Using existing code structure with minimal modifications*

### 1.1 Population Growth Scenarios ⭐ **HIGHEST PRIORITY**

**Objective**: Model 2030 and 2050 projections to show increasing nitrogen loads without intervention

**Current Code Status**: ✅ Fully supported by existing `config.py` SCENARIOS structure

**Files to Modify**: 
- `BEST-Z/scripts/config.py` (add scenarios)

**Implementation**:
```python
# Add to SCENARIOS dictionary in config.py
'bau_2030': {
    'pop_factor': 1.25,  # 25% growth by 2030 (3.7% annual * 8 years)
    'nre_override': {}   # No treatment improvements
},
'bau_2050': {
    'pop_factor': 2.48,  # Stone Town: 27,350→67,830 m³/day growth from report
    'nre_override': {}   # No treatment improvements
}
```

**Validation**: 
- Compare population projections with report data
- Verify growth rates align with 3.7% annual increase

**Value**: Shows the urgency of intervention - nitrogen loads will increase dramatically with population growth alone.

**Testing**:
```python
# Test in dashboard
scenario = config.SCENARIOS['bau_2030']
result_df = n_load.apply_scenario(pop_df, scenario)
print(f"Total N load 2030: {result_df['n_load_kg_y'].sum():.0f} kg/year")
```

### 1.2 Improved FSM Enforcement Scenario ⭐ **HIGH PRIORITY**

**Objective**: Model impact of better sludge collection and treatment at existing facilities

**Current Code Status**: ✅ Fully supported

**Files to Modify**: 
- `BEST-Z/scripts/config.py` (add scenario)

**Implementation**:
```python
'improved_fsm_2030': {
    'pop_factor': 1.25,  # Include population growth
    'nre_override': {
        '1': 0.0,   # Sewer still untreated (25 outfalls, no treatment plants)
        '2': 0.45,  # Septic: proper emptying to Kibele treatment (vs current 20%)
        '3': 0.25,  # Pit latrines: regulated emptying and treatment
        '4': 0.20,  # Other systems: some improvement
        '5': 0.15,  # VIP latrines: slight improvement
        '6': 0.15,  # Pit with slab: slight improvement
        '7': 0.10,  # Pit without lid: minimal improvement
        '8': 0.05,  # Poor pit: minimal improvement
        '9': 0.05,  # Open pit: minimal improvement
        '10': 0.0,  # Bucket: no improvement
        '11': 0.0   # Open defecation: no improvement
    }
}
```

**Rationale**: 
- Report shows only 20% of sludge reaches treatment currently
- Kibele has some treatment capacity (though at 300% capacity: 12 m³/day vs 4 m³/day design)
- This scenario models better enforcement and collection

**Expert Input Needed**:
- Sanitation Expert: What's realistic removal efficiency for improved FSM?
- Sanitation Expert: What percentage of sludge could realistically reach treatment?

### 1.3 Technology Upgrade Scenario

**Objective**: Model uniform technology upgrades across all sanitation types

**Current Code Status**: ✅ Fully supported (similar to existing 'improved_removal' scenario)

**Files to Modify**: 
- `BEST-Z/scripts/config.py` (add scenario)

**Implementation**:
```python
'technology_upgrade_2030': {
    'pop_factor': 1.25,
    'nre_override': {
        '1': 0.60,  # Sewer with basic treatment (primary + secondary)
        '2': 0.50,  # Improved septic systems with proper design
        '3': 0.30,  # Improved pit latrines with better containment
        '4': 0.25,  # Other improved systems
        '5': 0.20,  # Improved VIP latrines
        '6': 0.20,  # Improved pit with slab
        '7': 0.15,  # Improved pit without lid
        '8': 0.10,  # Improved poor pit
        '9': 0.05,  # Improved open pit
        '10': 0.30, # Bucket with proper disposal
        '11': 0.0   # Open defecation: no improvement possible
    }
}
```

**Testing Strategy**:
```python
# Compare scenarios
baseline = n_load.apply_scenario(pop_df, config.SCENARIOS['baseline_2022'])
improved_fsm = n_load.apply_scenario(pop_df, config.SCENARIOS['improved_fsm_2030'])
tech_upgrade = n_load.apply_scenario(pop_df, config.SCENARIOS['technology_upgrade_2030'])

print(f"Baseline N load: {baseline['n_load_kg_y'].sum():.0f} kg/year")
print(f"Improved FSM N load: {improved_fsm['n_load_kg_y'].sum():.0f} kg/year")
print(f"Tech upgrade N load: {tech_upgrade['n_load_kg_y'].sum():.0f} kg/year")
```

---

## PHASE 2: MULTI-NUTRIENT CALCULATIONS (Week 2)
*Extend model to calculate phosphorus and pathogen loads alongside nitrogen*

### 2.1 Phosphorus Load Calculations 💡 **HIGH VALUE**

**Objective**: Add phosphorus load calculations using existing efficiency data

**Current Code Status**: ❌ Needs new functions in `n_load.py`, but efficiency data exists

**Files to Modify**: 
- `BEST-Z/scripts/config.py` (add phosphorus parameters)
- `BEST-Z/scripts/n_load.py` (add phosphorus functions)

**Implementation**:

**Step 1: Add phosphorus constants to config.py**
```python
# Add to config.py
# Phosphorus parameters
D_C = 25  # Daily detergent consumption per capita (g/day) - NEEDS EXPERT INPUT
P_D = 0.12  # Phosphorus content in detergents (typical 10-15%) - NEEDS EXPERT INPUT
P_EXCRETA = 1.5  # Phosphorus from human excreta (g/person/day) - literature value
```

**Step 2: Add phosphorus calculation function to n_load.py**
```python
def calc_phosphorus_load(pop_df, scenario=None):
    """
    Calculate phosphorus loads from household sources.
    
    Args:
        pop_df: Population dataframe
        scenario: Scenario dictionary (optional)
    
    Returns:
        DataFrame with phosphorus load columns
    """
    df = pop_df.copy()
    
    # Apply scenario if provided
    if scenario:
        df['population'] = df['population'] * scenario.get('pop_factor', 1.0)
    
    # Get phosphorus removal efficiency
    df['pre'] = df['phosphorus_removal_efficiency'].astype(float)
    
    # Apply scenario overrides for phosphorus
    if scenario and 'pre_override' in scenario:
        for ttype, val in scenario['pre_override'].items():
            mask = df['toilet_type_id'].str.lower() == ttype
            df.loc[mask, 'pre'] = float(val)
    
    # Calculate phosphorus loads
    # P from detergents
    df['p_load_detergent_kg_y'] = (
        df['population'] * config.D_C * 365 * config.P_D * (1 - df['pre'])
    ) / 1000
    
    # P from human excreta
    df['p_load_excreta_kg_y'] = (
        df['population'] * config.P_EXCRETA * 365 * (1 - df['pre'])
    ) / 1000
    
    # Total phosphorus load
    df['p_load_total_kg_y'] = df['p_load_detergent_kg_y'] + df['p_load_excreta_kg_y']
    
    logging.info('Calculated phosphorus load for %s rows', len(df))
    return df
```

**Step 3: Add area-specific phosphorus scenarios**
```python
def apply_phosphorus_scenario_with_areas(pop_df: pd.DataFrame, scenario: dict) -> pd.DataFrame:
    """Apply scenario with area targeting for phosphorus calculations."""
    df = pop_df.copy()
    
    # Apply population factor
    df['population'] = df['population'] * scenario.get('pop_factor', 1.0)
    
    # Initialize phosphorus removal efficiencies
    df['pre'] = df['phosphorus_removal_efficiency'].astype(float)
    
    # Apply global overrides
    for ttype, val in scenario.get('pre_override', {}).items():
        mask = df['toilet_type_id'].str.lower() == ttype
        df.loc[mask, 'pre'] = float(val)
    
    # Apply Stone Town specific overrides
    if 'stone_town_pre_override' in scenario:
        stone_town_mask = df['ward_name'].isin(config.WARD_CLASSIFICATIONS['stone_town_wards'])
        for ttype, val in scenario['stone_town_pre_override'].items():
            mask = stone_town_mask & (df['toilet_type_id'].str.lower() == ttype)
            df.loc[mask, 'pre'] = float(val)
    
    # Calculate phosphorus loads (same as above)
    df['p_load_detergent_kg_y'] = (
        df['population'] * config.D_C * 365 * config.P_D * (1 - df['pre'])
    ) / 1000
    
    df['p_load_excreta_kg_y'] = (
        df['population'] * config.P_EXCRETA * 365 * (1 - df['pre'])
    ) / 1000
    
    df['p_load_total_kg_y'] = df['p_load_detergent_kg_y'] + df['p_load_excreta_kg_y']
    
    return df
```

**Expert Input Required**:
- **Sanitation Expert**: Realistic detergent consumption rates in Zanzibar
- **Sanitation Expert**: Phosphorus content in locally used detergents
- **Marine Biology Expert**: Critical phosphorus thresholds for marine ecosystems

### 2.2 Pathogen (FIO) Load Calculations 💡 **HIGH VALUE**

**Objective**: Add pathogen load calculations using log reduction efficiencies

**Current Code Status**: ❌ Needs new functions, but efficiency data exists

**Files to Modify**: 
- `BEST-Z/scripts/config.py` (add pathogen parameters)
- `BEST-Z/scripts/n_load.py` (add pathogen functions)

**Implementation**:

**Step 1: Add pathogen constants to config.py**
```python
# Add to config.py
# Pathogen parameters
EFIO = 1e11  # Fecal indicator organisms per person per day (CFU/person/day) - NEEDS EXPERT INPUT
# Note: This is a typical value, but needs validation for Zanzibar context
```

**Step 2: Add pathogen calculation function to n_load.py**
```python
def calc_pathogen_load(pop_df, scenario=None):
    """
    Calculate pathogen (FIO) loads from household sources.
    
    Args:
        pop_df: Population dataframe
        scenario: Scenario dictionary (optional)
    
    Returns:
        DataFrame with pathogen load columns
    """
    df = pop_df.copy()
    
    # Apply scenario if provided
    if scenario:
        df['population'] = df['population'] * scenario.get('pop_factor', 1.0)
    
    # Get pathogen removal efficiency (log reduction)
    df['pathogen_log_reduction'] = df['pathogen_removal_efficiency_log10'].astype(float)
    
    # Apply scenario overrides for pathogens
    if scenario and 'pathogen_override' in scenario:
        for ttype, val in scenario['pathogen_override'].items():
            mask = df['toilet_type_id'].str.lower() == ttype
            df.loc[mask, 'pathogen_log_reduction'] = float(val)
    
    # Calculate pathogen removal efficiency from log reduction
    # Log reduction of X means 10^(-X) fraction remains
    df['pathogen_removal_efficiency'] = 1 - (10 ** (-df['pathogen_log_reduction']))
    
    # Calculate pathogen loads
    df['fio_load_cfu_day'] = (
        df['population'] * config.EFIO * (1 - df['pathogen_removal_efficiency'])
    )
    
    df['fio_load_cfu_year'] = df['fio_load_cfu_day'] * 365
    
    # Convert to log scale for easier interpretation
    df['fio_load_log_cfu_day'] = np.log10(df['fio_load_cfu_day'] + 1)  # +1 to avoid log(0)
    
    logging.info('Calculated pathogen load for %s rows', len(df))
    return df
```

**Step 3: Add area-specific pathogen scenarios**
```python
def apply_pathogen_scenario_with_areas(pop_df: pd.DataFrame, scenario: dict) -> pd.DataFrame:
    """Apply scenario with area targeting for pathogen calculations."""
    df = pop_df.copy()
    
    # Apply population factor
    df['population'] = df['population'] * scenario.get('pop_factor', 1.0)
    
    # Initialize pathogen removal efficiencies
    df['pathogen_log_reduction'] = df['pathogen_removal_efficiency_log10'].astype(float)
    
    # Apply global overrides
    for ttype, val in scenario.get('pathogen_override', {}).items():
        mask = df['toilet_type_id'].str.lower() == ttype
        df.loc[mask, 'pathogen_log_reduction'] = float(val)
    
    # Apply Stone Town specific overrides
    if 'stone_town_pathogen_override' in scenario:
        stone_town_mask = df['ward_name'].isin(config.WARD_CLASSIFICATIONS['stone_town_wards'])
        for ttype, val in scenario['stone_town_pathogen_override'].items():
            mask = stone_town_mask & (df['toilet_type_id'].str.lower() == ttype)
            df.loc[mask, 'pathogen_log_reduction'] = float(val)
    
    # Calculate pathogen removal efficiency and loads
    df['pathogen_removal_efficiency'] = 1 - (10 ** (-df['pathogen_log_reduction']))
    
    df['fio_load_cfu_day'] = (
        df['population'] * config.EFIO * (1 - df['pathogen_removal_efficiency'])
    )
    
    df['fio_load_cfu_year'] = df['fio_load_cfu_day'] * 365
    df['fio_load_log_cfu_day'] = np.log10(df['fio_load_cfu_day'] + 1)
    
    return df
```

**Expert Input Required**:
- **Marine Biology Expert**: Typical FIO excretion rates for Zanzibar population
- **Marine Biology Expert**: Critical FIO levels for marine ecosystem health
- **Sanitation Expert**: Realistic pathogen removal for different treatment technologies

### 2.3 Integrated Multi-Nutrient Function 💡 **HIGHEST VALUE**

**Objective**: Create unified function calculating all pollutants simultaneously

**Implementation**:
```python
def calc_multi_nutrient_loads(pop_df, scenario=None):
    """
    Calculate nitrogen, phosphorus, and pathogen loads simultaneously.
    
    Args:
        pop_df: Population dataframe
        scenario: Enhanced scenario dictionary with all pollutant parameters
    
    Returns:
        DataFrame with all pollutant loads and wastewater volumes
    """
    df = pop_df.copy()
    
    # Apply scenario if provided
    if scenario:
        df['population'] = df['population'] * scenario.get('pop_factor', 1.0)
    
    # Initialize removal efficiencies
    df['nre'] = df['nitrogen_removal_efficiency'].astype(float)
    df['pre'] = df['phosphorus_removal_efficiency'].astype(float)
    df['pathogen_log_reduction'] = df['pathogen_removal_efficiency_log10'].astype(float)
    
    # Apply scenario overrides
    if scenario:
        # Nitrogen overrides
        for ttype, val in scenario.get('nre_override', {}).items():
            mask = df['toilet_type_id'].str.lower() == ttype
            df.loc[mask, 'nre'] = float(val)
        
        # Phosphorus overrides
        for ttype, val in scenario.get('pre_override', {}).items():
            mask = df['toilet_type_id'].str.lower() == ttype
            df.loc[mask, 'pre'] = float(val)
        
        # Pathogen overrides
        for ttype, val in scenario.get('pathogen_override', {}).items():
            mask = df['toilet_type_id'].str.lower() == ttype
            df.loc[mask, 'pathogen_log_reduction'] = float(val)
    
    # Calculate nitrogen loads (existing logic)
    df['n_load_kg_y'] = (
        df['population'] * config.P_C * 365 * config.PTN * (1 - df['nre'])
    ) / 1000
    
    # Calculate phosphorus loads
    df['p_load_detergent_kg_y'] = (
        df['population'] * config.D_C * 365 * config.P_D * (1 - df['pre'])
    ) / 1000
    
    df['p_load_excreta_kg_y'] = (
        df['population'] * config.P_EXCRETA * 365 * (1 - df['pre'])
    ) / 1000
    
    df['p_load_total_kg_y'] = df['p_load_detergent_kg_y'] + df['p_load_excreta_kg_y']
    
    # Calculate pathogen loads
    df['pathogen_removal_efficiency'] = 1 - (10 ** (-df['pathogen_log_reduction']))
    df['fio_load_cfu_day'] = (
        df['population'] * config.EFIO * (1 - df['pathogen_removal_efficiency'])
    )
    df['fio_load_cfu_year'] = df['fio_load_cfu_day'] * 365
    df['fio_load_log_cfu_day'] = np.log10(df['fio_load_cfu_day'] + 1)
    
    # Add wastewater volumes (from previous phase)
    df = calc_wastewater_volume(df)
    
    logging.info('Calculated multi-nutrient loads for %s rows', len(df))
    return df
```

### 2.4 Enhanced Scenario Definitions with Multi-Nutrients

**Implementation**:
```python
# Enhanced scenarios in config.py with all pollutants
MULTI_NUTRIENT_SCENARIOS = {
    'kisakasaka_wsp_multi_2030': {
        'pop_factor': 1.25,
        'stone_town_override': {
            # Nitrogen removal
            'nre_override': {'1': 0.85, '2': 0.85},
            # Phosphorus removal (WSP typically achieves 80-90% P removal)
            'pre_override': {'1': 0.80, '2': 0.80},
            # Pathogen removal (WSP achieves 3-4 log reduction)
            'pathogen_override': {'1': 3.5, '2': 3.5}
        },
        'other_areas_override': {
            'nre_override': {'2': 0.0, '3': 0.0},
            'pre_override': {'2': 0.0, '3': 0.0},
            'pathogen_override': {'2': 0.0, '3': 0.0}
        }
    },
    
    'improved_fsm_multi_2030': {
        'pop_factor': 1.25,
        'nre_override': {'2': 0.45, '3': 0.25},
        'pre_override': {'2': 0.40, '3': 0.20},  # Slightly lower P removal than N
        'pathogen_override': {'2': 2.0, '3': 1.5}  # Moderate pathogen reduction
    }
}
```

---

## PHASE 3: VOLUME & SPATIAL TARGETING (Week 3)
*Requires moderate code modifications but high value*

### 3.1 Wastewater Volume Calculations 💡 **HIGHEST VALUE**

**Objective**: Add volume metrics alongside multi-nutrient loads for intervention sizing

**Current Code Status**: ❌ Needs new function in `n_load.py`

**Files to Modify**: 
- `BEST-Z/scripts/n_load.py` (add volume functions)
- `BEST-Z/scripts/config.py` (add water consumption parameter)

**Implementation**:

**Step 1: Add constants to config.py**
```python
# Add to config.py
WATER_CONSUMPTION_LPCD = 150  # Liters per capita per day
WASTEWATER_FACTOR = 0.8       # Wastewater = 80% of water consumption
```

**Step 2: Add volume function to n_load.py**
```python
def calc_wastewater_volume(pop_df, water_consumption_lpcd=None):
    """
    Calculate wastewater generation volumes alongside nitrogen loads.
    
    Args:
        pop_df: Population dataframe with 'population' column
        water_consumption_lpcd: Liters per capita per day (default from config)
    
    Returns:
        DataFrame with additional volume columns
    """
    if water_consumption_lpcd is None:
        water_consumption_lpcd = config.WATER_CONSUMPTION_LPCD
    
    df = pop_df.copy()
    
    # Wastewater generation
    df['wastewater_L_day'] = df['population'] * water_consumption_lpcd * config.WASTEWATER_FACTOR
    df['wastewater_m3_day'] = df['wastewater_L_day'] / 1000  # Convert L to m³
    df['wastewater_m3_year'] = df['wastewater_m3_day'] * 365
    
    # Treatment capacity needed (total wastewater requiring treatment)
    df['treatment_capacity_needed_m3_day'] = df['wastewater_m3_day']
    
    return df

def calc_multi_nutrient_with_volume(pop_df, scenario=None):
    """
    Enhanced version calculating all pollutant loads and volumes.
    
    Args:
        pop_df: Population dataframe
        scenario: Enhanced scenario dictionary with all pollutant parameters
    
    Returns:
        DataFrame with all pollutant loads and wastewater volumes
    """
    # Use the integrated multi-nutrient function (from Phase 2)
    df = calc_multi_nutrient_loads(pop_df, scenario)
    
    # Volume calculations are already included in calc_multi_nutrient_loads
    # Add additional pollutant-specific volume metrics
    df['treated_n_kg_y'] = df['n_load_kg_y'] * df['nre']
    df['untreated_n_kg_y'] = df['n_load_kg_y'] * (1 - df['nre'])
    
    df['treated_p_kg_y'] = df['p_load_total_kg_y'] * df['pre']
    df['untreated_p_kg_y'] = df['p_load_total_kg_y'] * (1 - df['pre'])
    
    df['treated_fio_cfu_y'] = df['fio_load_cfu_year'] * df['pathogen_removal_efficiency']
    df['untreated_fio_cfu_y'] = df['fio_load_cfu_year'] * (1 - df['pathogen_removal_efficiency'])
    
    # Volume-based treatment efficiency metrics
    df['treated_volume_m3_day'] = df['wastewater_m3_day'] * df['nre']  # Assuming N removal as proxy
    df['untreated_volume_m3_day'] = df['wastewater_m3_day'] * (1 - df['nre'])
    
    return df
```

**Step 3: Update aggregate_ward function**
```python
def aggregate_ward_multi_nutrient(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate all pollutant loads and volumes to ward level."""
    group_cols = [
        'reg_name', 'H_DISTRICT_NAME', 'H_COUNCIL_NAME',
        'H_CONSTITUENCY_NAME', 'H_DIVISION_NAME', 'ward_name'
    ]
    
    agg_dict = {
        # Nitrogen loads
        'n_load_kg_y': 'sum',
        'treated_n_kg_y': 'sum',
        'untreated_n_kg_y': 'sum',
        
        # Phosphorus loads
        'p_load_total_kg_y': 'sum',
        'p_load_detergent_kg_y': 'sum',
        'p_load_excreta_kg_y': 'sum',
        'treated_p_kg_y': 'sum',
        'untreated_p_kg_y': 'sum',
        
        # Pathogen loads
        'fio_load_cfu_year': 'sum',
        'treated_fio_cfu_y': 'sum',
        'untreated_fio_cfu_y': 'sum',
        
        # Volume metrics
        'wastewater_m3_day': 'sum',
        'wastewater_m3_year': 'sum',
        'treatment_capacity_needed_m3_day': 'sum',
        'treated_volume_m3_day': 'sum',
        'untreated_volume_m3_day': 'sum',
        
        # Population
        'population': 'sum'
    }
    
    ward = df.groupby(group_cols).agg(agg_dict).reset_index()
    
    # Rename columns with ward prefix
    rename_dict = {
        'n_load_kg_y': 'ward_n_load_kg_y',
        'treated_n_kg_y': 'ward_treated_n_kg_y',
        'untreated_n_kg_y': 'ward_untreated_n_kg_y',
        'p_load_total_kg_y': 'ward_p_load_kg_y',
        'p_load_detergent_kg_y': 'ward_p_detergent_kg_y',
        'p_load_excreta_kg_y': 'ward_p_excreta_kg_y',
        'treated_p_kg_y': 'ward_treated_p_kg_y',
        'untreated_p_kg_y': 'ward_untreated_p_kg_y',
        'fio_load_cfu_year': 'ward_fio_load_cfu_y',
        'treated_fio_cfu_y': 'ward_treated_fio_cfu_y',
        'untreated_fio_cfu_y': 'ward_untreated_fio_cfu_y',
        'wastewater_m3_day': 'ward_wastewater_m3_day',
        'wastewater_m3_year': 'ward_wastewater_m3_year',
        'treatment_capacity_needed_m3_day': 'ward_treatment_capacity_m3_day',
        'treated_volume_m3_day': 'ward_treated_volume_m3_day',
        'untreated_volume_m3_day': 'ward_untreated_volume_m3_day',
        'population': 'ward_population'
    }
    
    ward = ward.rename(columns=rename_dict)
    
    # Calculate ward-level efficiency metrics
    ward['ward_n_removal_efficiency'] = ward['ward_treated_n_kg_y'] / (ward['ward_n_load_kg_y'] + ward['ward_treated_n_kg_y'])
    ward['ward_p_removal_efficiency'] = ward['ward_treated_p_kg_y'] / (ward['ward_p_load_kg_y'] + ward['ward_treated_p_kg_y'])
    
    return ward
```

**Validation Against Report Data**:
```python
# Test volume calculations against report figures
# Report: Stone Town generates 12,000 m³/day untreated sewage
# Report: Total Stone Town wastewater: 27,350 m³/day (2025)

def validate_volume_calculations():
    # Load data
    pop_df = ingest.load_census_data()
    
    # Calculate volumes for Stone Town wards
    stone_town_wards = ['Shangani', 'Malindi', 'Mji Mkongwe']  # Need complete list
    stone_town_data = pop_df[pop_df['ward_name'].isin(stone_town_wards)]
    
    volumes = calc_wastewater_volume(stone_town_data)
    total_volume = volumes['wastewater_m3_day'].sum()
    
    print(f"Calculated Stone Town volume: {total_volume:.0f} m³/day")
    print(f"Report Stone Town volume: 27,350 m³/day")
    print(f"Difference: {abs(total_volume - 27350):.0f} m³/day")
    
    return total_volume
```

**Value**: 
- Enables comparison with report figures (12,000 m³/day Stone Town, 27,350 m³/day total)
- Shows treatment capacity requirements for each scenario
- Critical for infrastructure sizing and cost estimation

### 2.2 Stone Town vs Other Areas Targeting 💡 **HIGH VALUE**

**Objective**: Enable area-specific interventions (Stone Town WSP, rural DEWATS)

**Current Code Status**: ❌ Needs extension to `apply_scenario()` function

**Files to Modify**: 
- `BEST-Z/scripts/config.py` (add ward classifications)
- `BEST-Z/scripts/n_load.py` (extend apply_scenario function)

**Implementation**:

**Step 1: Add ward classifications to config.py**
```python
# Add to config.py - NEEDS GIS EXPERT INPUT
WARD_CLASSIFICATIONS = {
    'stone_town_wards': [
        'Shangani', 'Malindi', 'Mji Mkongwe'  # Need complete list from GIS expert
        # Add all Stone Town wards based on census data analysis
    ],
    'urban_wards': [
        # West A, West B urban areas - need GIS expert input
    ],
    'rural_wards': [
        # Rural areas suitable for DEWATS - need GIS expert input
    ],
    'tourism_zones': [
        # Coastal wards with high tourism impact - need marine biology expert input
    ]
}

# Function to get ward classification
def get_ward_classification(ward_name, classification_type):
    """Get ward classification for targeting interventions."""
    return ward_name in WARD_CLASSIFICATIONS.get(classification_type, [])
```

**Step 2: Extend apply_scenario function in n_load.py**
```python
def apply_scenario_with_areas(pop_df: pd.DataFrame, scenario: dict) -> pd.DataFrame:
    """
    Enhanced scenario application with area targeting.
    
    Args:
        pop_df: Population dataframe
        scenario: Enhanced scenario dictionary with area-specific overrides
    
    Returns:
        DataFrame with nitrogen loads calculated using area-specific parameters
    """
    df = pop_df.copy()
    
    # Apply population factor
    df['population'] = df['population'] * scenario.get('pop_factor', 1.0)
    
    # Initialize removal efficiencies
    df['nre'] = df['nitrogen_removal_efficiency'].astype(float)
    
    # Apply global overrides (existing logic)
    for ttype, val in scenario.get('nre_override', {}).items():
        mask = df['toilet_type_id'].str.lower() == ttype
        df.loc[mask, 'nre'] = float(val)
    
    # Apply Stone Town specific overrides
    if 'stone_town_override' in scenario:
        stone_town_mask = df['ward_name'].isin(config.WARD_CLASSIFICATIONS['stone_town_wards'])
        for ttype, val in scenario['stone_town_override'].items():
            mask = stone_town_mask & (df['toilet_type_id'].str.lower() == ttype)
            df.loc[mask, 'nre'] = float(val)
            logging.info(f'Applied Stone Town override: toilet type {ttype} = {val} for {mask.sum()} records')
    
    # Apply other areas overrides
    if 'other_areas_override' in scenario:
        other_areas_mask = ~df['ward_name'].isin(config.WARD_CLASSIFICATIONS['stone_town_wards'])
        for ttype, val in scenario['other_areas_override'].items():
            mask = other_areas_mask & (df['toilet_type_id'].str.lower() == ttype)
            df.loc[mask, 'nre'] = float(val)
            logging.info(f'Applied other areas override: toilet type {ttype} = {val} for {mask.sum()} records')
    
    # Apply urban areas overrides
    if 'urban_override' in scenario:
        urban_mask = df['ward_name'].isin(config.WARD_CLASSIFICATIONS['urban_wards'])
        for ttype, val in scenario['urban_override'].items():
            mask = urban_mask & (df['toilet_type_id'].str.lower() == ttype)
            df.loc[mask, 'nre'] = float(val)
    
    # Apply rural areas overrides
    if 'rural_override' in scenario:
        rural_mask = df['ward_name'].isin(config.WARD_CLASSIFICATIONS['rural_wards'])
        for ttype, val in scenario['rural_override'].items():
            mask = rural_mask & (df['toilet_type_id'].str.lower() == ttype)
            df.loc[mask, 'nre'] = float(val)
    
    # Calculate nitrogen loads (existing logic)
    df['n_load_kg_y'] = (
        df['population'] * config.P_C * 365 * config.PTN * (1 - df['nre'])
    ) / 1000
    
    logging.info('Calculated nitrogen load with area targeting for %s rows', len(df))
    return df
```

**Step 3: Add area analysis function**
```python
def analyze_by_area(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze results by geographic area."""
    df = df.copy()
    
    # Add area classifications
    df['is_stone_town'] = df['ward_name'].isin(config.WARD_CLASSIFICATIONS['stone_town_wards'])
    df['is_urban'] = df['ward_name'].isin(config.WARD_CLASSIFICATIONS['urban_wards'])
    df['is_rural'] = df['ward_name'].isin(config.WARD_CLASSIFICATIONS['rural_wards'])
    
    # Create area summary
    area_summary = []
    
    for area_type in ['stone_town', 'urban', 'rural']:
        mask = df[f'is_{area_type}']
        if mask.any():
            summary = {
                'area_type': area_type,
                'population': df.loc[mask, 'population'].sum(),
                'n_load_kg_y': df.loc[mask, 'n_load_kg_y'].sum(),
                'wastewater_m3_day': df.loc[mask, 'wastewater_m3_day'].sum() if 'wastewater_m3_day' in df.columns else 0,
                'ward_count': mask.sum()
            }
            area_summary.append(summary)
    
    return pd.DataFrame(area_summary)
```

**Expert Input Required**:
- **GIS Expert**: Complete list of Stone Town wards
- **GIS Expert**: Urban vs rural ward classification
- **Sanitation Expert**: Which areas would be served by different interventions

### 2.3 Kisakasaka WSP Scenario Implementation 💡 **HIGH VALUE**

**Objective**: Model the proposed 22.5-hectare WSP serving Stone Town

**Dependencies**: Requires 2.2 (area targeting)

**Files to Modify**: 
- `BEST-Z/scripts/config.py` (add WSP scenario)

**Implementation**:
```python
# Add to SCENARIOS in config.py
'kisakasaka_wsp_2030': {
    'pop_factor': 1.25,  # Population growth to 2030
    'stone_town_override': {
        '1': 0.85,  # Sewer connected to WSP: 85% N removal
        '2': 0.85   # Septic systems connected to WSP: 85% N removal
    },
    'other_areas_override': {
        '2': 0.0,   # Septic tanks outside Stone Town: no change
        '3': 0.0,   # Pit latrines: no change
        '4': 0.0,   # Other systems: no change
        '5': 0.0,   # VIP latrines: no change
        '6': 0.0,   # Pit with slab: no change
        '7': 0.0,   # Pit without lid: no change
        '8': 0.0,   # Poor pit: no change
        '9': 0.0,   # Open pit: no change
        '10': 0.0,  # Bucket: no change
        '11': 0.0   # Open defecation: no change
    }
}
```

**WSP Impact Analysis Function**:
```python
def analyze_wsp_impact(pop_df):
    """Analyze the impact of Kisakasaka WSP implementation."""
    
    # Calculate baseline (no intervention)
    baseline = calc_n_load_with_volume(pop_df, config.SCENARIOS['bau_2030'])
    
    # Calculate WSP scenario
    wsp_scenario = calc_n_load_with_volume(pop_df, config.SCENARIOS['kisakasaka_wsp_2030'])
    
    # Stone Town analysis
    stone_town_mask = baseline['ward_name'].isin(config.WARD_CLASSIFICATIONS['stone_town_wards'])
    
    baseline_stone_town = baseline[stone_town_mask]
    wsp_stone_town = wsp_scenario[stone_town_mask]
    
    results = {
        'stone_town_baseline_n_load': baseline_stone_town['n_load_kg_y'].sum(),
        'stone_town_wsp_n_load': wsp_stone_town['n_load_kg_y'].sum(),
        'stone_town_n_reduction': baseline_stone_town['n_load_kg_y'].sum() - wsp_stone_town['n_load_kg_y'].sum(),
        'stone_town_n_reduction_pct': (1 - wsp_stone_town['n_load_kg_y'].sum() / baseline_stone_town['n_load_kg_y'].sum()) * 100,
        'stone_town_wastewater_volume': baseline_stone_town['wastewater_m3_day'].sum(),
        'stone_town_treatment_capacity_needed': wsp_stone_town['treatment_capacity_needed_m3_day'].sum(),
        'total_baseline_n_load': baseline['n_load_kg_y'].sum(),
        'total_wsp_n_load': wsp_scenario['n_load_kg_y'].sum(),
        'total_n_reduction': baseline['n_load_kg_y'].sum() - wsp_scenario['n_load_kg_y'].sum(),
        'total_n_reduction_pct': (1 - wsp_scenario['n_load_kg_y'].sum() / baseline['n_load_kg_y'].sum()) * 100
    }
    
    return results
```

**Expert Input Required**:
- **Sanitation Expert**: Is 85% nitrogen removal realistic for WSP in Zanzibar conditions?
- **Sanitation Expert**: What's the actual service area for Kisakasaka WSP?
- **GIS Expert**: Which specific wards would be connected to the WSP?

**Value**: Shows the dramatic impact of centralized treatment for Stone Town's high-volume wastewater generation.

---

## PHASE 3: DASHBOARD ENHANCEMENTS (Week 3-4)
*Improve user interface and visualization*

### 3.1 Volume Metrics in Dashboard

**Objective**: Display wastewater volumes alongside nitrogen loads

**Current Code Status**: ❌ Needs modification to `interactive_dashboard.py`

**Files to Modify**: 
- `BEST-Z/scripts/interactive_dashboard.py`

**Implementation**:

**Step 1: Update data processing in dashboard**
```python
# In interactive_dashboard.py, modify the scenario processing section

def process_scenario_with_volumes(pop_df, scenario_name):
    """Process scenario with both nitrogen loads and volumes."""
    scenario = config.SCENARIOS[scenario_name]
    
    # Use enhanced function if area targeting is available
    if any(key in scenario for key in ['stone_town_override', 'other_areas_override']):
        result_df = n_load.apply_scenario_with_areas(pop_df, scenario)
    else:
        result_df = n_load.apply_scenario(pop_df, scenario)
    
    # Add volume calculations
    result_df = n_load.calc_wastewater_volume(result_df)
    
    # Aggregate to ward level
    ward_df = n_load.aggregate_ward_with_volume(result_df)
    
    return result_df, ward_df
```

**Step 2: Add volume metrics to sidebar**
```python
# Add to sidebar metrics display
st.sidebar.subheader("📊 Scenario Results")

if 'ward_df' in st.session_state:
    ward_df = st.session_state.ward_df
    
    # Nitrogen metrics
    total_n_load = ward_df['ward_total_n_load_kg'].sum()
    st.sidebar.metric("Total N Load", f"{total_n_load:,.0f} kg/year")
    
    # Volume metrics
    total_wastewater = ward_df['ward_wastewater_m3_day'].sum()
    st.sidebar.metric("Total Wastewater", f"{total_wastewater:,.0f} m³/day")
    
    total_treatment_needed = ward_df['ward_treatment_capacity_m3_day'].sum()
    st.sidebar.metric("Treatment Capacity Needed", f"{total_treatment_needed:,.0f} m³/day")
    
    # Stone Town specific metrics (if area targeting is implemented)
    if 'stone_town_wards' in config.WARD_CLASSIFICATIONS:
        stone_town_mask = ward_df['ward_name'].isin(config.WARD_CLASSIFICATIONS['stone_town_wards'])
        if stone_town_mask.any():
            stone_town_wastewater = ward_df.loc[stone_town_mask, 'ward_wastewater_m3_day'].sum()
            st.sidebar.metric("Stone Town Wastewater", f"{stone_town_wastewater:,.0f} m³/day")
```

**Step 3: Add volume-based map visualization**
```python
def create_volume_map(gdf, volume_column='ward_wastewater_m3_day'):
    """Create choropleth map based on wastewater volumes."""
    
    # Create base map
    center_lat = gdf.geometry.centroid.y.mean()
    center_lon = gdf.geometry.centroid.x.mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
    
    # Add choropleth layer
    folium.Choropleth(
        geo_data=gdf,
        data=gdf,
        columns=['ward_name', volume_column],
        key_on='feature.properties.ward_name',
        fill_color='YlOrRd',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=f'Wastewater Volume (m³/day)',
        nan_fill_color='lightgray'
    ).add_to(m)
    
    # Add tooltips
    for idx, row in gdf.iterrows():
        folium.Marker(
            location=[row.geometry.centroid.y, row.geometry.centroid.x],
            popup=f"""
            <b>{row['ward_name']}</b><br>
            N Load: {row.get('ward_total_n_load_kg', 0):,.0f} kg/year<br>
            Wastewater: {row.get(volume_column, 0):,.0f} m³/day<br>
            Population: {row.get('ward_population', 0):,.0f}
            """,
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m)
    
    return m
```

### 3.2 Scenario Comparison Features

**Objective**: Side-by-side comparison of intervention scenarios

**Implementation**:

**Step 1: Add comparison interface**
```python
# Add to main dashboard
st.subheader("🔄 Scenario Comparison")

col1, col2 = st.columns(2)

with col1:
    scenario1 = st.selectbox("Baseline Scenario", list(config.SCENARIOS.keys()), key="scenario1")

with col2:
    scenario2 = st.selectbox("Intervention Scenario", list(config.SCENARIOS.keys()), key="scenario2")

if st.button("Compare Scenarios"):
    # Process both scenarios
    result1, ward1 = process_scenario_with_volumes(pop_df, scenario1)
    result2, ward2 = process_scenario_with_volumes(pop_df, scenario2)
    
    # Calculate differences
    comparison_df = ward1.merge(ward2, on='ward_name', suffixes=('_baseline', '_intervention'))
    comparison_df['n_load_reduction'] = comparison_df['ward_total_n_load_kg_baseline'] - comparison_df['ward_total_n_load_kg_intervention']
    comparison_df['n_load_reduction_pct'] = (comparison_df['n_load_reduction'] / comparison_df['ward_total_n_load_kg_baseline']) * 100
    
    # Display comparison metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_reduction = comparison_df['n_load_reduction'].sum()
        st.metric("Total N Reduction", f"{total_reduction:,.0f} kg/year")
    
    with col2:
        baseline_total = comparison_df['ward_total_n_load_kg_baseline'].sum()
        reduction_pct = (total_reduction / baseline_total) * 100
        st.metric("Reduction Percentage", f"{reduction_pct:.1f}%")
    
    with col3:
        intervention_volume = comparison_df['ward_wastewater_m3_day_intervention'].sum()
        st.metric("Treatment Capacity Needed", f"{intervention_volume:,.0f} m³/day")
```

**Step 2: Add difference map**
```python
def create_difference_map(gdf, comparison_df):
    """Create map showing differences between scenarios."""
    
    # Merge geographic data with comparison results
    map_df = gdf.merge(comparison_df, on='ward_name', how='left')
    
    # Create map
    center_lat = map_df.geometry.centroid.y.mean()
    center_lon = map_df.geometry.centroid.x.mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
    
    # Add choropleth for nitrogen reduction
    folium.Choropleth(
        geo_data=map_df,
        data=map_df,
        columns=['ward_name', 'n_load_reduction'],
        key_on='feature.properties.ward_name',
        fill_color='RdYlGn',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='N Load Reduction (kg/year)',
        nan_fill_color='lightgray'
    ).add_to(m)
    
    return m
```

### 3.3 Enhanced Visualizations

**Objective**: Better communication of intervention impacts

**Implementation**:

**Step 1: Add summary charts**
```python
import plotly.express as px
import plotly.graph_objects as go

def create_scenario_comparison_chart(comparison_results):
    """Create bar chart comparing scenarios."""
    
    scenarios = list(comparison_results.keys())
    n_loads = [results['total_n_load'] for results in comparison_results.values()]
    volumes = [results['total_volume'] for results in comparison_results.values()]
    
    fig = go.Figure()
    
    # Add nitrogen load bars
    fig.add_trace(go.Bar(
        name='Nitrogen Load (kg/year)',
        x=scenarios,
        y=n_loads,
        yaxis='y',
        offsetgroup=1
    ))
    
    # Add volume bars on secondary axis
    fig.add_trace(go.Bar(
        name='Wastewater Volume (m³/day)',
        x=scenarios,
        y=volumes,
        yaxis='y2',
        offsetgroup=2
    ))
    
    # Update layout
    fig.update_layout(
        title='Scenario Comparison: Nitrogen Loads and Wastewater Volumes',
        xaxis=dict(title='Scenarios'),
        yaxis=dict(title='Nitrogen Load (kg/year)', side='left'),
        yaxis2=dict(title='Wastewater Volume (m³/day)', side='right', overlaying='y'),
        barmode='group'
    )
    
    return fig
```

**Step 2: Add intervention impact visualization**
```python
def create_intervention_impact_chart(baseline_results, intervention_results):
    """Create before/after comparison chart."""
    
    categories = ['Stone Town', 'Urban Areas', 'Rural Areas', 'Total']
    baseline_values = [baseline_results[cat] for cat in categories]
    intervention_values = [intervention_results[cat] for cat in categories]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Baseline',
        x=categories,
        y=baseline_values,
        marker_color='red'
    ))
    
    fig.add_trace(go.Bar(
        name='With Intervention',
        x=categories,
        y=intervention_values,
        marker_color='green'
    ))
    
    fig.update_layout(
        title='Nitrogen Load Reduction by Area',
        xaxis_title='Geographic Area',
        yaxis_title='Nitrogen Load (kg/year)',
        barmode='group'
    )
    
    return fig
```

---

## PHASE 4: ADVANCED SCENARIOS (Future Enhancement)
*More sophisticated intervention modeling*

### 4.1 Combined Intervention Scenarios

**Objective**: Model multiple interventions simultaneously

**Implementation**:
```python
'comprehensive_2030': {
    'pop_factor': 1.25,
    'stone_town_override': {
        '1': 0.85,  # WSP for Stone Town
        '2': 0.85
    },
    'urban_override': {
        '2': 0.50,  # Improved septic systems in urban areas
        '3': 0.30   # Improved pit latrines in urban areas
    },
    'rural_override': {
        '2': 0.45,  # DEWATS for rural septic systems
        '3': 0.25,  # Improved pit latrine management
        '5': 0.20   # VIP latrine improvements
    }
}
```

### 4.2 DEWATS Rural Targeting

**Objective**: Model decentralized treatment systems

**Implementation**:
```python
'dewats_rural_2030': {
    'pop_factor': 1.25,
    'rural_override': {
        '2': 0.65,  # DEWATS for septic systems: 65% N removal
        '3': 0.40,  # Constructed wetlands for pit latrines
        '5': 0.35   # Improved VIP with DEWATS
    },
    'other_areas_override': {
        '1': 0.0,   # No change in sewer areas
        '2': 0.0,   # No change in non-rural septic
        '3': 0.0    # No change in non-rural pits
    }
}
```

### 4.3 Phased Implementation Scenarios

**Objective**: Model gradual rollout of interventions

**Implementation**:
```python
'phased_implementation_2030': {
    'pop_factor': 1.25,
    'stone_town_override': {
        '1': 0.60,  # Partial WSP implementation: 60% efficiency
        '2': 0.60
    },
    'other_areas_override': {
        '2': 0.20,  # Gradual FSM improvement: 20% efficiency
        '3': 0.10
    }
}
```

---

## EXPERT INPUT REQUIREMENTS

### GIS Expert Requirements

| **Data Need** | **Purpose** | **Priority** | **Format** | **File Location** |
|---------------|-------------|--------------|------------|-------------------|
| Stone Town ward boundaries definition | WSP service area targeting | **HIGH** | Ward name list | Update `config.py` WARD_CLASSIFICATIONS |
| Kisakasaka WSP service area | Define which wards would be connected | **HIGH** | Ward list or polygon | Update `config.py` WARD_CLASSIFICATIONS |
| Urban vs rural ward classification | Intervention targeting | **MEDIUM** | Ward classification table | Update `config.py` WARD_CLASSIFICATIONS |
| Tourism zone boundaries | Prioritization for marine protection | **MEDIUM** | Ward list | Update `config.py` WARD_CLASSIFICATIONS |
| Population density validation | Volume calculation validation | **LOW** | Census data analysis | Validate against existing census data |

**Questions for GIS Expert**:
1. Which specific wards should be classified as "Stone Town" for WSP service area?
2. What's the best way to define urban vs rural areas for intervention targeting?
3. Can you provide coordinates for the proposed Kisakasaka WSP location?
4. Which coastal wards are most critical for marine ecosystem protection?

### Sanitation Expert Requirements

| **Data Need** | **Purpose** | **Priority** | **Details** | **Code Impact** |
|---------------|-------------|--------------|-------------|-----------------|
| **Multi-Nutrient Treatment Efficiencies** | **Scenario modeling** | **HIGH** | **WSP: N=85%, P=80%, Pathogen=3.5 log?** | **Update all intervention scenarios** |
| Kisakasaka WSP design parameters | Scenario modeling | **HIGH** | Capacity, multi-pollutant efficiency, service area | Update WSP scenario in `config.py` |
| **Detergent consumption rates** | **Phosphorus calculations** | **HIGH** | **Daily consumption (g/capita/day) in Zanzibar** | **Update `D_C` in `config.py`** |
| **Phosphorus content in detergents** | **Phosphorus calculations** | **HIGH** | **P content in locally used detergents (%)** | **Update `P_D` in `config.py`** |
| Current Kibele treatment capacity | FSM scenario modeling | **HIGH** | Actual vs design capacity, multi-pollutant efficiency | Update FSM scenarios |
| Water consumption rates | Volume calculation validation | **MEDIUM** | L/capita/day for Zanzibar context | Update `WATER_CONSUMPTION_LPCD` in `config.py` |
| **DEWATS multi-pollutant performance** | **Rural scenarios** | **MEDIUM** | **N, P, pathogen removal for constructed wetlands** | **Update DEWATS scenarios** |
| Vacuum truck service patterns | FSM improvement potential | **MEDIUM** | Which areas get regular service? | Inform area-specific FSM scenarios |

**Questions for Sanitation Expert**:
1. Is 85% nitrogen removal realistic for WSP in Zanzibar's climate and operating conditions?
2. What's a realistic target for improved FSM (currently 20% of sludge reaches treatment)?
3. What water consumption rate should we use for volume calculations (currently 150 L/capita/day)?
4. Which toilet types would realistically be connected to the Kisakasaka WSP?
5. What's the actual current capacity and efficiency of Kibele treatment plant?

### Marine Biology Expert Requirements

| **Data Need** | **Purpose** | **Priority** | **Details** | **Code Impact** |
|---------------|-------------|--------------|-------------|-----------------|
| **Multi-pollutant critical thresholds** | **Impact assessment** | **HIGH** | **N, P, FIO levels causing ecosystem damage** | **Add multi-pollutant threshold analysis** |
| **Multi-pollutant field measurements** | **Model validation** | **HIGH** | **Current N, P, FIO levels in Stone Town waters** | **Validate all model outputs** |
| **FIO excretion rates** | **Pathogen calculations** | **HIGH** | **CFU/person/day for Zanzibar population** | **Update `EFIO` in `config.py`** |
| Priority marine protection zones | Scenario prioritization | **MEDIUM** | Most sensitive marine areas | Update `config.py` WARD_CLASSIFICATIONS |
| **Phosphorus-nitrogen ratios** | **Eutrophication assessment** | **MEDIUM** | **Critical N:P ratios for algal blooms** | **Add N:P ratio analysis functions** |
| Seasonal variation patterns | Model calibration | **MEDIUM** | Tourism/rainfall impact on loads | Add seasonal adjustment factors |
| **Multi-pollutant discharge standards** | **Scenario target setting** | **LOW** | **Acceptable N, P, FIO levels** | **Add multi-pollutant compliance checking** |

**Questions for Marine Biology Expert**:
1. What nitrogen concentration levels start causing damage to coral reefs and seagrass?
2. Which coastal areas are most vulnerable to nitrogen pollution?
3. Do we have baseline water quality measurements to validate our model outputs?
4. How do seasonal patterns (tourism, rainfall) affect nitrogen loads in marine environment?
5. What should be the target nitrogen reduction to protect marine ecosystems?

---

## CRITICAL QUESTIONS FOR TEAM DISCUSSION

### Model Validation Questions
1. **Volume Validation**: Can we validate our volume calculations against the reported 12,000 m³/day Stone Town discharge and 27,350 m³/day total?
2. **Parameter Sensitivity**: Which removal efficiency assumptions have the biggest impact on results?
3. **Spatial Accuracy**: How should we define geographic boundaries for intervention targeting?

### Intervention Feasibility Questions
1. **WSP Implementation**: Is 85% nitrogen removal realistic for Kisakasaka WSP in Zanzibar conditions?
2. **FSM Improvement**: What's a realistic target for improved sludge collection (from current 20%)?
3. **Timeline Assumptions**: What's a realistic implementation timeline for major interventions?
4. **Cost Considerations**: How do we balance nitrogen reduction effectiveness vs implementation cost?

### Prioritization Questions
1. **Intervention Comparison**: WSP vs improved FSM vs DEWATS - which gives best nitrogen reduction per dollar invested?
2. **Spatial Targeting**: Stone Town (high volume) vs rural areas (high per-capita impact) - where to focus first?
3. **Marine Protection**: Which coastal areas are most critical for tourism/fisheries protection?
4. **Population Growth**: How do we account for rapid population growth in intervention planning?

---

## PRACTICAL SCENARIO DEFINITIONS

Based on the report and expert input requirements, here are the most valuable scenarios to implement:

```python
# Complete scenario definitions for config.py
ENHANCED_SCENARIOS = {
    # 1. Business as usual with population growth
    'bau_2030': {
        'pop_factor': 1.25,  # 25% growth by 2030
        'nre_override': {}   # No improvements, shows problem scale
    },
    
    'bau_2050': {
        'pop_factor': 2.48,  # Based on report projections
        'nre_override': {}   # No improvements
    },
    
    # 2. Improved FSM enforcement island-wide
    'improved_fsm_2030': {
        'pop_factor': 1.25,
        'nre_override': {
            '1': 0.0,   # Sewer still untreated
            '2': 0.45,  # Septic: proper emptying to treatment
            '3': 0.25,  # Pit: regulated emptying
            '4': 0.20,  # Other systems
            '5': 0.15,  # VIP latrines
            '6': 0.15,  # Pit with slab
            '7': 0.10,  # Pit without lid
            '8': 0.05,  # Poor pit
            '9': 0.05,  # Open pit
            '10': 0.0,  # Bucket
            '11': 0.0   # Open defecation
        }
    },
    
    # 3. Technology upgrade across all systems
    'technology_upgrade_2030': {
        'pop_factor': 1.25,
        'nre_override': {
            '1': 0.60,  # Sewer with basic treatment
            '2': 0.50,  # Improved septic systems
            '3': 0.30,  # Improved pit latrines
            '4': 0.25,  # Other improved systems
            '5': 0.20,  # Improved VIP
            '6': 0.20,  # Improved pit with slab
            '7': 0.15,  # Improved pit without lid
            '8': 0.10,  # Improved poor pit
            '9': 0.05,  # Improved open pit
            '10': 0.30, # Bucket with proper disposal
            '11': 0.0   # Open defecation
        }
    },
    
    # 4. Kisakasaka WSP for Stone Town (requires area targeting)
    'kisakasaka_wsp_2030': {
        'pop_factor': 1.25,
        'stone_town_override': {
            '1': 0.85,  # Sewer connected to WSP
            '2': 0.85   # Septic connected to WSP
        },
        'other_areas_override': {
            '2': 0.0, '3': 0.0, '4': 0.0, '5': 0.0,
            '6': 0.0, '7': 0.0, '8': 0.0, '9': 0.0,
            '10': 0.0, '11': 0.0
        }
    },
    
    # 5. DEWATS for rural areas (requires area targeting)
    'dewats_rural_2030': {
        'pop_factor': 1.25,
        'rural_override': {
            '2': 0.65,  # DEWATS for septic systems
            '3': 0.40,  # Constructed wetlands for pits
            '5': 0.35   # Improved VIP with DEWATS
        },
        'other_areas_override': {
            '1': 0.0, '2': 0.0, '3': 0.0, '4': 0.0
        }
    },
    
    # 6. Combined comprehensive intervention
    'comprehensive_2030': {
        'pop_factor': 1.25,
        'stone_town_override': {
            '1': 0.85,  # WSP for Stone Town
            '2': 0.85
        },
        'urban_override': {
            '2': 0.50,  # Improved septic in urban areas
            '3': 0.30   # Improved pits in urban areas
        },
        'rural_override': {
            '2': 0.45,  # DEWATS for rural areas
            '3': 0.25,
            '5': 0.20
        }
    }
}
```

---

## IMPLEMENTATION SEQUENCE

### Week 1: Foundation Scenarios ✅ **START TODAY**
**Files to Modify**: `BEST-Z/scripts/config.py`

**Tasks**:
1. ✅ Add population growth scenarios (bau_2030, bau_2050)
2. ✅ Add improved FSM scenario
3. ✅ Add technology upgrade scenario
4. 📋 Test scenarios in existing dashboard
5. 📋 Validate results with team experts

**Testing**:
```bash
# Test new scenarios
cd /Users/edgar/zanzibar/zanzibar-model
python run_dashboard.py
# Select new scenarios in dropdown and verify results
```

### Week 2: Multi-Nutrient Calculations 🔧 **HIGH VALUE**
**Files to Modify**: 
- `BEST-Z/scripts/config.py` (add P and pathogen parameters)
- `BEST-Z/scripts/n_load.py` (add multi-nutrient functions)

**Tasks**:
1. 🔧 Add phosphorus and pathogen constants to config.py
2. 🔧 Implement `calc_phosphorus_load()` function
3. 🔧 Implement `calc_pathogen_load()` function
4. 🔧 Implement `calc_multi_nutrient_loads()` integrated function
5. 🔧 Create multi-nutrient scenario definitions
6. 📋 Validate calculations with expert input

**Expert Dependencies**:
- **Sanitation Expert**: Detergent consumption rates, P content
- **Marine Biology Expert**: FIO excretion rates

**Testing**:
```python
# Test multi-nutrient calculations
pop_df = ingest.load_census_data()
result_df = n_load.calc_multi_nutrient_loads(pop_df)
print(f"Total N load: {result_df['n_load_kg_y'].sum():.0f} kg/year")
print(f"Total P load: {result_df['p_load_total_kg_y'].sum():.0f} kg/year")
print(f"Total FIO load: {result_df['fio_load_cfu_year'].sum():.2e} CFU/year")
```

### Week 3: Volume Integration & Spatial Targeting 🔧
**Files to Modify**: 
- `BEST-Z/scripts/config.py` (add water consumption constants, ward classifications)
- `BEST-Z/scripts/n_load.py` (add volume functions, area targeting)

**Tasks**:
1. 🔧 Add water consumption constants to config.py
2. 🔧 Implement `calc_multi_nutrient_with_volume()` function
3. 🔧 Update `aggregate_ward_multi_nutrient()` function
4. 📋 Get ward classifications from GIS expert
5. 🔧 Add WARD_CLASSIFICATIONS to config.py
6. 🔧 Implement area-specific multi-nutrient scenarios
7. 🔧 Add Kisakasaka WSP multi-nutrient scenario
8. 📋 Validate volume calculations against report data (12,000 m³/day Stone Town)

**Dependencies**: 
- **GIS Expert Input**: Stone Town ward list
- **Sanitation Expert Input**: Multi-pollutant WSP efficiency parameters

**Testing**:
```python
# Test integrated multi-nutrient with volume calculations
scenario = config.MULTI_NUTRIENT_SCENARIOS['kisakasaka_wsp_multi_2030']
result_df = n_load.calc_multi_nutrient_with_volume(pop_df, scenario)
print(f"Stone Town wastewater: {result_df[stone_town_mask]['wastewater_m3_day'].sum():.0f} m³/day")
```

### Week 4: Enhanced Dashboard with Multi-Nutrient Display 🔧
**Files to Modify**: 
- `BEST-Z/scripts/interactive_dashboard.py`

**Tasks**:
1. 🔧 Add multi-nutrient metrics to dashboard sidebar
2. 🔧 Implement multi-pollutant map visualizations (N, P, FIO)
3. 🔧 Add multi-nutrient scenario comparison features
4. 🔧 Create pollutant-specific difference maps
5. 🔧 Add N:P ratio analysis and visualization
6. 🔧 Implement threshold compliance checking
7. 🔧 Add multi-pollutant summary charts
8. 📝 Update user documentation for multi-nutrient features
9. 🚀 Deploy enhanced multi-nutrient model

**Testing**:
```bash
# Test enhanced multi-nutrient dashboard
python run_dashboard.py
# Verify all pollutant metrics display
# Test multi-nutrient scenario comparisons
# Validate pollutant-specific map visualizations
# Check N:P ratio calculations
```

---

## SUCCESS METRICS

### Technical Metrics
- ✅ **Multi-nutrient calculations working correctly (N, P, FIO loads calculated simultaneously)**
- ✅ Volume calculations match reported wastewater generation (12,000 m³/day Stone Town, 27,350 m³/day total)
- ✅ Area targeting works correctly (Stone Town vs other areas show different results)
- ✅ Scenarios show meaningful differences between interventions for all pollutants
- ✅ **Dashboard displays nitrogen, phosphorus, pathogen, and volume metrics**
- ✅ **N:P ratios calculated and displayed for eutrophication assessment**
- ✅ All new functions have proper error handling and logging

### Decision Support Metrics
- ✅ **Model answers: "What's the multi-pollutant reduction from Kisakasaka WSP?"**
- ✅ **Model answers: "Which pollutant (N, P, FIO) is the limiting factor for marine ecosystem protection?"**
- ✅ Model answers: "What treatment capacity is needed for each scenario?"
- ✅ **Model answers: "FSM improvement vs WSP - which gives better overall pollutant reduction?"**
- ✅ Model answers: "Which areas should be prioritized for intervention?"
- ✅ **Model answers: "What are the N:P ratios in different scenarios and do they exceed eutrophication thresholds?"**
- ✅ Results inform World Bank investment priorities with quantitative evidence for all pollutants

### Validation Metrics
- ✅ Volume calculations validated against report data
- ✅ **Multi-pollutant load estimates validated against field measurements (N, P, FIO)**
- ✅ **Phosphorus calculations validated with detergent consumption data**
- ✅ **Pathogen calculations validated with FIO excretion rates**
- ✅ Scenario parameters validated by sanitation and marine biology experts
- ✅ Geographic targeting validated by GIS expert

### Multi-Nutrient Integration Metrics
- ✅ **Phosphorus loads from both detergents and excreta calculated separately**
- ✅ **Pathogen loads expressed in both absolute (CFU/year) and log scale**
- ✅ **Treatment efficiencies applied correctly for each pollutant type**
- ✅ **Area-specific scenarios work for all pollutants simultaneously**
- ✅ **Dashboard allows switching between N, P, and FIO visualizations**

---

## RISK MITIGATION

### Technical Risks
1. **Volume calculation accuracy**: Validate against multiple data sources
2. **Area targeting complexity**: Start with simple Stone Town vs other classification
3. **Dashboard performance**: Test with full dataset before deployment
4. **Data compatibility**: Ensure new functions work with existing data structure

### Expert Input Risks
1. **Delayed expert feedback**: Implement with reasonable assumptions, update when input received
2. **Conflicting expert opinions**: Document assumptions and allow parameter adjustment
3. **Missing data**: Use literature values with clear documentation of sources

### Implementation Risks
1. **Code complexity**: Implement incrementally, test each phase thoroughly
2. **User interface changes**: Maintain backward compatibility with existing features
3. **Performance issues**: Profile code and optimize bottlenecks

---

## DOCUMENTATION REQUIREMENTS

### Code Documentation
- ✅ All new functions have comprehensive docstrings
- ✅ Parameter assumptions clearly documented
- ✅ Data sources and validation methods documented
- ✅ Expert input requirements and assumptions documented

### User Documentation
- ✅ Update USER_MANUAL.md with new features
- ✅ Create scenario interpretation guide
- ✅ Document volume calculation methodology
- ✅ Provide examples of intervention analysis

### Technical Documentation
- ✅ Update BEST-Z_Model_Implementation_Report.md
- ✅ Document new functions and their integration
- ✅ Explain area targeting methodology
- ✅ Document validation procedures and results

## MULTI-NUTRIENT MODEL INTEGRATION SUMMARY

The enhanced BEST-Z model will calculate and analyze three critical pollutants simultaneously:

### **Nitrogen (N) - Eutrophication Driver**
- **Source**: Human excreta (protein metabolism)
- **Calculation**: `Pop * P_c * 365 * PtN * (1 - NRE) / 1000`
- **Units**: kg N/year
- **Current Baseline**: 0% removal (realistic for Zanzibar)
- **Intervention Target**: 85% removal with WSP

### **Phosphorus (P) - Eutrophication Co-Driver**
- **Sources**: Detergents + human excreta
- **Calculation**: `Pop * (D_c * P_d + P_excreta) * 365 * (1 - PRE) / 1000`
- **Units**: kg P/year
- **Current Baseline**: 0-15% removal depending on system
- **Intervention Target**: 80% removal with WSP

### **Pathogens (FIO) - Public Health Risk**
- **Source**: Human excreta (fecal indicator organisms)
- **Calculation**: `Pop * EFIO * (1 - (1 - 10^(-log_reduction)))`
- **Units**: CFU/year (also log CFU/day for interpretation)
- **Current Baseline**: 0-1.5 log reduction
- **Intervention Target**: 3.5 log reduction with WSP

### **Wastewater Volume - Infrastructure Sizing**
- **Calculation**: `Pop * water_consumption * 0.8 / 1000`
- **Units**: m³/day
- **Validation Target**: Match 12,000 m³/day Stone Town discharge

### **Key Integration Benefits**:
1. **Comprehensive Impact Assessment**: Shows which pollutant is the limiting factor
2. **N:P Ratio Analysis**: Critical for understanding eutrophication risk
3. **Multi-Pollutant Scenario Comparison**: Interventions ranked by overall environmental benefit
4. **Volume-Pollutant Integration**: Treatment capacity sized for actual pollutant loads
5. **Area-Specific Multi-Pollutant Targeting**: Stone Town WSP vs rural DEWATS effectiveness

This comprehensive work plan provides both the strategic overview needed for team presentation and the detailed technical specifications required for AI-assisted implementation of a full multi-nutrient sanitation model.