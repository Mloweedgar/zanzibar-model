"""Data validation functions for the BEST-Z dashboard."""

import pandas as pd
import geopandas as gpd
from .dashboard_constants import (
    CENSUS_REQUIRED_COLUMNS,
    SANITATION_REQUIRED_COLUMNS, 
    GEOJSON_REQUIRED_COLUMNS
)


def validate_required_columns(df, required_columns, data_type_name):
    """
    Generic function to validate that a dataframe has required columns.
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        data_type_name: Name of data type for error messages
        
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        return False, f"Missing required columns in {data_type_name}: {missing_cols}"
    return True, "Valid"


def validate_census_data(df):
    """
    Validate census data has required columns.
    
    Args:
        df: Census dataframe to validate
        
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    return validate_required_columns(df, CENSUS_REQUIRED_COLUMNS, "census data")


def validate_sanitation_data(df):
    """
    Validate sanitation efficiency data has required columns.
    
    Args:
        df: Sanitation dataframe to validate
        
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    return validate_required_columns(df, SANITATION_REQUIRED_COLUMNS, "sanitation data")


def validate_geojson_data(gdf):
    """
    Validate GeoJSON has required columns and geometry.
    
    Args:
        gdf: GeoDataFrame to validate
        
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    if 'geometry' not in gdf.columns:
        return False, "Missing geometry column"
    
    return validate_required_columns(gdf, GEOJSON_REQUIRED_COLUMNS, "GeoJSON data")


def validate_all_uploaded_files(census_df, sanitation_df, geojson_gdf):
    """
    Validate all uploaded files at once.
    
    Args:
        census_df: Census dataframe
        sanitation_df: Sanitation dataframe  
        geojson_gdf: Ward boundaries geodataframe
        
    Returns:
        dict: Dictionary with validation results for each file type
    """
    results = {
        'census': validate_census_data(census_df),
        'sanitation': validate_sanitation_data(sanitation_df),
        'geojson': validate_geojson_data(geojson_gdf)
    }
    
    # Check if all are valid
    all_valid = all(result[0] for result in results.values())
    results['all_valid'] = all_valid
    
    return results


def get_validation_summary(validation_results):
    """
    Get a summary of validation results for display.
    
    Args:
        validation_results: Results from validate_all_uploaded_files
        
    Returns:
        dict: Summary information for display
    """
    summary = {
        'all_valid': validation_results['all_valid'],
        'errors': []
    }
    
    for file_type, (is_valid, message) in validation_results.items():
        if file_type != 'all_valid' and not is_valid:
            summary['errors'].append(f"{file_type.title()}: {message}")
    
    return summary 