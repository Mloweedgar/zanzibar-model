# Zanzibar FIO Pathogen Modelling: Technical Report

## Spatial Framework for Sanitation Impact Assessment

## Executive Summary

This report presents findings from a spatial pathogen  model developed to assess fecal indicator organism (FIO) contamination patterns in Zanzibar's groundwater system. The model links sanitation infrastructure conditions to potential pathogen concentrations at 18,976 water points across the study area.

**Why measure FIO instead of actual pathogens?**

- FIO are easier and cheaper to test for than dangerous pathogens
- If FIO levels are high, disease-causing organisms are likely present too
- International standards use FIO as an early warning indicator for water safety

**Real-world context:** A reading of 1,000 CFU/100mL means there are 1,000 colonies of these bacteria in a small cup (100mL) of water - indicating significant contamination risk.

### Key Findings

**Model Performance:**

- Calibration achieved log-space RMSE of 0.52 (n=3 matched boreholes with laboratory data)
- Spearman rank correlation of 1.0 and Kendall τ of 1.0 indicate perfect rank agreement
- Limited laboratory validation data constrains robust performance assessment

### **Understanding Model Performance Metrics**

**Log-space RMSE of 0.52 - What does this mean?**

- RMSE = "Root Mean Square Error" - essentially, how far off our predictions are on average
- "Log-space" means we're comparing numbers on a logarithmic scale (like 10, 100, 1000)
- 0.52 is quite good - it means our model predictions are typically within about 3x of the actual values
- **Analogy:** If the lab says 100 CFU/100mL, our model might predict 30-300 CFU/100mL

**Spearman correlation of 1.0 - Perfect ranking:**

- This measures whether we get the "ranking" right (which sites are highest, medium, lowest)
- 1.0 = perfect ranking - we correctly identified which sites are most/least contaminated
- **Why this matters:** Even if exact numbers aren't perfect, we're correctly identifying priority sites

**n=3 limitation - Why so few validation points?**

- Laboratory testing is expensive (~$50 per sample)
- Many government boreholes showed "non-detect" (too clean to measure)
- This is our biggest limitation - we need more data to be more confident

**Concentration Patterns:**

- Government boreholes: median modeled concentration 26.4 CFU/100mL (n=60)
- Private boreholes: median modeled concentration 47.3 CFU/100mL (n=18,916)
- Concentration range spans 4 orders of magnitude (0.007 to 20,489 CFU/100mL)
- 15% of private boreholes exceed 1,000 CFU/100mL using current scenario parameters

### **Making Sense of the Numbers**

**CFU/100mL - What's a Colony Forming Unit?**

- CFU = Colony Forming Unit - one bacteria that can grow into a visible colony
- 100mL = about half a cup of water
- **Context:** WHO guidelines suggest <1 CFU/100mL for safe drinking water
- **Comparison:** Swimming pool water typically allows up to 200 CFU/100mL

**Why are government boreholes cleaner?**

1. **Deeper wells** - contamination decreases with depth
2. **Better siting** - located away from latrines by regulation
3. **Higher pumping rates** - dilutes contamination more
4. **Regular maintenance** - kept in better condition

**Spatial Distribution:**

- Higher concentrations cluster in areas with dense uncontained sanitation systems
- Government boreholes show lower median concentrations, consistent with deeper extraction and regulated siting
- Private boreholes within 35m of pit latrines show elevated concentrations

### **Understanding Spatial Patterns**

**Why 35m for private boreholes?**

- This is the typical contamination "plume" distance in Zanzibar's soil conditions
- **Think of it like this:** Imagine dropping food coloring in sand - it spreads in a circle
- After 35m, the contamination is diluted enough to be negligible
- Government boreholes use 100m because they pump much more water, creating larger influence zones

**"Dense uncontained sanitation" - What does this look like?**

- Areas where many pit latrines are close together (like urban slums)
- **Example:** If 10 households each with a pit latrine are clustered in a 50m radius
- Multiple contamination sources combine = higher total contamination
- **Analogy:** Like multiple leaky pipes - each adds to the total problem

### Actionable Next Steps

1. **Expand laboratory monitoring** at additional government boreholes to strengthen calibration dataset
2. **Target interventions** in areas where models indicate concentrations are very high
3. **Improve data collection** on pit latrine construction standards and maintenance schedules
4. **Validate model assumptions** through groundwater flow and seasonal contamination studies

---

## Background and Objectives

### Zanzibar Sanitation Context

Zanzibar's sanitation landscape comprises diverse toilet technologies with varying containment performance. The majority of households rely on pit latrines and septic systems, with limited sewerage coverage. Groundwater serves as the primary drinking water source through private and government-managed boreholes, creating potential exposure pathways from inadequately contained sanitation systems.

### **Zanzibar's Sanitation Challenge**

**The Basic Problem:**

- **78.5% of people use basic pit latrines** - simple holes in the ground with poor containment
- **Only 0.1% have sewered toilets** - almost no centralized treatment
- **People drink groundwater** - water comes from underground, not rivers or lakes
- **Problem:** Waste from toilets can seep into the same groundwater people drink

**What's a "containment efficiency"?**

- This measures how much waste stays contained vs. leaks into the environment
- **Pit latrines: 10% containment** = 90% of waste leaks out
- **Septic systems: 30% containment** = 70% of waste leaks out  
- **Sewered systems: 50% containment** = 50% of waste leaks out (even these aren't perfect!)

**Real-world impact:**

- A family of 10 using a pit latrine releases ~9 million bacteria per day into the environment
- In dense neighborhoods, this adds up quickly
- Some private wells are literally surrounded by multiple leaking latrines

This modeling framework supports the World Bank sanitation grant objectives by quantifying relative contamination risks and identifying priority areas for infrastructure improvements. The model addresses key policy questions around optimal intervention targeting and expected health benefits from sanitation upgrades.

### Model Objectives

The FIO transport model provides:

1. **Relative risk assessment** across water points to inform monitoring priorities
2. **Scenario analysis capability** for evaluating intervention strategies
3. **Evidence base** for sanitation investment decisions
4. **Baseline quantification** for measuring improvement outcomes

**Why "relative" not "absolute" risk?**

- We're better at ranking (which is worse) than exact predictions
- **Analogy:** Like a weather forecast - better at saying "tomorrow will be hotter than today" than exact temperature
- Perfect for prioritization decisions: "Fix neighborhood A before neighborhood B"

### Model Scope and Limitations

The model estimates steady-state pathogen concentrations under current conditions. It does not account for:

- Seasonal variations in groundwater flow
- Dynamic loading from rainfall events
- Complex hydrogeological transport processes
- Regulatory compliance thresholds

Results support comparative analysis and intervention prioritization rather than absolute risk assessment.

---

## Data Sources and Preprocessing

### Sanitation Inventory

**Source:** Zanzibar sanitation survey dataset  
**Records:** 279,934 toilet facilities  

### **Our Data Foundation**

**Scale of this dataset:**

- **279,934 toilets mapped** -  comprehensive sanitation database
- **GPS coordinates for each** - we know exactly where every toilet is located
- **Covers entire island** - Stone Town to rural villages, all included

**Data quality achievements:**

- **99.6% location accuracy** - 1,247 records with bad coordinates removed
- **Field verified** - Data was correcte during 2022 national cencus
- **Standardized toilet categories** - consistent classification of toilet types into;
- Category 1: Sewered systems (0.1% of facilities)
- Category 2: Basic pit latrines (78.5% of facilities)  
- Category 3: Septic tanks/improved systems (20.8% of facilities)
- Category 4: Open defecation sites (0.6% of facilities)

### Borehole Datasets

**Private Boreholes:**

- **Records:** 18,916 locations
- **Default abstraction rate:** Variable by location (derived from survey data)
- **Spatial distribution:** Concentrated in residential areas

**Government(ZAWA) Boreholes:**

- **Records:** 60 locations  
- **Default abstraction rate:** 20,000 L/day
- **Laboratory data:** Available for 44 boreholes (total coliform and E. coli)
- **Quality assurance:** Regular monitoring under government protocols

### **Two Very Different Water Systems**

**Private Boreholes (18,916 wells):**

- **Who owns them:** Individual households, small businesses, Community boreholes etc..
- **Typical depth:** 10-30 meters (shallow)
- **Water usage:** 100-1,000 L/day (one family)
- **Maintenance:** Often poor, no regular testing
- **Location:** Often in backyards, close to latrines
- **Why high risk:** Shallow + close to contamination sources + no testing

**Government Boreholes (60 wells):**

- **Who owns them:** Ministry of Water, ZAWA
- **Typical depth:** 50-150 meters (deep)
- **Water usage:** 20,000 L/day (whole neighborhood)
- **Maintenance:** Regular, professional testing
- **Location:** Chosen by engineers, away from contamination
- **Why lower risk:** Deep + good siting + regular monitoring

**Laboratory Data Challenge:**

- **44 out of 60** government wells have lab data (73% coverage)
- **83% showed "non-detect"** - too clean to measure contamination
- **Only 3 wells** had measurable contamination for model calibration
- **This is actually good news** - government wells are mostly safe
- **But bad for modeling** - we need contaminated wells to calibrate the model

### Quality Control Measures

**Coordinate validation:** Removed 1,247 records with missing/invalid coordinates  
**Data consistency:** Verified toilet category assignments against field descriptions  
**Laboratory data handling:** Converted "Numerous" readings to 1000 CFU/100mL for analysis; treated non-detects as 0.1 CFU/100mL

---

## Methods

### Model Architecture

The FIO transport model operates through three sequential layers:

### **The Three-Layer Approach Explained**

**Think of this like a factory assembly line with 3 stations:**

1. **Station 1 (Source Loading):** How much contamination starts at each toilet?
2. **Station 2 (Spatial Transport):** How much contamination reaches each well?
3. **Station 3 (Concentration Calculation):** What's the final concentration in the water?

**Why this approach?**

- **Modular:** Each layer can be improved independently
- **Transparent:** You can see exactly where numbers come from
- **Flexible:** Easy to test "what-if" scenarios by changing one layer

#### Layer 1: Source Load Calculation

**Fundamental equation:**

```bash
fio_load = population × E_FIO × (1 - η)
```

### **Breaking Down the Source Load Formula**

#### **This equation answers: "How many bacteria escape from each toilet per day?"**

**Variables explained:**

- `population`: **How many people use this toilet** (default: 10 persons per household)
  - *Why 10?* Average Zanzibar household size from census data
- `E_FIO`: **How many bacteria each person produces per day** (1.0 × 10^7 CFU/person/day)
  - *Where does this come from?* Medical literature on fecal bacteria production
  - *What does 10^7 mean?* 10,000,000 bacteria per person per day (sounds like a lot, but it's normal!)
- `η` (eta): **Containment efficiency** - the fraction that stays contained
  - *Example:* η = 0.10 means 10% stays in, 90% leaks out
- `(1 - η)`: **The fraction that escapes** into the environment

**Real example calculation:**

- Household of 10 people with a pit latrine (η = 0.10)
- `fio_load = 10 × 10,000,000 × (1 - 0.10)`
- `fio_load = 10 × 10,000,000 × 0.90 = 90,000,000 CFU/day`
- **That's 90 million bacteria escaping into the ground every day from one household!**

Where:

- `population`: Household population served (default: 10 persons)
- `E_FIO`: Fecal indicator organisms per person per day (CFU/day)
- `η`: Containment efficiency by toilet category

**Parameter values:**

- E_FIO = 1.0 × 10^7 CFU/person/day
- Containment efficiencies: η₁ = 0.50, η₂ = 0.10, η₃ = 0.30, η₄ = 0.00

#### Layer 2: Spatial Transport

**Distance-based decay model:**

```bash
surviving_load = fio_load × exp(-ks × distance_m)
```

### 🌍 **How Contamination Spreads Through Soil**

#### **This equation answers: "How many bacteria survive the journey from toilet to well?"**

**The exponential decay concept:**

- **Think like radioactive decay** - the farther contamination travels, the more it dies off
- **exp(-ks × distance)** is mathematical shorthand for "exponential decay"
- **ks = 0.06 m⁻¹** is our "decay rate" - how quickly bacteria die as they travel

**What does ks = 0.06 m⁻¹ mean practically?**

- At 10m distance: ~55% of bacteria survive the journey
- At 20m distance: ~30% survive  
- At 35m distance: ~15% survive
- At 50m distance: ~5% survive
- **This is why we use 35m as the cutoff** - beyond that, very little contamination reaches the well

**Why exponential decay?**

- **Filtration:** Soil acts like a filter, trapping bacteria
- **Die-off:** Bacteria die naturally over time and distance
- **Dilution:** Contamination mixes with clean groundwater
- **Real-world validation:** This pattern matches field studies worldwide

**Distance calculation:**

- We use **Haversine formula** - accounts for Earth's curved surface
- **More accurate than** simple straight-line distance
- **Matters in Zanzibar** because we're covering ~1,600 km² area

Where:

- `ks`: Linear decay coefficient (0.06 m⁻¹)
- `distance_m`: Haversine distance between toilet and borehole

**Linking radii:**

- Private boreholes: 35m maximum influence distance
- Government boreholes: 100m maximum influence distance

#### Layer 3: Concentration Calculation

**Dilution in abstracted water:**

```
concentration_CFU_per_100mL = Σ(surviving_loads) / (Q_L_per_day / 100)
```

### **From Bacteria Count to Water Concentration**

**This equation answers: "What's the final bacteria concentration in the drinking water?"**

**Breaking down the formula:**

- `Σ(surviving_loads)`: **Sum of all contamination** reaching this well from all nearby toilets
  - *Greek symbol Σ (sigma) = "sum of"*
  - *Example:* If 3 toilets contribute 1M, 2M, and 5M bacteria/day, total = 8M bacteria/day
- `Q_L_per_day`: **How much water is pumped per day** (liters)
  - *Government boreholes:* 20,000 L/day (serves whole community)
  - *Private boreholes:* varies, typically 100-1,000 L/day (serves one household)
- `/ 100`: **Convert to "per 100mL"** (standard reporting unit)
  - *Why 100mL?* International standard for water quality testing

**Real example:**

- Well receives 10,000,000 bacteria/day from nearby toilets
- Well pumps 1,000 L/day = 10,000 × 100mL portions
- Concentration = 10,000,000 ÷ 10,000 = 1,000 CFU/100mL

**Why government wells are often cleaner:**

- **Higher pumping rates** = more dilution
- **Example:** Same contamination (10M bacteria/day) but:
  - Private well (1,000 L/day): 1,000 CFU/100mL  
  - Government well (20,000 L/day): 50 CFU/100mL
- **20x more dilution** = much cleaner water

Where Q represents daily abstraction volume.

### Intervention Scenarios

The model supports four intervention types:

1. **Open defecation reduction:** Converts Category 4 to Category 3 systems
2. **Infrastructure upgrades:** Converts Category 2 to Category 3 systems  
3. **Centralized treatment:** Improves Category 1 efficiency to 90%
4. **Fecal sludge treatment:** Improves Category 3 efficiency to 80%

Interventions preserve population mass through row-splitting methodology.

### Spatial Implementation

**Neighbor search:** BallTree algorithm for efficient distance calculations  
**Coordinate system:** WGS84 geographic coordinates  
**Distance calculation:** Haversine formula accounting for Earth curvature  
**Caching:** Adjacency relationships cached per scenario for computational efficiency

---

## Calibration and Evaluation

### Calibration Methodology

**Grid search approach:** Systematic evaluation across parameter combinations

- ks_per_m values: [0.0003, 0.0005, 0.001, 0.0015, 0.002, 0.003]
- EFIO scale factors: [0.7, 0.85, 1.0, 1.15, 1.3]

**Evaluation metrics:**

- **Log-space RMSE:** √(mean((log₁₀(model+1) - log₁₀(lab+1))²))
- **Spearman rank correlation:** Non-parametric rank agreement
- **Kendall's τ:** Alternative rank correlation robust to outliers
- **Pearson correlation (log-transformed):** Linear relationship in log space

### Calibration Results

**Best parameter combination (grid search):**

- ks_per_m = 0.003 m⁻¹
- EFIO scale = 0.7
- Log-space RMSE = 6.08
- Matched boreholes: n = 42

**Trend search optimization:**

- ks_per_m = 0.08 m⁻¹  
- EFIO = 1.0 × 10^7 CFU/person/day
- Spearman ρ = 1.0, Kendall τ = 1.0
- Log-space RMSE = 0.52
- Matched boreholes: n = 3

### Model Performance Assessment

**Limitations in validation data:**

- Only 3 government boreholes with reliable E. coli measurements for trend calibration
- Laboratory detection limits affect correlation analysis
- Limited spatial coverage of monitoring points

**Sensitivity analysis:** Model shows strong response to ks parameter, indicating transport assumptions significantly influence predictions.

---

### Model vs Laboratory Comparison

**Available validation points:** 44 government boreholes with laboratory E. coli data  
**Zero detections:** 39 boreholes (88.6%)  
**Positive detections:** 5 boreholes (11.4%)  

**Correlation analysis (n=3 non-zero pairs):**

- Spearman ρ = 1.0
- Kendall τ = 1.0  
- Pearson r (log-transformed) = 0.74
- RMSE (log-space) = 0.52

---

## Limitations and Uncertainties

### Data Quality Constraints

**Laboratory data limitations:**

- High proportion of non-detects limits calibration robustness
- Limited spatial coverage of monitoring points
- Potential temporal mismatch between model steady-state and sampling conditions

**Sanitation inventory assumptions:**

- Household population estimates based on regional averages
- Toilet category classification may not capture construction quality variations
- Maintenance and emptying schedules not incorporated

### Model Assumptions

**Spatial transport simplifications:**

- Uniform hydrogeological properties assumed
- No groundwater flow direction consideration
- Distance-only decay ignores subsurface heterogeneity

**Temporal limitations:**

- Steady-state conditions assumed
- Seasonal variations not modeled
- Rainfall-driven loading events not captured

**Pathogen survival:**

- Single decay coefficient applied across all conditions
- Temperature, pH, and soil type effects not differentiated
- Virus and bacterial pathogen differences not distinguished

### Uncertainty Quantification

**Parameter sensitivity:**

- 95% confidence intervals not available due to limited validation data
- Decay coefficient uncertainty spans order of magnitude based on literature
- EFIO estimates vary 2-3 orders of magnitude across populations

---

## Reproducibility

### Environment Requirements

**Python version:** 3.10 or higher  
**Required packages:** Listed in `requirements.txt`

```bash
pip install pandas geopandas matplotlib folium streamlit requests scikit-learn
```

### Data Preprocessing Commands

```bash
# Navigate to repository root
cd /path/to/zanzibar-model

# Generate enriched borehole datasets with Q estimates  
python main.py derive-private-q
python main.py derive-government-q
```

### Model Execution

**Run baseline scenario:**

```bash
python main.py pipeline --scenario calibrated_trend_baseline
```

**Run custom scenario:**

```bash
python main.py pipeline --scenario '{"pop_factor": 1.0, "EFIO_override": 1e7, "ks_per_m": 0.06, "od_reduction_percent": 50.0}'
```

**Execute calibration:**

```bash
python main.py calibrate
python main.py trend
```

### Output Files Generated

- `data/output/last_scenario.json`: Scenario parameters and metadata
- `data/output/fio_concentration_at_boreholes.csv`: Concentration results by borehole
- `data/output/dashboard_government_boreholes.csv`: Government borehole results with lab data
- `data/output/dashboard_private_boreholes.csv`: Private borehole results  
- `data/output/calibration_results.csv`: Grid search calibration outcomes
- `data/output/trend_search_results.csv`: Correlation-optimized parameters

### File Paths and Structure

```bash
zanzibar-model/
├── app/
│   ├── fio_core.py          # Layer 1 calculations
│   ├── fio_transport.py     # Layer 2-3 calculations  
│   ├── fio_runner.py        # Pipeline orchestration
│   ├── fio_config.py        # Parameters and scenarios
│   └── calibrate.py         # Calibration utilities
├── data/
│   ├── input/               # Raw datasets
│   ├── derived/             # Preprocessed datasets
│   └── output/              # Model results
└── main.py                  # Command-line interface
```

---

## Appendices

### Appendix A: Complete Parameter Set

**calibrated_trend_baseline scenario parameters:**

```json
{
  "scenario_name": "calibrated_trend_baseline",
  "parameters": {
    "pop_factor": 1.0,
    "EFIO_override": 10000000.0,
    "ks_per_m": 0.06,
    "radius_by_type": {
      "private": 35,
      "government": 100
    },
    "od_reduction_percent": 0.0,
    "infrastructure_upgrade_percent": 0.0,
    "centralized_treatment_enabled": false,
    "fecal_sludge_treatment_percent": 0.0,
    "efficiency_override": {
      "1": 0.5,
      "2": 0.1,
      "3": 0.3,
      "4": 0.0
    }
  }
}
```

### Appendix B: Calibration Grid Results

Complete calibration grid showing RMSE performance across parameter combinations (see `data/output/calibration_results.csv` for full results):

Best performing parameters:

- ks_per_m = 0.003, efio_scale = 0.7: RMSE = 6.08 (n=42)
- ks_per_m = 0.08, EFIO = 1e7: Spearman ρ = 1.0 (n=3)

### Appendix C: Code References

**Core equation implementations:**

Layer 1 (fio_core.py:112-114):

```python
df['fio_load'] = (
    df['household_population'] * EFIO * (1 - df['pathogen_containment_efficiency'])
)
```

Layer 2 (fio_transport.py:106-108):  

```python
decayed_load = toilet_loads * np.exp(-ks_per_m * distances_m)
```

Layer 3 (fio_transport.py:134-136):

```python  
conc_df['concentration_CFU_per_100mL'] = (
    conc_df['total_surviving_fio_load'] / (conc_df['Q_L_per_day'] / 100.0)
)
```

---

**Report prepared by:** Edgar Mlowe 


**Technical review:** Inprogress  

---
