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
    
    # Apply scenario overrides for removal efficiency
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
    
    Args:
        pop_df: Population DataFrame with toilet type data
        scenario_name: Name of scenario from config.FIO_SCENARIOS
        
    Returns:
        GeoDataFrame with ward-level FIO calculations
    """
    if scenario_name not in config.FIO_SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name}")
    
    scenario = config.FIO_SCENARIOS[scenario_name]
    
    # Apply scenario and calculate loads
    fio_df = apply_scenario(pop_df, scenario)
    
    # Aggregate to ward level
    ward_fio = aggregate_ward(fio_df)
    
    return ward_fio 