"""Core FIO model functions for data standardization and Layer 1 calculations."""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Tuple, Dict, Any

from . import fio_config as config


def standardize_sanitation_table(
    raw_path: str, 
    out_path: str, 
    category_eff_map: Dict[int, float], 
    household_population_default: int
) -> pd.DataFrame:
    """
    Standardize sanitation data by applying column mapping, adding efficiency and population.
    
    Args:
        raw_path: Path to raw sanitation_type.csv
        out_path: Path to save standardized output
        category_eff_map: Map of toilet_category_id -> containment efficiency
        household_population_default: Default household population
        
    Returns:
        Standardized DataFrame with required columns
    """
    logging.info(f"Loading raw sanitation data from {raw_path}")
    df = pd.read_csv(raw_path)
    
    # Apply column mapping
    available_cols = set(df.columns)
    mapping_to_use = {k: v for k, v in config.SANITATION_COLUMN_MAPPING.items() 
                      if k in available_cols}
    
    if not mapping_to_use:
        raise ValueError(f"No expected columns found in {raw_path}. Available: {list(df.columns)}")
    
    logging.info(f"Applying column mapping: {mapping_to_use}")
    df_mapped = df[list(mapping_to_use.keys())].rename(columns=mapping_to_use)
    
    # Validate required columns exist after mapping
    required_cols = ['id', 'lat', 'long', 'toilet_category_id']
    missing_cols = [col for col in required_cols if col not in df_mapped.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns after mapping: {missing_cols}")
    
    # Coerce numeric fields
    df_mapped['lat'] = pd.to_numeric(df_mapped['lat'], errors='coerce')
    df_mapped['long'] = pd.to_numeric(df_mapped['long'], errors='coerce')
    df_mapped['toilet_category_id'] = pd.to_numeric(df_mapped['toilet_category_id'], errors='coerce')
    
    # Add pathogen containment efficiency
    df_mapped['pathogen_containment_efficiency'] = df_mapped['toilet_category_id'].map(category_eff_map)
    
    # Fill missing efficiencies with 0 (no containment)
    df_mapped['pathogen_containment_efficiency'] = df_mapped['pathogen_containment_efficiency'].fillna(0.0)
    
    # Add household population
    df_mapped['household_population'] = household_population_default
    
    # Drop rows with missing coordinates
    before_clean = len(df_mapped)
    df_mapped = df_mapped.dropna(subset=['lat', 'long'])
    after_clean = len(df_mapped)
    
    if before_clean != after_clean:
        logging.warning(f"Dropped {before_clean - after_clean} rows with missing coordinates")
    
    # Save standardized data
    df_mapped.to_csv(out_path, index=False)
    logging.info(f"Saved standardized sanitation data to {out_path} ({len(df_mapped)} rows)")
    
    return df_mapped


def apply_interventions(df: pd.DataFrame, scenario: Dict[str, Any]) -> pd.DataFrame:
    """
    Apply intervention scenarios by modifying population distribution.
    
    Applies in order:
    1. Open defecation reduction (convert to pit latrines)
    2. Infrastructure upgrades (convert pit latrines to septic)
    
    Args:
        df: Standardized sanitation DataFrame
        scenario: Scenario dictionary with intervention parameters
        
    Returns:
        DataFrame with interventions applied (may have more rows due to splits)
    """
    df = df.copy()
    
    # Apply population factor
    pop_factor = scenario.get('pop_factor', 1.0)
    df['household_population'] = df['household_population'] * pop_factor
    
    # 1. Open defecation reduction
    od_reduction = scenario.get('od_reduction_percent', 0.0) / 100.0
    if od_reduction > 0:
        logging.info(f"Applying {od_reduction*100:.1f}% open defecation reduction")
        
        # Identify open defecation households (category 4 = no containment)
        od_mask = df['toilet_category_id'] == 4
        
        if od_mask.any():
            # Create converted rows (OD -> pit latrine)
            converted_rows = df[od_mask].copy()
            converted_rows['household_population'] = converted_rows['household_population'] * od_reduction
            converted_rows['toilet_category_id'] = 2  # Convert to basic pit latrine
            converted_rows['pathogen_containment_efficiency'] = 0.20  # Update efficiency
            
            # Reduce original OD population
            df.loc[od_mask, 'household_population'] = df.loc[od_mask, 'household_population'] * (1 - od_reduction)
            
            # Append converted rows
            df = pd.concat([df, converted_rows], ignore_index=True)
    
    # 2. Infrastructure upgrades (pit latrine -> septic)
    upgrade_percent = scenario.get('infrastructure_upgrade_percent', 0.0) / 100.0
    if upgrade_percent > 0:
        logging.info(f"Applying {upgrade_percent*100:.1f}% infrastructure upgrade")
        
        # Identify pit latrine households (category 2)
        pit_mask = df['toilet_category_id'] == 2
        
        if pit_mask.any():
            # Create upgraded rows (pit -> septic)
            upgraded_rows = df[pit_mask].copy()
            upgraded_rows['household_population'] = upgraded_rows['household_population'] * upgrade_percent
            upgraded_rows['toilet_category_id'] = 3  # Convert to septic
            upgraded_rows['pathogen_containment_efficiency'] = 0.90  # Update efficiency
            
            # Reduce original pit population
            df.loc[pit_mask, 'household_population'] = df.loc[pit_mask, 'household_population'] * (1 - upgrade_percent)
            
            # Append upgraded rows
            df = pd.concat([df, upgraded_rows], ignore_index=True)
    
    # Remove rows with zero population
    df = df[df['household_population'] > 0].reset_index(drop=True)
    
    logging.info(f"Applied interventions: {len(df)} household records")
    return df


def compute_layer1_loads(df: pd.DataFrame, EFIO: float) -> pd.DataFrame:
    """
    Compute Layer 1 FIO loads and save net pathogen load file.
    
    Implements: fio_load = household_population × EFIO × (1 − η)
    
    Args:
        df: DataFrame with interventions applied
        EFIO: FIO excretion rate (CFU·person⁻¹·day⁻¹)
        
    Returns:
        DataFrame with fio_load column added
    """
    df = df.copy()
    
    # Calculate FIO load using Layer 1 formula
    df['fio_load'] = (
        df['household_population'] * EFIO * (1 - df['pathogen_containment_efficiency'])
    )
    
    # Create pathogen load output with required columns
    pathogen_load_df = df[['id', 'lat', 'long', 'fio_load']].copy()
    
    # Save to specified output path
    pathogen_load_df.to_csv(config.NET_PATHOGEN_LOAD_PATH, index=False)
    logging.info(f"Saved net pathogen load to {config.NET_PATHOGEN_LOAD_PATH} ({len(pathogen_load_df)} records)")
    
    # Log summary statistics
    total_load = df['fio_load'].sum()
    max_load = df['fio_load'].max()
    logging.info(f"Total FIO load: {total_load:.2e} CFU/day, Max household load: {max_load:.2e} CFU/day")
    
    return df


def build_or_load_household_tables(
    context_dir: Path, 
    scenario: Dict[str, Any]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build or load standardized household sanitation tables with Layer 1 calculations.
    
    Args:
        context_dir: Path to context directory 
        scenario: Scenario dictionary
        
    Returns:
        Tuple of (standardized_df, pathogen_load_df)
    """
    # Check if standardized file exists and has required columns
    if config.SANITATION_STANDARDIZED_PATH.exists():
        logging.info(f"Loading existing standardized data from {config.SANITATION_STANDARDIZED_PATH}")
        df = pd.read_csv(config.SANITATION_STANDARDIZED_PATH)
        
        # Check if it has the required columns for our new model
        required_cols = ['household_population', 'pathogen_containment_efficiency']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            logging.info(f"Existing file missing required columns {missing_cols} - rebuilding from raw data")
            df = standardize_sanitation_table(
                raw_path=str(config.SANITATION_RAW_PATH),
                out_path=str(config.SANITATION_STANDARDIZED_PATH),
                category_eff_map=config.CONTAINMENT_EFFICIENCY_DEFAULT,
                household_population_default=config.HOUSEHOLD_POPULATION_DEFAULT
            )
    else:
        # Build from raw data
        logging.info("Building standardized sanitation table from raw data")
        df = standardize_sanitation_table(
            raw_path=str(config.SANITATION_RAW_PATH),
            out_path=str(config.SANITATION_STANDARDIZED_PATH),
            category_eff_map=config.CONTAINMENT_EFFICIENCY_DEFAULT,
            household_population_default=config.HOUSEHOLD_POPULATION_DEFAULT
        )
    
    # Apply interventions
    df_with_interventions = apply_interventions(df, scenario)
    
    # Compute Layer 1 loads
    EFIO = scenario.get('EFIO_override') or config.EFIO_DEFAULT
    df_with_loads = compute_layer1_loads(df_with_interventions, EFIO)
    
    # Load pathogen load output for return
    pathogen_load_df = pd.read_csv(config.NET_PATHOGEN_LOAD_PATH)
    
    return df_with_loads, pathogen_load_df