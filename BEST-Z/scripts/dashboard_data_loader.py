"""Data loading and processing functions for the BEST-Z dashboard."""

import streamlit as st
import pandas as pd
import geopandas as gpd
import tempfile
import io
from pathlib import Path

# Handle imports for both direct execution and module execution
try:
    from . import config, ingest, preprocess
    from .dashboard_constants import SAMPLE_CENSUS_DATA, SAMPLE_SANITATION_DATA, SAMPLE_GEOJSON_DATA
except ImportError:
    # If relative imports fail, try absolute imports
    import sys
    from pathlib import Path
    
    # Add the BEST-Z directory to Python path
    best_z_dir = Path(__file__).parent.parent
    if str(best_z_dir) not in sys.path:
        sys.path.insert(0, str(best_z_dir))
    
    from scripts import config, ingest, preprocess
    from scripts.dashboard_constants import SAMPLE_CENSUS_DATA, SAMPLE_SANITATION_DATA, SAMPLE_GEOJSON_DATA


def save_uploaded_file(uploaded_file, target_path):
    """Save uploaded file to target path."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "wb") as f:
        f.write(uploaded_file.getbuffer())


def load_data_from_uploaded_files(uploaded_files):
    """
    Load and process data from uploaded files.
    
    Args:
        uploaded_files: Dictionary containing uploaded file contents
        
    Returns:
        tuple: (pop_df, wards_gdf, toilet_types_df)
    """
    # Load household data from uploaded census file
    census_df = pd.read_csv(io.StringIO(uploaded_files['census'].decode('utf-8')))
    
    # Create temporary files for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Save uploaded files to temp directory
        census_path = temp_dir / 'census.csv'
        sanitation_path = temp_dir / 'sanitation.csv'
        geojson_path = temp_dir / 'wards.geojson'
        
        census_df.to_csv(census_path, index=False)
        
        sanitation_df = pd.read_csv(io.StringIO(uploaded_files['sanitation'].decode('utf-8')))
        sanitation_df.to_csv(sanitation_path, index=False)
        
        # Handle GeoJSON
        geojson_str = uploaded_files['geojson'].decode('utf-8')
        with open(geojson_path, 'w') as f:
            f.write(geojson_str)
        
        # Temporarily update config paths
        original_data_raw = config.DATA_RAW
        config.DATA_RAW = temp_dir
        
        try:
            # Process data using existing functions
            hh = preprocess.clean_households_from_path(census_path)
            pop = preprocess.group_population(hh)
            pop = preprocess.add_removal_efficiency_from_path(pop, sanitation_path)
            wards_gdf = ingest.read_geojson(geojson_path)
            
            # Load toilet type names for better UX
            toilet_types_df = sanitation_df[['toilet_type_id', 'toilet_type', 'system_category']].copy()
            toilet_types_df['toilet_type_id'] = toilet_types_df['toilet_type_id'].astype(str).str.strip()
            
        finally:
            # Restore original config
            config.DATA_RAW = original_data_raw
    
    return pop, wards_gdf, toilet_types_df


def load_default_data():
    """
    Load data from default files.
    
    Returns:
        tuple: (pop_df, wards_gdf, toilet_types_df)
    """
    # Load household data
    hh = preprocess.clean_households()
    
    # Group population by ward and toilet type
    pop = preprocess.group_population(hh)
    
    # Add removal efficiency data
    pop = preprocess.add_removal_efficiency(pop)
    
    # Load ward geometry
    wards_gdf = ingest.read_geojson(config.DATA_RAW / 'unguja_wards.geojson')
    
    # Load toilet type names for better UX
    toilet_types_df = ingest.read_csv(config.DATA_RAW / 'sanitation_removal_efficiencies_Zanzibar.csv')
    toilet_types_df = toilet_types_df[['toilet_type_id', 'toilet_type', 'system_category']].copy()
    toilet_types_df['toilet_type_id'] = toilet_types_df['toilet_type_id'].astype(str).str.strip()
    
    return pop, wards_gdf, toilet_types_df


@st.cache_data
def load_base_data(use_uploaded=False):
    """
    Load and preprocess base data (cached for performance).
    
    Args:
        use_uploaded: Whether to use uploaded files or default data
        
    Returns:
        tuple: (pop_df, wards_gdf, toilet_types_df)
    """
    if use_uploaded and 'uploaded_files' in st.session_state:
        return load_data_from_uploaded_files(st.session_state.uploaded_files)
    else:
        return load_default_data()


def get_sample_data_for_download():
    """
    Get sample template data for download.
    
    Returns:
        tuple: (census_df, sanitation_df, geojson_dict)
    """
    # Create sample dataframes
    sample_census = pd.DataFrame(SAMPLE_CENSUS_DATA)
    sample_sanitation = pd.DataFrame(SAMPLE_SANITATION_DATA)
    sample_geojson = SAMPLE_GEOJSON_DATA
    
    return sample_census, sample_sanitation, sample_geojson


def get_data_summary(census_df, sanitation_df, wards_gdf):
    """
    Get summary statistics for uploaded data.
    
    Args:
        census_df: Census dataframe
        sanitation_df: Sanitation dataframe
        wards_gdf: Ward boundaries geodataframe
        
    Returns:
        dict: Summary statistics
    """
    return {
        'census_records': len(census_df),
        'toilet_types': len(sanitation_df),
        'wards_geojson': len(wards_gdf),
        'unique_wards_census': census_df['ward_name'].nunique()
    } 