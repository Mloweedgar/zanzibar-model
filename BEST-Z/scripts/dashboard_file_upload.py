"""File upload handling functions for the BEST-Z dashboard."""

import streamlit as st
import pandas as pd
import geopandas as gpd
import io
from .dashboard_validation import validate_all_uploaded_files, get_validation_summary
from .dashboard_data_loader import get_sample_data_for_download, get_data_summary
from .dashboard_ui_components import (
    create_file_upload_widgets,
    create_data_summary_expander,
    create_template_download_section,
    create_data_requirements_expander
)


def handle_file_upload_section():
    """
    Handle the complete file upload section including validation and processing.
    
    Returns:
        bool: True if uploaded files are valid and ready to use, False otherwise
    """
    # Create upload widgets
    census_file, sanitation_file, geojson_file = create_file_upload_widgets()
    
    # Validate and process uploaded files
    use_uploaded = False
    
    if census_file and sanitation_file and geojson_file:
        use_uploaded = process_uploaded_files(census_file, sanitation_file, geojson_file)
    elif census_file or sanitation_file or geojson_file:
        st.sidebar.warning("⚠️ Please upload all three required files")
    else:
        show_upload_help_section()
    
    return use_uploaded


def process_uploaded_files(census_file, sanitation_file, geojson_file):
    """
    Process and validate uploaded files.
    
    Args:
        census_file: Uploaded census CSV file
        sanitation_file: Uploaded sanitation CSV file
        geojson_file: Uploaded GeoJSON file
        
    Returns:
        bool: True if all files are valid, False otherwise
    """
    try:
        # Read and validate files
        census_df = pd.read_csv(census_file)
        sanitation_df = pd.read_csv(sanitation_file)
        geojson_str = geojson_file.read().decode('utf-8')
        wards_gdf = gpd.read_file(io.StringIO(geojson_str))
        
        # Validate data
        validation_results = validate_all_uploaded_files(census_df, sanitation_df, wards_gdf)
        validation_summary = get_validation_summary(validation_results)
        
        if validation_summary['all_valid']:
            # Store uploaded files in session state
            st.session_state.uploaded_files = {
                'census': census_file.getvalue(),
                'sanitation': sanitation_file.getvalue(),
                'geojson': geojson_file.getvalue()
            }
            
            st.sidebar.success("✅ All files uploaded and validated successfully!")
            
            # Show data summary
            summary = get_data_summary(census_df, sanitation_df, wards_gdf)
            create_data_summary_expander(summary)
            
            return True
        else:
            # Show validation errors
            display_validation_errors(validation_summary['errors'])
            return False
            
    except Exception as e:
        st.sidebar.error(f"❌ Error processing files: {str(e)}")
        return False


def display_validation_errors(errors):
    """Display validation errors in the sidebar."""
    for error in errors:
        st.sidebar.error(f"❌ {error}")


def show_upload_help_section():
    """Show help section with file requirements and templates when no files are uploaded."""
    st.sidebar.info("📤 Upload all three data files to use custom data")
    
    # Show data format requirements
    create_data_requirements_expander()
    
    # Download template files section
    sample_census, sample_sanitation, sample_geojson = get_sample_data_for_download()
    create_template_download_section(sample_census, sample_sanitation, sample_geojson)


def clear_uploaded_files():
    """Clear uploaded files from session state."""
    if 'uploaded_files' in st.session_state:
        del st.session_state.uploaded_files


def has_uploaded_files():
    """Check if there are uploaded files in session state."""
    return 'uploaded_files' in st.session_state and st.session_state.uploaded_files 