"""FIO (Faecal Indicator Organism) load calculations."""

import pandas as pd
import numpy as np
import logging
from . import config


def apply_scenario(pop_df: pd.DataFrame, scenario: dict) -> pd.DataFrame:
    """Return DataFrame with FIO load columns for a scenario.
    
    Implements: L_FIO,ward = Σ P_s × EFIO × (1 - R_s)
    """
    df = pop_df.copy()
    
    # Apply population factor
    df['population'] = df['population'] * scenario['pop_factor']
    
    # Map toilet types to FIO sanitation categories
    df['fio_sanitation_type'] = df['toilet_type_id'].astype(str).str.strip().map(
        config.FIO_SANITATION_MAPPING
    )
    
    # Add default FIO removal efficiencies
    df['fio_removal_efficiency'] = df['fio_sanitation_type'].map(
        config.FIO_REMOVAL_EFFICIENCY
    )
    
    # Apply centralized wastewater treatment improvements (affects sewered systems)
    centralized_treatment = scenario.get('centralized_treatment_percent', 0.0) / 100.0
    if centralized_treatment > 0:
        # Improve sewer connection efficiency (55% → 85% max) when treatment plants built
        sewer_mask = df['fio_sanitation_type'] == 'SewerConnection'
        base_sewer_eff = config.FIO_REMOVAL_EFFICIENCY['SewerConnection']
        improved_sewer_eff = base_sewer_eff + (0.30 * centralized_treatment)  # +30% improvement max
        df.loc[sewer_mask, 'fio_removal_efficiency'] = improved_sewer_eff
    
    # Apply fecal sludge treatment improvements (affects septic tank systems)
    fecal_sludge_treatment = scenario.get('fecal_sludge_treatment_percent', 0.0) / 100.0
    if fecal_sludge_treatment > 0:
        # Improve septic tank efficiency (40% → 70% max) when proper FSM facilities available
        septic_mask = df['fio_sanitation_type'] == 'SepticTank'
        base_septic_eff = config.FIO_REMOVAL_EFFICIENCY['SepticTank']
        improved_septic_eff = base_septic_eff + (0.30 * fecal_sludge_treatment)  # +30% improvement max
        df.loc[septic_mask, 'fio_removal_efficiency'] = improved_septic_eff
    
    # Apply manual scenario overrides for removal efficiency (these take precedence)
    for sanitation_type, override_eff in scenario['fio_removal_override'].items():
        mask = df['fio_sanitation_type'] == sanitation_type
        df.loc[mask, 'fio_removal_efficiency'] = float(override_eff)
    
    # Handle open defecation reduction scenario
    od_reduction = scenario.get('od_reduction_percent', 0.0) / 100.0
    if od_reduction > 0:
        # Convert percentage of 'None' population to 'PitLatrine'
        od_mask = df['fio_sanitation_type'] == 'None'
        
        # Create new rows for converted population
        if od_mask.any():
            converted_rows = df[od_mask].copy()
            converted_rows['population'] = converted_rows['population'] * od_reduction
            converted_rows['fio_sanitation_type'] = 'PitLatrine'
            converted_rows['fio_removal_efficiency'] = config.FIO_REMOVAL_EFFICIENCY['PitLatrine']
            
            # Reduce original open defecation population
            df.loc[od_mask, 'population'] = df.loc[od_mask, 'population'] * (1 - od_reduction)
            
            # Append converted rows
            df = pd.concat([df, converted_rows], ignore_index=True)
    
    # Handle infrastructure upgrade scenario (pit latrines to septic tanks)
    infrastructure_upgrade = scenario.get('infrastructure_upgrade_percent', 0.0) / 100.0
    if infrastructure_upgrade > 0:
        # Convert percentage of 'PitLatrine' population to 'SepticTank'
        pit_mask = df['fio_sanitation_type'] == 'PitLatrine'
        
        # Create new rows for upgraded population
        if pit_mask.any():
            upgraded_rows = df[pit_mask].copy()
            upgraded_rows['population'] = upgraded_rows['population'] * infrastructure_upgrade
            upgraded_rows['fio_sanitation_type'] = 'SepticTank'
            upgraded_rows['fio_removal_efficiency'] = config.FIO_REMOVAL_EFFICIENCY['SepticTank']
            
            # Reduce original pit latrine population
            df.loc[pit_mask, 'population'] = df.loc[pit_mask, 'population'] * (1 - infrastructure_upgrade)
            
            # Append upgraded rows
            df = pd.concat([df, upgraded_rows], ignore_index=True)
    
    # Calculate FIO loads (cfu/day)
    df['fio_total_cfu_day'] = (
        df['population'] * config.EFIO * (1 - df['fio_removal_efficiency'])
    )
    
    # Calculate open defecation component
    df['fio_open_cfu_day'] = np.where(
        df['fio_sanitation_type'] == 'None',
        df['population'] * config.EFIO,
        0
    )
    
    logging.info('Calculated FIO load for %s rows', len(df))
    return df


def aggregate_ward(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate FIO load to ward level and calculate metrics."""
    group_cols = [
        'reg_name', 'H_DISTRICT_NAME', 'H_COUNCIL_NAME',
        'H_CONSTITUENCY_NAME', 'H_DIVISION_NAME', 'ward_name'
    ]
    
    # Aggregate by ward
    ward_agg = df.groupby(group_cols).agg({
        'fio_total_cfu_day': 'sum',
        'fio_open_cfu_day': 'sum',
        'population': 'sum'
    }).reset_index()
    
    # Calculate open defecation share percentage
    ward_agg['open_share_percent'] = np.where(
        ward_agg['fio_total_cfu_day'] > 0,
        (ward_agg['fio_open_cfu_day'] / ward_agg['fio_total_cfu_day']) * 100,
        0
    )
    
    # Rename columns for consistency
    ward_agg = ward_agg.rename(columns={
        'fio_total_cfu_day': 'ward_total_fio_cfu_day',
        'fio_open_cfu_day': 'ward_open_fio_cfu_day',
        'population': 'ward_total_population'
    })
    
    logging.info('Aggregated FIO load for %s wards', len(ward_agg))
    return ward_agg


def compute_fio(pop_df: pd.DataFrame, scenario_name: str = 'baseline_2022') -> pd.DataFrame:
    """Main function to compute FIO loads for a scenario.
    
    This is the public interface function as specified in requirements.
    DEPRECATED: This function now delegates to the new layered model for 
    improved accuracy. Use fio_pipeline.compute_fio_layered() directly
    for new applications.
    
    Args:
        pop_df: Population DataFrame with toilet type data
        scenario_name: Name of scenario from config.FIO_SCENARIOS
        
    Returns:
        GeoDataFrame with ward-level FIO calculations
    """
    import warnings
    warnings.warn(
        "compute_fio() is deprecated. Consider using the new FIO layered model "
        "in fio_pipeline.py for improved accuracy and receptor concentration calculations.",
        DeprecationWarning,
        stacklevel=2
    )
    
    if scenario_name not in config.FIO_SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name}")
    
    scenario = config.FIO_SCENARIOS[scenario_name]
    
    # Apply scenario and calculate loads
    fio_df = apply_scenario(pop_df, scenario)
    
    # Aggregate to ward level
    ward_fio = aggregate_ward(fio_df)
    
    return ward_fio 


def compute_fio_layered_wrapper(pop_df: pd.DataFrame, scenario: dict, 
                               receptor_Q: float = 1e7) -> pd.DataFrame:
    """Wrapper to use new layered model with legacy data format.
    
    This function bridges between the legacy ward-based data format and 
    the new household-based layered model.
    
    Args:
        pop_df: Population DataFrame with toilet type data (legacy format)
        scenario: Scenario parameters from config.FIO_SCENARIOS  
        receptor_Q: Default receptor flow rate [L/day]
        
    Returns:
        DataFrame with receptor concentrations and ward aggregations
    """
    try:
        from . import fio_pipeline
        from . import fio_core
    except ImportError:
        import fio_pipeline
        import fio_core
    
    # Convert legacy ward-based data to household format
    # This is a simplified conversion - in practice you might want more sophisticated mapping
    households = []
    for _, row in pop_df.iterrows():
        household_id = f"{row['ward_name']}_{row.get('toilet_type_id', 'unknown')}"
        
        # Map toilet type to sanitation category for eta calculation
        toilet_type = str(row.get('toilet_type_id', '11')).strip()
        fio_sanitation_type = config.FIO_SANITATION_MAPPING.get(toilet_type, 'None')
        eta = config.FIO_REMOVAL_EFFICIENCY.get(fio_sanitation_type, 0.0)
        
        # Apply scenario overrides
        if 'fio_removal_override' in scenario:
            eta = scenario['fio_removal_override'].get(fio_sanitation_type, eta)
        
        households.append({
            'household_id': household_id,
            'pop': row.get('population', 10) * scenario.get('pop_factor', 1.0),
            'efio': config.EFIO,
            'eta': eta,
            'ward_name': row.get('ward_name', 'unknown')
        })
    
    households_df = pd.DataFrame(households)
    
    # Create synthetic receptor for the region
    receptors_df = pd.DataFrame({
        'receptor_id': ['regional_receptor'],
        'Q': [receptor_Q]
    })
    
    # Create mapping (all households to single receptor)
    mapping_df = pd.DataFrame({
        'household_id': households_df['household_id'],
        'receptor_id': 'regional_receptor',
        't': 1.0  # Default 1-day travel time
    })
    
    # Use layered model defaults
    defaults = config.FIO_LAYERED_DEFAULTS.copy()
    
    # Compute using layered model
    concentrations, contributions = fio_pipeline.compute_fio_layered(
        households_df, receptors_df, mapping_df, defaults
    )
    
    # Aggregate contributions back to ward level for compatibility
    ward_aggregations = contributions.merge(
        households_df[['household_id', 'ward_name']], 
        on='household_id'
    ).groupby('ward_name').agg({
        'L': 'sum',
        'L_reaching': 'sum'
    }).reset_index()
    
    ward_aggregations['concentration_CFU_L'] = concentrations.iloc[0]['C']
    ward_aggregations['receptor_id'] = concentrations.iloc[0]['receptor_id']
    
    logging.info(f"Layered model computed concentration: {concentrations.iloc[0]['C']:.1f} CFU/L")
    
    return ward_aggregations