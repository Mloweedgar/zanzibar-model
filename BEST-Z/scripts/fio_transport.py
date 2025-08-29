"""FIO transport and dilution calculations (Layers 2-3)."""

import pandas as pd
import numpy as np
import logging
from typing import Tuple, List, Dict, Any

from . import fio_config as config


def haversine_m(lat1: float, lon1: float, lat2_arr: np.ndarray, lon2_arr: np.ndarray) -> np.ndarray:
    """
    Vectorized haversine distance calculation in meters.
    
    Args:
        lat1, lon1: Single point coordinates (degrees)
        lat2_arr, lon2_arr: Arrays of coordinates (degrees)
        
    Returns:
        Array of distances in meters
    """
    # Convert to radians
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2_arr)
    lon2_rad = np.radians(lon2_arr)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = (np.sin(dlat/2)**2 + 
         np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2)
    c = 2 * np.arcsin(np.sqrt(a))
    
    # Earth radius in meters
    R = 6371000
    distance = R * c
    
    return distance


def load_boreholes_with_ids(path_in: str, path_out: str, prefix: str) -> pd.DataFrame:
    """
    Load borehole data and ensure ID column exists.
    
    Args:
        path_in: Input borehole CSV path
        path_out: Output path for borehole file with IDs
        prefix: ID prefix for generated IDs (e.g., 'privbh', 'govbh')
        
    Returns:
        DataFrame with guaranteed 'id', 'lat', 'long' columns
    """
    logging.info(f"Loading borehole data from {path_in}")
    df = pd.read_csv(path_in)
    
    # Standardize coordinate column names (fuzzy matching)
    coord_mapping = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower in ['lat', 'latitude']:
            coord_mapping[col] = 'lat'
        elif col_lower in ['long', 'lon', 'longitude']:
            coord_mapping[col] = 'long'
    
    if coord_mapping:
        df = df.rename(columns=coord_mapping)
        logging.info(f"Mapped coordinate columns: {coord_mapping}")
    
    # Ensure lat/long columns exist
    if 'lat' not in df.columns or 'long' not in df.columns:
        raise ValueError(f"Could not find lat/long columns in {path_in}. Available: {list(df.columns)}")
    
    # Coerce coordinates to numeric
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['long'] = pd.to_numeric(df['long'], errors='coerce')
    
    # Drop rows with missing coordinates
    before_clean = len(df)
    df = df.dropna(subset=['lat', 'long'])
    after_clean = len(df)
    
    if before_clean != after_clean:
        logging.warning(f"Dropped {before_clean - after_clean} borehole records with missing coordinates")
    
    # Create ID column if missing
    if 'id' not in df.columns:
        df['id'] = [f"{prefix}_{i:03d}" for i in range(len(df))]
        logging.info(f"Generated {len(df)} IDs with prefix '{prefix}'")
    
    # Ensure id column is string type
    df['id'] = df['id'].astype(str)
    
    # Save with IDs
    df.to_csv(path_out, index=False)
    logging.info(f"Saved borehole data with IDs to {path_out} ({len(df)} records)")
    
    return df


def link_sources_to_boreholes(
    toilets_df: pd.DataFrame, 
    bores_df: pd.DataFrame, 
    borehole_type: str,
    ks_per_m: float,
    radius_m: float
) -> pd.DataFrame:
    """
    Link toilet sources to boreholes within radius and compute surviving FIO load.
    
    Implements Layer 2: surviving_fio_load = fio_load × exp(−ks_per_m × distance_m)
    
    Args:
        toilets_df: DataFrame with toilet/household data
        bores_df: DataFrame with borehole data  
        borehole_type: Type identifier ('private' or 'government')
        ks_per_m: Spatial decay constant (m⁻¹)
        radius_m: Maximum linking distance (meters)
        
    Returns:
        DataFrame with toilet-borehole links and surviving loads
    """
    logging.info(f"Linking {len(toilets_df)} toilets to {len(bores_df)} {borehole_type} boreholes (radius: {radius_m}m)")
    
    if bores_df.empty:
        logging.warning(f"No {borehole_type} boreholes to link to")
        return pd.DataFrame(columns=[
            'toilet_id', 'toilet_lat', 'toilet_long', 'borehole_id', 
            'borehole_type', 'distance_m', 'surviving_fio_load'
        ])
    
    # Filter toilets with valid FIO loads to reduce computation
    valid_toilets = toilets_df[
        (toilets_df['fio_load'].notna()) & (toilets_df['fio_load'] > 0)
    ].copy()
    
    if valid_toilets.empty:
        logging.warning("No toilets with valid FIO loads")
        return pd.DataFrame(columns=[
            'toilet_id', 'toilet_lat', 'toilet_long', 'borehole_id', 
            'borehole_type', 'distance_m', 'surviving_fio_load'
        ])
    
    logging.info(f"Processing {len(valid_toilets)} toilets with valid FIO loads")
    
    links = []
    processed = 0
    
    # Use vectorized approach: compute all distances in batches to save memory
    batch_size = 1000  # Process toilets in batches
    
    for i in range(0, len(valid_toilets), batch_size):
        batch_toilets = valid_toilets.iloc[i:i+batch_size]
        
        for _, toilet in batch_toilets.iterrows():
            # Calculate distances to all boreholes vectorized
            distances = haversine_m(
                toilet['lat'], toilet['long'],
                bores_df['lat'].values, bores_df['long'].values
            )
            
            # Find boreholes within radius
            within_radius_mask = distances <= radius_m
            
            if np.any(within_radius_mask):
                # Get nearby boreholes and their distances
                nearby_borehole_indices = np.where(within_radius_mask)[0]
                nearby_distances = distances[within_radius_mask]
                
                # Create links for all nearby boreholes
                for idx, distance in zip(nearby_borehole_indices, nearby_distances):
                    borehole = bores_df.iloc[idx]
                    
                    # Calculate surviving FIO load using Layer 2 formula
                    surviving_load = toilet['fio_load'] * np.exp(-ks_per_m * distance)
                    
                    links.append({
                        'toilet_id': toilet['id'],
                        'toilet_lat': toilet['lat'],
                        'toilet_long': toilet['long'],
                        'borehole_id': borehole['id'],
                        'borehole_type': borehole_type,
                        'distance_m': distance,
                        'surviving_fio_load': surviving_load
                    })
            
            processed += 1
            if processed % 5000 == 0:
                logging.info(f"Processed {processed}/{len(valid_toilets)} toilets...")
    
    if not links:
        logging.warning(f"No links found for {borehole_type} boreholes within {radius_m}m radius")
        return pd.DataFrame(columns=[
            'toilet_id', 'toilet_lat', 'toilet_long', 'borehole_id', 
            'borehole_type', 'distance_m', 'surviving_fio_load'
        ])
    
    links_df = pd.DataFrame(links)
    logging.info(f"Created {len(links_df)} links to {borehole_type} boreholes")
    
    return links_df


def pick_Q_L_per_day(df: pd.DataFrame, flow_prefs: List[str]) -> pd.Series:
    """
    Infer flow rate (Q) in L/day from available columns using preference order.
    
    Args:
        df: DataFrame with potential flow columns
        flow_prefs: List of column names in preference order
        
    Returns:
        Series of Q values in L/day
    """
    Q_series = pd.Series(index=df.index, dtype=float)
    
    for col_name in flow_prefs:
        if col_name in df.columns:
            # Get non-null values for this column
            valid_mask = df[col_name].notna() & Q_series.isna()
            valid_values = pd.to_numeric(df[col_name], errors='coerce')
            
            if valid_mask.any():
                # Apply unit conversions based on column name
                if 'Lps' in col_name or 'L/s' in col_name:
                    # Convert L/s to L/day
                    Q_series.loc[valid_mask] = valid_values.loc[valid_mask] * 86400
                    logging.info(f"Used {col_name} (L/s -> L/day conversion) for {valid_mask.sum()} records")
                elif 'm3' in col_name or 'M3' in col_name:
                    # Convert m³/day to L/day  
                    Q_series.loc[valid_mask] = valid_values.loc[valid_mask] * 1000
                    logging.info(f"Used {col_name} (m³/day -> L/day conversion) for {valid_mask.sum()} records")
                else:
                    # Assume already in L/day
                    Q_series.loc[valid_mask] = valid_values.loc[valid_mask]
                    logging.info(f"Used {col_name} (L/day) for {valid_mask.sum()} records")
    
    return Q_series


def build_borehole_Q_map(
    df: pd.DataFrame, 
    borehole_type: str, 
    defaults_by_type: Dict[str, float]
) -> pd.DataFrame:
    """
    Build Q (flow rate) map for boreholes with defaults for missing values.
    
    Args:
        df: Borehole DataFrame
        borehole_type: Type identifier  
        defaults_by_type: Default Q values by borehole type
        
    Returns:
        DataFrame with columns: id, borehole_type, Q_L_per_day
    """
    # Infer Q from available columns
    Q_series = pick_Q_L_per_day(df, config.FLOW_PREFERENCE_ORDER)
    
    # Fill missing Q with defaults
    default_Q = defaults_by_type.get(borehole_type, 2000.0)
    Q_series = Q_series.fillna(default_Q)
    
    filled_count = Q_series.isna().sum()
    if filled_count > 0:
        logging.info(f"Filled {filled_count} missing Q values with default {default_Q} L/day for {borehole_type}")
    
    # Create Q map DataFrame
    Q_map = pd.DataFrame({
        'id': df['id'],
        'borehole_type': borehole_type,
        'Q_L_per_day': Q_series
    })
    
    return Q_map


def compute_borehole_concentrations(
    links_df: pd.DataFrame, 
    bh_q_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute borehole concentrations and save concentration outputs.
    
    Implements Layer 3: concentration_CFU_per_L = surviving_fio_load / Q_L_per_day
    
    Args:
        links_df: DataFrame with toilet-borehole links
        bh_q_df: DataFrame with borehole Q values
        
    Returns:
        Tuple of (concentration_links_df, borehole_concentrations_df)
    """
    if links_df.empty:
        logging.warning("No links provided - creating empty concentration outputs")
        
        # Create empty outputs with correct columns
        empty_links = pd.DataFrame(columns=[
            'toilet_id', 'toilet_lat', 'toilet_long', 'borehole_id', 
            'borehole_type', 'distance_m', 'surviving_fio_load', 'Q_L_per_day', 'concentration_CFU_per_L'
        ])
        
        empty_boreholes = pd.DataFrame(columns=[
            'borehole_id', 'borehole_type', 'total_surviving_fio_load', 'Q_L_per_day', 'concentration_CFU_per_L'
        ])
        
        # Save empty files
        empty_links.to_csv(config.NET_SURVIVING_PATHOGEN_CONCENTRATION_LINKS_PATH, index=False)
        empty_boreholes.to_csv(config.FIO_CONCENTRATION_AT_BOREHOLES_PATH, index=False)
        
        return empty_links, empty_boreholes
    
    # Join links with Q data - using suffixes to handle duplicate columns
    links_with_Q = links_df.merge(
        bh_q_df, 
        left_on='borehole_id', 
        right_on='id', 
        how='left',
        suffixes=('', '_q')
    )
    
    # Drop the duplicate borehole_type column from Q data if it exists
    if 'borehole_type_q' in links_with_Q.columns:
        links_with_Q = links_with_Q.drop('borehole_type_q', axis=1)
    
    # Calculate concentration per link (Layer 3)
    links_with_Q['concentration_CFU_per_L'] = (
        links_with_Q['surviving_fio_load'] / links_with_Q['Q_L_per_day']
    )
    
    # Aggregate by borehole
    borehole_agg = links_with_Q.groupby('borehole_id').agg({
        'borehole_type': 'first',
        'surviving_fio_load': 'sum',  # Total load to borehole
        'Q_L_per_day': 'first'        # Q should be consistent per borehole
    }).reset_index()
    
    # Calculate aggregate concentration per borehole
    borehole_agg['concentration_CFU_per_L'] = (
        borehole_agg['surviving_fio_load'] / borehole_agg['Q_L_per_day']
    )
    
    # Rename columns for output
    borehole_agg = borehole_agg.rename(columns={
        'surviving_fio_load': 'total_surviving_fio_load'
    })
    
    # Select columns for link output
    link_output_cols = [
        'toilet_id', 'toilet_lat', 'toilet_long', 'borehole_id', 
        'borehole_type', 'distance_m', 'surviving_fio_load', 'Q_L_per_day', 'concentration_CFU_per_L'
    ]
    links_output = links_with_Q[link_output_cols].copy()
    
    # Save outputs
    links_output.to_csv(config.NET_SURVIVING_PATHOGEN_CONCENTRATION_LINKS_PATH, index=False)
    borehole_agg.to_csv(config.FIO_CONCENTRATION_AT_BOREHOLES_PATH, index=False)
    
    logging.info(f"Saved concentration links to {config.NET_SURVIVING_PATHOGEN_CONCENTRATION_LINKS_PATH} ({len(links_output)} links)")
    logging.info(f"Saved borehole concentrations to {config.FIO_CONCENTRATION_AT_BOREHOLES_PATH} ({len(borehole_agg)} boreholes)")
    
    return links_output, borehole_agg