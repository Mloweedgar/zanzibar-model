"""Data loading functions for the BEST-Z dashboard."""

import streamlit as st
import pandas as pd
import geopandas as gpd
import tempfile
import io
from pathlib import Path
from . import config, preprocess, ingest, n_load

@st.cache_data
def load_default_data():
    """
    Load and preprocess default data.
    
    Returns:
        tuple: (pop_df, wards_gdf, toilet_types_df)
    """
    # Load data
    hh = preprocess.clean_households()
    pop = preprocess.group_population(hh)
    pop = preprocess.add_removal_efficiency(pop)
    wards_gdf = ingest.read_geojson(config.DATA_RAW / 'unguja_wards.geojson')
    
    # Create toilet types reference for better UX
    toilet_types_df = pd.DataFrame([
        {'toilet_type_id': '1', 'toilet_type': 'Flush to sewer', 'system_category': 'septic_tank_sewer'},
        {'toilet_type_id': '2', 'toilet_type': 'Flush to septic tank', 'system_category': 'septic_tank'},
        {'toilet_type_id': '3', 'toilet_type': 'Flush to pit', 'system_category': 'septic_tank'},
        {'toilet_type_id': '4', 'toilet_type': 'VIP', 'system_category': 'septic_tank'},
        {'toilet_type_id': '5', 'toilet_type': 'Ventilated Improved Pit', 'system_category': 'septic_tank'},
        {'toilet_type_id': '6', 'toilet_type': 'Pit latrine with washable slab', 'system_category': 'septic_tank'},
        {'toilet_type_id': '7', 'toilet_type': 'Traditional latrine', 'system_category': 'septic_tank'},
        {'toilet_type_id': '8', 'toilet_type': 'Pit latrine with not-washable/soil slab', 'system_category': 'septic_tank'},
        {'toilet_type_id': '9', 'toilet_type': 'Pit latrine without slab/open pit', 'system_category': 'septic_tank'},
        {'toilet_type_id': '10', 'toilet_type': 'Bucket', 'system_category': 'septic_tank'},
        {'toilet_type_id': '11', 'toilet_type': 'No facility/bush/field/beach', 'system_category': 'septic_tank'}
    ])
    
    return pop, wards_gdf, toilet_types_df


@st.cache_data
def load_base_data():
    """
    Load and preprocess base data (cached for performance).
    
    Returns:
        tuple: (pop_df, wards_gdf, toilet_types_df)
    """
    return load_default_data()


def get_data_summary(census_df, sanitation_df, wards_gdf):
    """
    Get summary statistics for data.
    
    Args:
        census_df: Census dataframe
        sanitation_df: Sanitation efficiency dataframe  
        wards_gdf: Wards geodataframe
        
    Returns:
        dict: Summary statistics
    """
    summary = {
        'census_rows': len(census_df),
        'unique_wards': census_df['ward_name'].nunique(),
        'sanitation_types': len(sanitation_df),
        'ward_boundaries': len(wards_gdf),
        'population': census_df.groupby(['ward_name', 'TOILET']).size().sum()
    }
    
    return summary 