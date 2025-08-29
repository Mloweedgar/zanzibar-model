# FIO Layered Model - Documentation

## Overview

This implementation provides a comprehensive three-layer FIO (Faecal Indicator Organism) contamination model that computes receptor concentrations using the formula:

```
C = (Pop × EFIO × (1 − η) × e^(−k·t)) / Q
```

## Quick Start

### Basic Usage

```bash
cd BEST-Z
python scripts/fio_cli.py compute --households data_examples/households.csv
```

### Full Usage

```bash
python scripts/fio_cli.py compute \
  --households data_examples/households.csv \
  --receptors data_examples/receptors.csv \
  --mapping data_examples/mapping.csv \
  --config data_examples/params.yaml \
  --out outputs/concentrations.csv \
  --contributions outputs/household_contributions.csv \
  --verbose
```

## Input File Formats

### households.csv (required)
```csv
household_id,lat,lon,pop,efio,eta,lrv
H1,,,10,1e9,0.5,
H2,,,15,1e9,,2.0
```

### receptors.csv (optional)
```csv
receptor_id,lat,lon,Q,Q_m3s
well_A,,,1e7,
well_B,,,5e6,
```

### mapping.csv (optional)
```csv
household_id,receptor_id,t,d
H1,well_A,1.0,
H2,well_A,1.5,
```

### params.yaml (optional)
```yaml
defaults:
  pop_per_household: 10
  efio: 1.0e9
  eta: 0.5
  k: 0.7
  t: 1.0
  Q: 1.0e7
  output_unit: CFU_L
mapping:
  mode: single
  synthetic_receptor_id: well_A
```

## Output Files

### concentrations.csv
```csv
receptor_id,total_L,total_L_reaching,total_households,Q,C
well_A,2.5e11,1.24e11,1,1e7,12414.6
```

### household_contributions.csv (optional)
```csv
household_id,receptor_id,L,L_reaching,t_used,d_used,k_used,k_s_used,eta_used,lrv_used
H1,well_A,2.5e11,1.24e11,1.0,,0.7,,0.5,
```

## Key Features

### Three-Layer Model
1. **Source Load**: `L = Pop × EFIO × (1 - η)`
2. **Environmental Decay**: `L_t = L × e^(-k×t)` or `L_d = L × e^(-k_s×d)`
3. **Receptor Concentration**: `C = L_reaching / Q`

### Parameter Conversions
- **LRV → η**: `η = 1 - 10^(-LRV)` (log-removal to efficiency)
- **T90 → k**: `k = ln(10) / T90` (time for 1-log reduction to decay constant)
- **Flow units**: m³/s → L/day conversion
- **Concentration units**: CFU/L ↔ CFU/100mL

### Mapping Strategies
- **Single**: All households → one synthetic receptor
- **Nearest**: Geographic distance-based assignment
- **Round-robin**: Even distribution across receptors
- **CSV**: Explicit household→receptor mapping

### Decay Options
- **Time-based** (preferred): First-order die-off with travel time
- **Distance-based**: Spatial attenuation over distance  
- **None**: Identity (with warning if no parameters available)

## Validation

The implementation has been validated against the worked example from `fio_modeling_markdown.md`:
- **Input**: Pop=500, EFIO=1e9, η=0.5, k=0.7, t=1, Q=1e7
- **Expected**: ≈12,400 CFU/L
- **Actual**: **12,414.6 CFU/L** ✅

## Testing

Run the test suites to validate functionality:

```bash
# Core mathematical functions
python scripts/test_fio_core.py

# Data pipeline and I/O
python scripts/test_fio_pipeline.py

# Comprehensive edge cases
python scripts/test_fio_comprehensive.py
```

## Integration

### Programmatic Usage

```python
from BEST_Z.scripts import fio_pipeline

# Load data
households = fio_pipeline.load_households_csv('households.csv')
receptors = fio_pipeline.load_receptors_csv('receptors.csv')
mapping = fio_pipeline.load_mapping_csv('mapping.csv', households, receptors)

# Compute concentrations
concentrations, contributions = fio_pipeline.compute_fio_layered(
    households, receptors, mapping
)
```

### Core Functions

```python
from BEST_Z.scripts import fio_core

# Source load calculation
L = fio_core.compute_source_load(pop=500, efio=1e9, eta=0.5)

# Apply time-based decay
L_t = fio_core.apply_decay_time(L, k=0.7, t=1.0)

# Calculate concentration
C = fio_core.compute_concentration(L_t, Q=1e7)
```

## Files Overview

- `fio_core.py` - Pure mathematical functions
- `fio_pipeline.py` - Data processing and mapping
- `fio_cli.py` - Command-line interface
- `test_fio_*.py` - Test suites
- `data_examples/` - Sample input files
- `config.py` - Extended with FIO parameters

## Domain Terminology

- **EFIO**: Excretion rate of faecal indicator organisms [CFU person⁻¹ day⁻¹]
- **η** (eta): Engineered removal efficiency [fraction, 0-1]
- **LRV**: Log-removal value [log₁₀ units]
- **k**: Die-off/inactivation rate [day⁻¹]
- **T90**: Time for 1 log₁₀ reduction [days]
- **k_s**: Spatial decay constant [m⁻¹]
- **Q**: Receiving water flow/discharge [L day⁻¹]
- **C**: Concentration at receptor [CFU L⁻¹]

## Assumptions

- Exponential decay (first-order kinetics)
- Complete mixing in receiving waters
- Uniform population shedding rates
- Site-specific sanitation effectiveness (η)
- One CSV row = one household
- Default household size: 10 persons

## Next Steps

- Integration with existing Streamlit dashboard
- Performance optimization for large datasets
- Additional geographic mapping algorithms
- Field data calibration hooks