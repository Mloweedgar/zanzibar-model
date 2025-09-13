# Enhanced Zanzibar Pathogen Model Dashboard - User Guide

## Overview

This enhanced dashboard provides a user-friendly interface for running pathogen modeling scenarios in alignment with the World Bank Terms of Reference for the Zanzibar Ocean Health and Sanitation Nexus project.

## Features

### 1. Single Scenario Analysis
Create and run individual pathogen modeling scenarios with an intuitive form-based interface.

**Key Components:**
- **Scenario Builder**: Select base templates and customize parameters
- **Sanitation Interventions**: Adjust intervention levels (OD reduction, infrastructure upgrades, treatment)
- **Population & Environment**: Set growth factors and environmental parameters
- **Advanced Settings**: Technical parameters for specialists (collapsed by default)
- **Interactive Map**: Visualize pathogen concentrations across borehole networks
- **Results Summary**: Key metrics and TOR progress tracking

### 2. Scenario Comparison Analysis
Compare multiple scenarios side-by-side to evaluate intervention effectiveness.

**Available Scenario Templates:**
- **Current Baseline**: No interventions (status quo)
- **50% Infrastructure Improvement**: Moderate intervention package
- **Full Intervention**: Comprehensive sanitation improvements

**Comparison Features:**
- Summary statistics table
- Risk level distribution charts
- Statistical comparisons (mean, median, risk percentages)
- Automated report generation for TOR deliverables

## Quick Start Guide

### Running a Single Scenario

1. **Launch the Dashboard**
   ```bash
   python man.py dashboard
   ```

2. **Configure Parameters**
   - Select a base scenario template from the dropdown
   - Adjust intervention sliders (OD reduction, infrastructure upgrade, etc.)
   - Set population growth factor
   - Optionally expand "Advanced Settings" for technical parameters

3. **Run the Model**
   - Click "🚀 Run Scenario" button
   - Wait for model execution (may take several minutes)
   - View results in the interactive map and summary tables

4. **Export Results**
   - Download borehole concentration data (CSV)
   - Export scenario parameters (JSON)
   - Generate reports for stakeholders

### Running Scenario Comparisons

1. **Navigate to Comparison Tab**
   - Click "🔀 Scenario Comparison" tab

2. **Select Scenarios**
   - Choose 2-3 scenarios from the multiselect dropdown
   - Preview parameter differences in the expandable section

3. **Execute Comparison**
   - Click "🔄 Run Scenario Comparison"
   - Wait for all scenarios to complete
   - Review comprehensive analysis results

4. **Analyze Results**
   - Study the comparison summary table
   - Examine charts showing risk distributions and concentration differences
   - Download the automated comparison report

## Understanding Results

### Pathogen Risk Categories
- **Low**: <10 CFU/100mL (Green markers)
- **Moderate**: 10-99 CFU/100mL (Blue markers)
- **High**: 100-999 CFU/100mL (Orange markers)
- **Very High**: ≥1000 CFU/100mL (Red markers)

### Key Metrics
- **Total Boreholes**: Number of water sources analyzed
- **High Risk Percentage**: Proportion of boreholes with ≥100 CFU/100mL
- **Mean/Median Concentration**: Central tendency measures
- **TOR Progress**: Deliverable completion tracking

## Model Architecture

The pathogen model uses a 3-layer approach:

1. **Layer 1**: Household pathogen loads
   - Formula: `fio_load = population × EFIO × (1 - containment_efficiency)`
   - Applies interventions (OD reduction, infrastructure upgrades)

2. **Layer 2**: Spatial transport with decay
   - Links toilets to nearby boreholes within specified radii
   - Applies exponential decay: `surviving_load = fio_load × exp(-ks × distance)`

3. **Layer 3**: Borehole concentrations
   - Formula: `concentration = sum(surviving_loads) / (flow_rate/100)`
   - Results in CFU/100mL for risk assessment

## TOR Compliance

This dashboard supports the following World Bank deliverables:

- ✅ **Automated Geospatial Data Workflows**: Streamlined data processing
- ✅ **GIS-Based Models**: Python scripts for pathogen flow analysis
- ✅ **Well Documented Scenarios**: Maps and visualizations comparing baseline vs interventions
- ✅ **Interactive Visualizations**: Stakeholder-ready presentations
- ✅ **Ready-to-use Datasets**: CSV exports for further analysis
- ✅ **Comprehensive Reports**: Technical documentation and executive summaries

## Advanced Configuration

### Custom Scenarios
Modify the scenario parameters in `app/fio_config.py` to add new templates:

```python
SCENARIOS = {
    'my_custom_scenario': {
        'pop_factor': 1.2,
        'od_reduction_percent': 40.0,
        'infrastructure_upgrade_percent': 60.0,
        # ... other parameters
    }
}
```

### Containment Efficiencies
Default efficiency values can be adjusted:
- Category 1 (Sewered): 50% containment
- Category 2 (Basic pit latrines): 10% containment  
- Category 3 (Septic/improved): 30% containment
- Category 4 (Open defecation): 0% containment

### Spatial Parameters
- **Private borehole radius**: 35m (default search distance)
- **Government borehole radius**: 100m (larger catchment area)
- **Spatial decay rate**: 0.06 1/m (pathogen die-off rate)

## Troubleshooting

### Common Issues

1. **Long execution times**: Normal for large datasets (279k households, 18k boreholes)
2. **Map loading issues**: Refresh browser or check internet connectivity
3. **Memory errors**: Reduce batch sizes in advanced settings

### Data Requirements
Ensure these files exist in `data/input/`:
- `sanitation_type.csv`: Household sanitation inventory
- `private_boreholes.csv`: Private water sources
- `government_boreholes.csv`: Public water sources

### Performance Tips
- Use smaller batch sizes for linking operations
- Run comparisons during off-peak hours
- Export results regularly to avoid data loss

## Contact and Support

For technical issues or questions about model implementation, refer to:
- Repository documentation in `/docs/`
- World Bank project team
- Technical specifications in `docs/report_prompt.md`

## Version History

- **v1.0**: Original dashboard with basic scenario running
- **v2.0**: Enhanced form-based UI with improved UX
- **v2.1**: Added scenario comparison module and advanced analytics
- **v2.2**: TOR compliance features and automated reporting

---

*This dashboard supports the World Bank STC Geospatial Programming Specialist deliverables for the Ocean Health and Sanitation Nexus project in Zanzibar.*