"""Interactive BEST-Z Model Dashboard using Streamlit - Refactored Version."""

import streamlit as st

from . import config, fio_load, preprocess
from .dashboard_constants import PAGE_CONFIG
from .dashboard_data_loader import load_base_data
from .dashboard_ui_components import (
    create_time_slider,
    create_fio_efficiency_sliders,
    create_open_defecation_intervention_slider,
    initialize_session_state,
    format_large_number
)
from .dashboard_maps import create_contamination_map, create_fio_map

# Page configuration
st.set_page_config(**PAGE_CONFIG)


def render_pathogen_tab(pop_df, year, pop_factor, fio_overrides, od_reduction):
    """Render the pathogen analysis - MAP FOCUSED."""
    
    # Create dynamic scenario based on user inputs
    scenario_key = 'crisis_2025_current' if year <= 2025 else 'crisis_2030_no_action' if year <= 2030 else 'crisis_2050_catastrophic'
    dynamic_scenario = config.FIO_SCENARIOS[scenario_key].copy()
    dynamic_scenario['fio_removal_override'] = fio_overrides
    dynamic_scenario['od_reduction_percent'] = od_reduction
    
    with st.spinner("Loading..."):
        fio_ward_data = fio_load.apply_scenario(pop_df, dynamic_scenario)
        fio_ward_agg = fio_load.aggregate_ward(fio_ward_data)
        fio_gdf = preprocess.attach_geometry(fio_ward_agg)
    
    st.subheader("🗺️ Zanzibar Pathogen Analysis")
    
    # Simple map selection
    map_story = st.selectbox(
        "What story do you want to see?",
        [
            "Overall contamination levels",
            "Open defecation impact"
        ]
    )
    
    # Generate simple, powerful map
    with st.spinner("Loading map..."):
        if "Overall contamination" in map_story:
            fio_map = create_fio_map(fio_gdf, 'ward_total_fio_cfu_day', 'Total Contamination (CFU/day)', 'YlOrRd')
            base_description = "**Total daily pathogen load per ward** - Combined contamination from all sources"
            
        else:  # Open defecation
            fio_map = create_fio_map(fio_gdf, 'open_share_percent', 'Open Defecation Share (%)', 'Reds')
            base_description = "**Open defecation impact** - Areas with highest  risk from open defecation"
    
    # Add intervention context to description
    if od_reduction > 0:
        intervention_text = f" | 🚨 **{od_reduction}% intervention active** - Watch contamination decrease!"
        description = base_description + intervention_text
    else:
        description = base_description
    
    # Display description with intervention context
    st.info(description)
    
    # LARGE, CLEAN MAP DISPLAY
    st.components.v1.html(fio_map._repr_html_(), height=700)
    
    # One key insight below map
    if "Overall contamination" in map_story:
        total_contamination = fio_gdf['ward_total_fio_cfu_day'].sum()
        highest_ward = fio_gdf.loc[fio_gdf['ward_total_fio_cfu_day'].idxmax(), 'ward_name']
        total_formatted = format_large_number(total_contamination)
        st.caption(f"💡 **Island total:** {total_formatted} CFU daily | **Highest ward:** {highest_ward}")
    else:  # Open defecation
        avg_od_percent = fio_gdf['open_share_percent'].mean()
        wards_with_od = (fio_gdf['open_share_percent'] > 0).sum()
        st.caption(f"💡 **Island average:** {avg_od_percent:.1f}% open defecation | **Wards affected:** {wards_with_od}")


def main():
    """Main dashboard application - MAP FOCUSED."""
    st.title("🗺️ Zanzibar Contamination Map")
    st.markdown("*Interactive pathogen analysis*")
    
    initialize_session_state()
    
    with st.spinner("Loading data..."):
        pop_df, _, _ = load_base_data()
    
    # Sidebar - clean controls only
    st.sidebar.header("⚙️ Map Controls")
    
    # Most impactful control first
    od_reduction = create_open_defecation_intervention_slider()
    
    # Secondary controls
    year, pop_factor = create_time_slider()
    fio_overrides = create_fio_efficiency_sliders()
    
    # Main area - pure map focus
    render_pathogen_tab(pop_df, year, pop_factor, fio_overrides, od_reduction)


if __name__ == "__main__":
    main() 