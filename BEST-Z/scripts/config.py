from pathlib import Path

# Constants
P_C = 64  # daily protein consumption per capita (g/day)
PTN = 0.16  # protein to nitrogen conversion factor

# FIO Constants
EFIO = 2e10  # per-capita FIO excretion factor (cfu person⁻¹ day⁻¹)

# Directories
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT_DIR / 'data_raw'
OUTPUT_DIR = ROOT_DIR / 'outputs'

SCENARIOS = {
    'crisis_2025_current': {
        'pop_factor': 1.0,
        'nre_override': {}
    },
    'crisis_2030_no_action': {
        'pop_factor': 1.25,  # 25% population growth by 2030 (3.7% annual * 8 years ≈ 1.25x)
        'nre_override': {}   # No improvement in treatment - same 0% removal
    },
    'crisis_2050_catastrophic': {
        'pop_factor': 2.48,  # From report: Stone Town population 219k→544k by 2050
        'nre_override': {}   # Still no treatment infrastructure - catastrophic
    }
}

# FIO Sanitation Type Mapping (toilet_type_id -> FIO category)
FIO_SANITATION_MAPPING = {
    '1': 'SewerConnection',    # Flush to sewer system
    '2': 'SepticTank',         # Flush to septic tank
    '3': 'SepticTank',         # Flush to covered pit
    '4': 'None',               # Flush to somewhere else (no containment)
    '5': 'PitLatrine',         # VIP latrine
    '6': 'PitLatrine',         # Pit with slab and lid
    '7': 'PitLatrine',         # Pit with slab without lid
    '8': 'PitLatrine',         # Pit with non-washable slab
    '9': 'PitLatrine',         # Pit without slab/open pit
    '10': 'None',              # Bucket
    '11': 'None'               # Open defecation
}

# FIO Removal Efficiencies by sanitation category
# ZANZIBAR REALITY: All systems currently have 0% removal efficiency
# - Pit latrines: Basic containment but significant leakage to groundwater
# - Septic tanks: Often overflow, not properly maintained, or discharge directly
# - Sewer connections: No treatment plants - direct discharge via 27 outfalls
FIO_REMOVAL_EFFICIENCY = {
    'None': 0.00,         # Open defecation - direct environmental release
    'PitLatrine': 0.00,   # Zanzibar reality: significant leakage, no treatment
    'SepticTank': 0.00,   # Zanzibar reality: overflow/direct discharge common
    'SewerConnection': 0.00  # Zanzibar reality: no treatment plants, direct ocean discharge
}

# FIO Crisis Scenarios - showing pathogen contamination growth
FIO_SCENARIOS = {
    'crisis_2025_current': {
        'pop_factor': 1.0,
        'fio_removal_override': {},
        'od_reduction_percent': 0.0
    },
    'crisis_2030_no_action': {
        'pop_factor': 1.25,  # 25% more people, same terrible sanitation
        'fio_removal_override': {},
        'od_reduction_percent': 0.0   # Open defecation stays the same rate
    },
    'crisis_2050_catastrophic': {
        'pop_factor': 2.48,  # Nearly 2.5x more contamination
        'fio_removal_override': {},
        'od_reduction_percent': 0.0   # Crisis explodes without intervention
    }
}

# Real-world contamination data from Zanzibar 2025 Report
REAL_WORLD_CONTAMINATION = {
    'stone_town_port_total_coliform': 11270,  # CFU - highest recorded
    'stone_town_port_fecal_coliform': 8050,   # CFU - highest recorded  
    'africa_house_enterococci': 8748,         # CFU - highest recorded
    'untreated_outfalls_count': 27,           # Number of direct ocean discharge points
    'daily_untreated_discharge_m3': 12000,    # m³/day from 3 major outfalls alone
    'sewer_coverage_percent': 18,             # Only 18% of urban population connected
    'open_defecation_percent': 11.7,          # Current prevalence rate
    'stone_town_population_2022': 219007,     # From census data
    'total_zanzibar_population_2022': 1889773, # From census data
    'annual_growth_rate': 3.7,               # Population growth rate %
}

# International Reference Standards (Car Dashboard Style - Show Numbers, Let Them Decide)
REFERENCE_STANDARDS = {
    # Water Quality References (CFU/100ml)
    'who_drinking_water_ecoli': 0,           # WHO drinking water guideline
    'who_recreational_enterococci': 200,     # WHO recreational water guideline  
    'eu_bathing_water_enterococci': 100,     # EU bathing water directive
    'us_epa_recreational_enterococci': 104,  # US EPA recreational standard
    'tanzania_bathing_water_target': 200,    # National target (if available)
    
    # Infrastructure References (%)
    'un_sdg_sanitation_target': 100,         # UN SDG 6.2 - universal sanitation
    'africa_urban_sewer_average': 30,        # Typical African urban coverage
    'middle_income_sewer_typical': 60,       # Middle-income country typical
    'who_basic_sanitation_threshold': 50,    # WHO basic coverage threshold
    
    # Treatment References
    'primary_treatment_removal': 30,         # % pathogen removal - primary treatment
    'secondary_treatment_removal': 90,       # % pathogen removal - secondary treatment
    'advanced_treatment_removal': 99,        # % pathogen removal - advanced treatment
}

# Wastewater growth projections from report (m³/day)
WASTEWATER_PROJECTIONS = {
    '2025': 111555,
    '2030': 133777, 
    '2040': 192384,
    '2050': 276667
}
