import pandas as pd
import numpy as np
import logging
from app import config

def parse_concentration(val):
    """
    Parse concentration values from government data.
    Handles:
    - "Numerous" -> 1000 (High cap)
    - "<1" -> 0
    - Numeric strings -> float
    - NaN/Empty -> NaN
    """
    if pd.isna(val):
        return np.nan
    
    val_str = str(val).strip().lower()
    
    if val_str == 'numerous':
        return 1000.0
    if '<' in val_str:
        return 0.0
    if val_str in ['nil', 'none', '-']:
        return 0.0
        
    try:
        return float(val_str)
    except ValueError:
        return np.nan

def load_government_data():
    """
    Load and clean government borehole data.
    Returns DataFrame with:
    - lat, long
    - e_coli_obs (Observed E. coli)
    - nitrate_obs (Observed Nitrate)
    """
    path = config.GOVERNMENT_BOREHOLES_PATH
    if not path.exists():
        logging.warning(f"Government data not found at {path}")
        return pd.DataFrame()
        
    try:
        df = pd.read_csv(path)
        
        # Strip whitespace from column names
        df.columns = df.columns.str.strip()
        
        # Standardize columns
        # Map: 'Total Coli' -> fio_obs (User requested switch from E. coli)
        df['fio_obs'] = df['Total Coli'].apply(parse_concentration)
        df['nitrate_obs'] = df['Nitrate (N'].apply(parse_concentration)
        
        # Ensure coordinates are numeric
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['long'] = pd.to_numeric(df['long'], errors='coerce')
        
        # Drop invalid rows
        df = df.dropna(subset=['lat', 'long'])
        
        logging.info(f"Loaded {len(df)} government boreholes")
        return df
        
    except Exception as e:
        logging.error(f"Error loading government data: {e}")
        return pd.DataFrame()
