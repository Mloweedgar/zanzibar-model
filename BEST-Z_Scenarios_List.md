# 📋 **BEST-Z Model Scenarios List**
---

## **Currently Implemented** (in config.py)

### ✅ **Existing Scenarios**
1. **`baseline_2022`** - Current conditions, no growth, no improvements
   - Population factor: 1.0
   - Nitrogen removal: 0% (all toilet types)

2. **`improved_removal`** - Uniform 80% improvement across major toilet types
   - Population factor: 1.0  
   - Nitrogen removal: 80% for types 1-4

3. **`pop_growth_2030`** - Basic population growth only
   - Population factor: 1.2 (20% growth)
   - Nitrogen removal: 0% (no improvements)

---

## **Phase 1: Quick Wins** (Ready to Implement)

### 🚀 **Population Growth Scenarios**
4. **`bau_2030`** - Business-as-usual with realistic growth
   - Population factor: 1.25 (25% growth by 2030)
   - Nitrogen removal: 0% (shows problem scale)

5. **`bau_2050`** - Long-term growth projection
   - Population factor: 2.48 (148% growth by 2050)
   - Nitrogen removal: 0% (demonstrates urgency)

### 🔧 **Intervention Scenarios**
6. **`improved_fsm_2030`** - Better sludge collection & treatment
   - Population factor: 1.25
   - Nitrogen removal: 0-45% (varies by toilet type)
   - Focus: Enforcement and existing facility utilization

7. **`technology_upgrade_2030`** - Uniform technology improvements
   - Population factor: 1.25
   - Nitrogen removal: 5-60% (varies by toilet type)
   - Focus: System-wide upgrades

---

## **Phase 2: Spatial Targeting** (Requires Code Extension)

### 🏛️ **Stone Town Focus**
8. **`kisakasaka_wsp_2030`** - Waste Stabilization Pond for Stone Town
   - Population factor: 1.25
   - Stone Town nitrogen removal: 85% (sewer connected to WSP)
   - Other areas: Baseline (0%)
   - **Infrastructure**: New WSP facility

### 🌾 **Rural Focus**  
9. **`dewats_rural_2030`** - Decentralized treatment for rural areas
   - Population factor: 1.25
   - Rural nitrogen removal: 65% (DEWATS systems)
   - Urban areas: Baseline (0%)
   - **Infrastructure**: Multiple DEWATS installations

### 🎯 **Comprehensive Intervention**
10. **`comprehensive_2030`** - Combined multi-area approach
    - Population factor: 1.25
    - Stone Town: 85% (WSP)
    - Rural areas: 65% (DEWATS)  
    - Urban areas: 45% (improved FSM)
    - **Infrastructure**: All interventions combined

---

## **Phase 3: Multi-Nutrient Scenarios** (Advanced Implementation)

### 🧪 **Multi-Pollutant Models**
11. **`kisakasaka_wsp_multi_2030`** - WSP with N, P, and pathogen calculations
    - Nitrogen removal: 85% (Stone Town)
    - Phosphorus removal: 80% (Stone Town)
    - Pathogen reduction: 3-4 log reduction

12. **`improved_fsm_multi_2030`** - FSM with all pollutants
    - Nitrogen removal: 25-45%
    - Phosphorus removal: 20-40%
    - Pathogen reduction: 1-2 log reduction

---

## **Scenario Categories by Implementation Complexity**

### 🟢 **IMMEDIATE** (Can implement today)
- `bau_2030`, `bau_2050`
- `improved_fsm_2030` 
- `technology_upgrade_2030`

### 🟡 **MODERATE** (Requires area targeting - 1-2 weeks)
- `kisakasaka_wsp_2030`
- `dewats_rural_2030`
- `comprehensive_2030`

### 🔴 **ADVANCED** (Requires multi-nutrient model - 2-4 weeks)
- `kisakasaka_wsp_multi_2030`
- `improved_fsm_multi_2030`
- All phosphorus and pathogen scenarios

---

## **Scenario Comparison Framework**

### **Key Metrics for Each Scenario**
- **Total nitrogen load** (kg N/year)
- **Load reduction** (% vs baseline)
- **Wastewater volume** (m³/day) - *Phase 2*
- **Phosphorus load** (kg P/year) - *Phase 3*
- **Pathogen load** (CFU/day) - *Phase 3*

### **Geographic Analysis**
- **Stone Town** impact
- **Rural areas** impact  
- **Island-wide** totals
- **Hotspot identification**

### **Policy Relevance**
- **Infrastructure requirements**
- **Implementation timeline**
- **Cost-effectiveness ranking**
- **Environmental impact priority**

---

## **Detailed Scenario Specifications**

### **Phase 1 Scenarios - Ready to Implement**

#### **`bau_2030` - Business as Usual 2030**
```python
'bau_2030': {
    'pop_factor': 1.25,  # 25% growth by 2030 (3.7% annual * 8 years)
    'nre_override': {}   # No treatment improvements
}
```
**Purpose**: Shows nitrogen load increase from population growth alone  
**Value**: Demonstrates urgency of intervention  

#### **`bau_2050` - Business as Usual 2050**
```python
'bau_2050': {
    'pop_factor': 2.48,  # Stone Town: 27,350→67,830 m³/day growth from report
    'nre_override': {}   # No treatment improvements
}
```
**Purpose**: Long-term projection without intervention  
**Value**: Shows scale of future problem  

#### **`improved_fsm_2030` - Improved Fecal Sludge Management**
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
**Purpose**: Models better enforcement and collection  
**Value**: Shows impact of policy improvements  
**Rationale**: Report shows only 20% of sludge reaches treatment currently  

#### **`technology_upgrade_2030` - Technology Upgrade**
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
**Purpose**: Models uniform technology upgrades  
**Value**: Comparison with targeted interventions  

### **Phase 2 Scenarios - Spatial Targeting**

#### **`kisakasaka_wsp_2030` - Kisakasaka Waste Stabilization Pond**
```python
'kisakasaka_wsp_2030': {
    'pop_factor': 1.25,  # Population growth to 2030
    'stone_town_override': {
        '1': 0.85,  # Sewer connected to WSP: 85% N removal
        '2': 0.45,  # Septic in Stone Town: improved collection to WSP
    },
    'other_areas_override': {
        # Rural and other urban areas remain at baseline
    }
}
```
**Purpose**: Models proposed WSP for Stone Town  
**Infrastructure**: New treatment facility 12km south of Stone Town  
**Capacity**: Designed for 12,000 m³/day (current Stone Town discharge)  

#### **`dewats_rural_2030` - Rural DEWATS Implementation**
```python
'dewats_rural_2030': {
    'pop_factor': 1.25,
    'rural_override': {
        '2': 0.65,  # DEWATS for septic systems: 65% N removal
        '3': 0.50,  # DEWATS for pit latrines: 50% N removal
    },
    'urban_areas_override': {
        # Urban areas remain at baseline
    }
}
```
**Purpose**: Models decentralized treatment for rural areas  
**Infrastructure**: Multiple constructed wetlands  
**Benefit**: Reduced transportation costs and emissions  

#### **`comprehensive_2030` - Combined Intervention**
```python
'comprehensive_2030': {
    'pop_factor': 1.25,
    'stone_town_override': {
        '1': 0.85,  # WSP for Stone Town
        '2': 0.70,  # Improved septic with WSP connection
    },
    'urban_override': {
        '2': 0.45,  # Improved FSM for urban septic
        '3': 0.25,  # Improved FSM for urban pit latrines
    },
    'rural_override': {
        '2': 0.65,  # DEWATS for rural septic
        '3': 0.50,  # DEWATS for rural pit latrines
    }
}
```
**Purpose**: Models all interventions combined  
**Infrastructure**: WSP + improved FSM + rural DEWATS  
**Value**: Maximum impact scenario  

---

## **Implementation Testing Strategy**

### **Phase 1 Testing**
```python
# Compare Phase 1 scenarios
baseline = n_load.apply_scenario(pop_df, config.SCENARIOS['baseline_2022'])
bau_2030 = n_load.apply_scenario(pop_df, config.SCENARIOS['bau_2030'])
improved_fsm = n_load.apply_scenario(pop_df, config.SCENARIOS['improved_fsm_2030'])
tech_upgrade = n_load.apply_scenario(pop_df, config.SCENARIOS['technology_upgrade_2030'])

print(f"Baseline N load: {baseline['n_load_kg_y'].sum():.0f} kg/year")
print(f"BAU 2030 N load: {bau_2030['n_load_kg_y'].sum():.0f} kg/year")
print(f"Improved FSM N load: {improved_fsm['n_load_kg_y'].sum():.0f} kg/year")
print(f"Tech upgrade N load: {tech_upgrade['n_load_kg_y'].sum():.0f} kg/year")
```

### **Validation Criteria**
- **Population growth**: Verify 25% increase by 2030 aligns with 3.7% annual rate
- **Load calculations**: Ensure nitrogen loads scale proportionally with population
- **Efficiency ranges**: Confirm removal efficiencies are within realistic bounds
- **Geographic targeting**: Validate area classifications match Zanzibar geography

---

## **Expert Input Requirements**

### **Sanitation Engineering Expert**
- **Wastewater generation rates**: L/person/day for urban/rural/tourist areas
- **Treatment efficiency validation**: Realistic removal rates for each intervention
- **Implementation feasibility**: Timeline and capacity constraints

### **Marine Biology Expert**  
- **Phosphorus parameters**: Detergent consumption and P content
- **Pathogen priorities**: Focus organisms and critical thresholds
- **Ecosystem impact**: Load reduction targets for marine protection

### **Policy Expert**
- **Intervention priorities**: Political and financial feasibility ranking
- **Implementation timeline**: Realistic deployment schedules
- **Regulatory framework**: Enforcement capacity and requirements

---

## **Next Steps for Implementation**

### **This Week** (Phase 1)
1. ✅ Add `bau_2030`, `bau_2050`, `improved_fsm_2030`, `technology_upgrade_2030` to config.py
2. ✅ Test scenarios in dashboard
3. ✅ Generate comparison visualizations
4. ✅ Validate with expert input

### **Next 2 Weeks** (Phase 2)  
1. ⏳ Implement area targeting system
2. ⏳ Add Stone Town and rural ward classifications
3. ⏳ Implement spatial scenarios with expert-validated parameters
4. ⏳ Add wastewater volume calculations

### **Following Month** (Phase 3)
1. ⏳ Implement phosphorus and pathogen load models
2. ⏳ Create multi-nutrient scenario comparisons
3. ⏳ Develop cost-effectiveness analysis framework
4. ⏳ Integrate with policy decision-support tools

---

## **File Locations**

- **Current scenarios**: `/BEST-Z/scripts/config.py`
- **Scenario application**: `/BEST-Z/scripts/n_load.py`
- **Dashboard integration**: `/BEST-Z/scripts/interactive_dashboard.py`
- **Work plan details**: `/BEST-Z_Enhancement_Work_Plan.md`
- **Expert presentation**: `/BEST-Z_Expert_Presentation.md`

---

*This comprehensive scenario list provides a clear roadmap from immediate quick wins to advanced multi-pollutant modeling, all designed to support evidence-based sanitation planning in Zanzibar.*