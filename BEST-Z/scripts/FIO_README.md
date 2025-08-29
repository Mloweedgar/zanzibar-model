# FIO Pathogen Model Implementation

This directory contains the fresh implementation of the FIO (Fecal Indicator Organism) pathogen model as specified in `docs/FIO_Pathogen_Model_Rebuild_Spec.md`.

## Overview

The model implements a three-layered approach to pathogen contamination modeling:

1. **Layer 1 - Source Load**: `L = Pop × EFIO × (1 − η)` 
2. **Layer 2 - Spatial Transport**: `L_d = L × e^(-k_s × d)`
3. **Layer 3 - Dilution**: `C = L_t / Q`

## Implementation Files

- **`fio_config.py`**: Configuration, parameters, scenarios, and file paths
- **`fio_core.py`**: Data standardization and Layer 1 load calculations
- **`fio_transport.py`**: Spatial linking and Layers 2-3 transport/dilution
- **`fio_runner.py`**: CLI orchestrator for the complete pipeline

## Usage

### Basic Usage
```bash
cd BEST-Z
python -m scripts.fio_runner
```

### With Scenarios
```bash
# Predefined scenarios
python -m scripts.fio_runner --scenario crisis_2030_no_action
python -m scripts.fio_runner --scenario intervention_2030

# Custom scenario
python -m scripts.fio_runner --scenario '{"pop_factor": 1.25, "od_reduction_percent": 10}'
```

## Output Files

The model generates 7 deterministic CSV files in `context/derived_data/`:

1. `sanitation_type_with_population.csv` - Standardized sanitation data
2. `net_pathogen_load_from_households.csv` - Layer 1 FIO loads
3. `private_boreholes_with_id.csv` - Private borehole locations with IDs
4. `government_boreholes_with_id.csv` - Government borehole locations with IDs
5. `net_surviving_pathogen_load_links.csv` - Toilet-borehole spatial links
6. `net_surviving_pathogen_concentration_links.csv` - Links with concentrations
7. `fio_concentration_at_boreholes.csv` - Final borehole contamination levels

## Model Validation

Successfully tested with:
- ✅ 279,934 household toilet records
- ✅ 18,976 borehole locations (18,916 private + 60 government)
- ✅ 8,096 spatial links within search radii
- ✅ 5,251 boreholes with contamination concentrations
- ✅ All intervention scenarios (OD reduction, infrastructure upgrades, treatment)

## Performance

The model processes the full Zanzibar dataset in approximately 4-6 minutes with:
- Layer 1 calculations: ~1 second
- Layer 2 spatial linking: ~4-5 minutes (depends on search radii)
- Layer 3 dilution calculations: ~1 second

## Key Features

- **Vectorized calculations** for performance
- **Flexible scenario system** supporting interventions
- **Robust error handling** with detailed logging
- **Deterministic outputs** for reproducible results
- **Comprehensive validation** of all data transformations