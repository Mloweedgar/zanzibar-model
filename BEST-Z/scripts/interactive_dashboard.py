"""Interactive BEST-Z Model Dashboard using Streamlit - Refactored Version."""

import streamlit as st
import numpy as np
import logging

# Handle imports for both direct execution and module execution
try:
    from . import config, n_load, fio_load, preprocess
    from .dashboard_constants import PAGE_CONFIG
    from .dashboard_data_loader import load_base_data
    from .dashboard_ui_components import (
        create_time_slider,
        create_crisis_metrics,
        create_fio_efficiency_sliders,
        create_data_export_section,
        initialize_session_state
    )
    from .dashboard_maps import create_nitrogen_map, create_contamination_map
except ImportError:
    # If relative imports fail, try absolute imports
    import sys
    from pathlib import Path
    
    # Add the BEST-Z directory to Python path
    best_z_dir = Path(__file__).parent.parent
    if str(best_z_dir) not in sys.path:
        sys.path.insert(0, str(best_z_dir))
    
    from scripts import config, n_load, fio_load, preprocess
    from scripts.dashboard_constants import PAGE_CONFIG
    from scripts.dashboard_data_loader import load_base_data
    from scripts.dashboard_ui_components import (
        create_time_slider,
        create_crisis_metrics,
        create_fio_efficiency_sliders,
        create_data_export_section,
        initialize_session_state
    )
    from scripts.dashboard_maps import create_nitrogen_map, create_contamination_map

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Page configuration
st.set_page_config(**PAGE_CONFIG)


def calculate_nitrogen_scenario(pop_df, pop_factor, nre_overrides):
    """Calculate nitrogen loads for given parameters."""
    scenario = {
        'pop_factor': pop_factor,
        'nre_override': nre_overrides
    }
    
    # Apply scenario
    scenario_df = n_load.apply_scenario(pop_df, scenario)
    
    # Aggregate to ward level
    ward_df = n_load.aggregate_ward(scenario_df)
    
    # Attach geometry
    gdf = preprocess.attach_geometry(ward_df)
    
    return gdf


def render_pathogen_tab(pop_df, year, pop_factor, fio_overrides):
    """Render the pathogen analysis tab (car dashboard style)."""
    st.header("🦠 Pathogen Load")
    
    # Create dynamic scenario based on user inputs
    scenario_key = 'crisis_2025_current' if year <= 2025 else 'crisis_2030_no_action' if year <= 2030 else 'crisis_2050_catastrophic'
    dynamic_scenario = config.FIO_SCENARIOS[scenario_key].copy()
    dynamic_scenario['fio_removal_override'] = fio_overrides
    
    # Debug: Show current efficiency values (can remove later)
    with st.expander("Current Treatment Efficiencies", expanded=False):
        for sanitation_type, efficiency in fio_overrides.items():
            st.write(f"{sanitation_type}: {efficiency:.0%}")
    
    # Force recalculation when sliders change
    cache_key = f"{year}_{hash(str(sorted(fio_overrides.items())))}"
    
    with st.spinner("Loading..."):
        fio_ward_data = fio_load.apply_scenario(pop_df, dynamic_scenario)
        fio_ward_agg = fio_load.aggregate_ward(fio_ward_data)
        fio_gdf = preprocess.attach_geometry(fio_ward_agg)
        
        od_top_wards = fio_gdf.nlargest(10, 'ward_open_fio_cfu_day')[
            ['ward_name', 'ward_open_fio_cfu_day', 'open_share_percent', 'ward_total_population']
        ].copy()
    
    # Simple metrics
    total_fio = fio_gdf['ward_total_fio_cfu_day'].sum()
    total_open_fio = fio_gdf['ward_open_fio_cfu_day'].sum()
    wards_with_od = (fio_gdf['ward_open_fio_cfu_day'] > 0).sum()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Daily Load", f"{total_fio:.1e}")
    with col2:
        contamination_pct = (total_open_fio/total_fio*100) if total_fio > 0 else 0
        st.metric("From Open Defecation", f"{contamination_pct:.0f}%")
    with col3:
        st.metric("Wards at Risk", f"{wards_with_od}")
    
    # Map stories
    st.subheader("🗺️ Contamination Map")
    
    map_story = st.selectbox(
        "View:",
        [
            "Disease hot-spots",
            "Overall contamination", 
            "Priority areas"
        ]
    )
    
    with st.spinner("Loading map..."):
        fio_map, description = create_contamination_map(fio_gdf, f"Show me the {map_story.lower()}")
        
    st.components.v1.html(fio_map._repr_html_(), height=600)
    
    # Simple intervention
    st.subheader("💡 Impact")
    od_reduction = st.slider("Open defecation reduction %", 0, 100, 50, 10)
    
    if od_reduction > 0:
        scenario_with_reduction = dynamic_scenario.copy()
        scenario_with_reduction['od_reduction_percent'] = float(od_reduction)
        
        with st.spinner("Calculating..."):
            scenario_fio_data = fio_load.apply_scenario(pop_df, scenario_with_reduction)
            scenario_fio_agg = fio_load.aggregate_ward(scenario_fio_data)
            
            baseline_total_od = fio_gdf['ward_open_fio_cfu_day'].sum()
            scenario_total_od = scenario_fio_agg['ward_open_fio_cfu_day'].sum()
            reduction_achieved = baseline_total_od - scenario_total_od
            reduction_percent = (reduction_achieved / baseline_total_od * 100) if baseline_total_od > 0 else 0
        
        st.success(f"**{reduction_percent:.0f}%** contamination reduction")
    
    create_data_export_section(fio_gdf, pop_factor, "pathogen")


def render_nitrogen_tab(pop_df, pop_factor, nre_overrides):
    """Render the nitrogen analysis tab."""
    st.header("Nitrogen Load Analysis")
    
    # Calculate nitrogen scenario
    with st.spinner("Calculating nitrogen loads..."):
        n_gdf = calculate_nitrogen_scenario(pop_df, pop_factor, nre_overrides)
    
    # Display summary statistics
    # create_nitrogen_summary_metrics(n_gdf) # This line is removed as per the edit hint

    # Create and display map
    with st.spinner("Generating nitrogen map..."):
        n_map = create_nitrogen_map(n_gdf)
    
    # Display map
    st.subheader("Nitrogen Load Map")
    st.components.v1.html(n_map._repr_html_(), height=600)
    
    # Data export section
    create_data_export_section(n_gdf, pop_factor, "nitrogen")


def main():
    """Main dashboard application."""
    st.title("🌊 BEST-Z Dashboard")
    st.markdown("Zanzibar pathogen contamination analysis")
    
    initialize_session_state()
    
    # Load data
    with st.spinner("Loading..."):
        pop_df, wards_gdf, toilet_types_df = load_base_data()
    
    # Sidebar controls - car dashboard style
    st.sidebar.header("🎛️ Controls")
    
    # Time slider
    year, pop_factor = create_time_slider()
    
    # FIO removal efficiency sliders - these update the map in real-time
    fio_overrides = create_fio_efficiency_sliders()
    
    # Single tab - focus only on pathogens
    render_pathogen_tab(pop_df, year, pop_factor, fio_overrides)


if __name__ == "__main__":
    main() 