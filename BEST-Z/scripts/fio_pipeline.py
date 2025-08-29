"""FIO Data Processing and Mapping Functions.

This module handles data I/O, mapping strategies, and aggregation for the
FIO layered model. It bridges between raw CSV data and the core mathematical
functions, following existing repository patterns.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import math

# Handle both relative and absolute imports
try:
    from . import config
    from . import ingest
    from .fio_core import (
        compute_source_load, eta_from_lrv, k_from_T90, choose_decay,
        compute_concentration, flow_m3s_to_Lday, concentration_to_100mL
    )
except ImportError:
    # Fallback for direct execution
    import config
    import ingest
    from fio_core import (
        compute_source_load, eta_from_lrv, k_from_T90, choose_decay,
        compute_concentration, flow_m3s_to_Lday, concentration_to_100mL
    )


def load_households_csv(path: Path, defaults: Optional[Dict] = None) -> pd.DataFrame:
    """Load and validate households CSV data.
    
    Args:
        path: Path to households.csv
        defaults: Default parameter values to fill missing data
        
    Returns:
        DataFrame with validated household data
    """
    if defaults is None:
        defaults = config.FIO_LAYERED_DEFAULTS
    
    df = ingest.read_csv(path)
    
    # Validate required columns
    required = config.FIO_INPUT_SCHEMAS['households_required']
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in households.csv: {missing}")
    
    # Fill missing values with defaults
    df['pop'] = df.get('pop', defaults['pop_per_household']).fillna(defaults['pop_per_household'])
    df['efio'] = df.get('efio', defaults['efio']).fillna(defaults['efio'])
    df['eta'] = df.get('eta', defaults['eta']).fillna(defaults['eta'])
    
    # Handle LRV → eta conversion (LRV takes precedence)
    if 'lrv' in df.columns and not df['lrv'].isna().all():
        lrv_mask = ~df['lrv'].isna()
        if lrv_mask.any():
            logging.info(f"Converting {lrv_mask.sum()} LRV values to eta")
            df.loc[lrv_mask, 'eta'] = df.loc[lrv_mask, 'lrv'].apply(eta_from_lrv)
    
    # Validate and clamp eta values
    eta_invalid = (df['eta'] < 0) | (df['eta'] > 1)
    if eta_invalid.any():
        logging.warning(f"Clamping {eta_invalid.sum()} eta values to [0, 1]")
        df['eta'] = df['eta'].clip(0, 1)
    
    # Validate population >= 0
    pop_invalid = df['pop'] < 0
    if pop_invalid.any():
        logging.warning(f"Setting {pop_invalid.sum()} negative population values to default")
        df.loc[pop_invalid, 'pop'] = defaults['pop_per_household']
    
    logging.info(f"Loaded {len(df)} households from {path}")
    return df


def load_receptors_csv(path: Optional[Path], defaults: Optional[Dict] = None) -> pd.DataFrame:
    """Load and validate receptors CSV data, or create synthetic receptor.
    
    Args:
        path: Path to receptors.csv (optional)
        defaults: Default parameter values
        
    Returns:
        DataFrame with receptor data
    """
    if defaults is None:
        defaults = config.FIO_LAYERED_DEFAULTS
        
    if path is None or not path.exists():
        # Create synthetic receptor
        logging.info("Creating synthetic receptor (no receptors.csv provided)")
        receptor_id = config.FIO_MAPPING_CONFIG['synthetic_receptor_id']
        return pd.DataFrame({
            'receptor_id': [receptor_id],
            'Q': [defaults['Q']],
            'lat': [None],
            'lon': [None]
        })
    
    df = ingest.read_csv(path)
    
    # Validate required columns
    required = config.FIO_INPUT_SCHEMAS['receptors_required']
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in receptors.csv: {missing}")
    
    # Handle flow conversions - prioritize Q_m3s if available
    if 'Q_m3s' in df.columns and not df['Q_m3s'].isna().all():
        m3s_mask = ~df['Q_m3s'].isna()
        if m3s_mask.any():
            logging.info(f"Converting {m3s_mask.sum()} flows from m³/s to L/day")
            df.loc[m3s_mask, 'Q'] = df.loc[m3s_mask, 'Q_m3s'].apply(flow_m3s_to_Lday)
    
    # Fill missing Q with default
    df['Q'] = df.get('Q', defaults['Q']).fillna(defaults['Q'])
    
    # Validate Q > 0
    Q_invalid = df['Q'] <= 0
    if Q_invalid.any():
        logging.warning(f"Setting {Q_invalid.sum()} invalid flow values to default")
        df.loc[Q_invalid, 'Q'] = defaults['Q']
    
    logging.info(f"Loaded {len(df)} receptors from {path}")
    return df


def load_mapping_csv(path: Optional[Path], households: pd.DataFrame, 
                     receptors: pd.DataFrame, defaults: Optional[Dict] = None) -> pd.DataFrame:
    """Load mapping CSV or generate mapping based on strategy.
    
    Args:
        path: Path to mapping.csv (optional)
        households: Household DataFrame
        receptors: Receptors DataFrame 
        defaults: Default parameter values
        
    Returns:
        DataFrame with household→receptor mapping
    """
    if defaults is None:
        defaults = config.FIO_LAYERED_DEFAULTS
    
    if path is not None and path.exists():
        # Load explicit mapping
        df = ingest.read_csv(path)
        
        # Validate required columns
        required = config.FIO_INPUT_SCHEMAS['mapping_required']
        missing = set(required) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns in mapping.csv: {missing}")
        
        logging.info(f"Loaded explicit mapping from {path}: {len(df)} entries")
        return df
    
    # Generate mapping based on strategy
    mode = config.FIO_MAPPING_CONFIG['mode']
    logging.info(f"Generating mapping using strategy: {mode}")
    
    if mode == 'single':
        # All households → single synthetic receptor
        receptor_id = config.FIO_MAPPING_CONFIG['synthetic_receptor_id']
        mapping = pd.DataFrame({
            'household_id': households['household_id'],
            'receptor_id': receptor_id,
            't': defaults['t'],  # Use global default time
            'd': None
        })
        
    elif mode == 'nearest':
        # Assign to nearest receptor by geodesic distance
        mapping = _generate_nearest_mapping(households, receptors, defaults)
        
    elif mode == 'round_robin':
        # Distribute households evenly across receptors
        mapping = _generate_round_robin_mapping(households, receptors, defaults)
        
    else:
        raise ValueError(f"Unknown mapping mode: {mode}")
    
    logging.info(f"Generated {len(mapping)} mappings using {mode} strategy")
    return mapping


def _generate_nearest_mapping(households: pd.DataFrame, receptors: pd.DataFrame, 
                             defaults: Dict) -> pd.DataFrame:
    """Generate nearest-receptor mapping using geodesic distance."""
    # Check if coordinates are available
    h_has_coords = households[['lat', 'lon']].notna().all(axis=1)
    r_has_coords = receptors[['lat', 'lon']].notna().all(axis=1)
    
    if not h_has_coords.any() or not r_has_coords.any():
        logging.warning("Insufficient coordinates for nearest mapping, falling back to single")
        receptor_id = config.FIO_MAPPING_CONFIG['synthetic_receptor_id']
        return pd.DataFrame({
            'household_id': households['household_id'],
            'receptor_id': receptor_id,
            't': defaults['t'],
            'd': None
        })
    
    # Simple distance calculation (Euclidean approximation for small areas)
    mappings = []
    for _, household in households.iterrows():
        if pd.isna(household['lat']) or pd.isna(household['lon']):
            # No coordinates - assign to first receptor
            receptor_id = receptors.iloc[0]['receptor_id']
            distance = None
        else:
            # Find nearest receptor
            distances = []
            for _, receptor in receptors.iterrows():
                if pd.isna(receptor['lat']) or pd.isna(receptor['lon']):
                    distances.append(float('inf'))
                else:
                    # Simple Euclidean distance (suitable for small areas like Zanzibar)
                    dist = math.sqrt(
                        (household['lat'] - receptor['lat'])**2 + 
                        (household['lon'] - receptor['lon'])**2
                    ) * 111000  # Rough conversion to meters
                    distances.append(dist)
            
            nearest_idx = np.argmin(distances)
            receptor_id = receptors.iloc[nearest_idx]['receptor_id']
            distance = distances[nearest_idx] if distances[nearest_idx] != float('inf') else None
        
        mappings.append({
            'household_id': household['household_id'],
            'receptor_id': receptor_id,
            't': defaults['t'],
            'd': distance
        })
    
    return pd.DataFrame(mappings)


def _generate_round_robin_mapping(households: pd.DataFrame, receptors: pd.DataFrame,
                                 defaults: Dict) -> pd.DataFrame:
    """Generate round-robin mapping distributing households evenly."""
    mappings = []
    for i, (_, household) in enumerate(households.iterrows()):
        receptor_idx = i % len(receptors)
        receptor_id = receptors.iloc[receptor_idx]['receptor_id']
        
        mappings.append({
            'household_id': household['household_id'],
            'receptor_id': receptor_id,
            't': defaults['t'],
            'd': None
        })
    
    return pd.DataFrame(mappings)


def compute_fio_layered(households: pd.DataFrame, receptors: pd.DataFrame,
                       mapping: pd.DataFrame, defaults: Optional[Dict] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Compute FIO concentrations using the three-layer model.
    
    Args:
        households: Household data
        receptors: Receptor data
        mapping: Household→receptor mapping
        defaults: Default parameters
        
    Returns:
        Tuple of (concentrations_df, contributions_df)
    """
    if defaults is None:
        defaults = config.FIO_LAYERED_DEFAULTS
    
    # Resolve decay parameters (T90 overrides k if provided)
    k = defaults['k']
    if defaults.get('T90') is not None:
        k = k_from_T90(defaults['T90'])
        logging.info(f"Using k={k:.6f} day⁻¹ from T90={defaults['T90']} days")
    
    k_s = defaults['k_s']
    
    # Process each household-receptor link
    contributions = []
    for _, row in mapping.iterrows():
        household_id = row['household_id']
        receptor_id = row['receptor_id']
        t = row.get('t', defaults['t'])
        d = row.get('d', None)
        
        # Get household data
        h_data = households[households['household_id'] == household_id]
        if h_data.empty:
            logging.warning(f"Household {household_id} not found, skipping")
            continue
        h_data = h_data.iloc[0]
        
        # Compute source load
        L = compute_source_load(h_data['pop'], h_data['efio'], h_data['eta'])
        
        # Apply decay
        L_reaching, decay_method = choose_decay(L, t, k, d, k_s)
        
        contributions.append({
            'household_id': household_id,
            'receptor_id': receptor_id,
            'L': L,
            'L_reaching': L_reaching,
            't_used': t if decay_method == 'time' else None,
            'd_used': d if decay_method == 'distance' else None,
            'k_used': k if decay_method == 'time' else None,
            'k_s_used': k_s if decay_method == 'distance' else None,
            'eta_used': h_data['eta'],
            'lrv_used': h_data.get('lrv', None)
        })
    
    contributions_df = pd.DataFrame(contributions)
    
    # Aggregate by receptor
    receptor_agg = contributions_df.groupby('receptor_id').agg({
        'L': 'sum',
        'L_reaching': 'sum',
        'household_id': 'count'
    }).reset_index()
    
    receptor_agg.rename(columns={
        'L': 'total_L',
        'L_reaching': 'total_L_reaching',
        'household_id': 'total_households'
    }, inplace=True)
    
    # Add receptor flow data and compute concentrations
    concentrations = receptor_agg.merge(receptors[['receptor_id', 'Q']], on='receptor_id')
    concentrations['C'] = concentrations.apply(
        lambda row: compute_concentration(row['total_L_reaching'], row['Q']), axis=1
    )
    
    # Convert units if requested
    if defaults['output_unit'] == 'CFU_100mL':
        concentrations['C'] = concentrations['C'].apply(concentration_to_100mL)
    
    logging.info(f"Computed concentrations for {len(concentrations)} receptors")
    return concentrations, contributions_df