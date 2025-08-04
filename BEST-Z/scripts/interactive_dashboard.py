"""Interactive BEST-Z Model Dashboard using Streamlit - Refactored Version."""

import streamlit as st

from . import config, fio_load, preprocess
from .dashboard_constants import PAGE_CONFIG
from .dashboard_data_loader import load_base_data
from .dashboard_ui_components import (
    create_time_slider,
    create_fio_efficiency_sliders,
    initialize_session_state
)
from .dashboard_maps import create_contamination_map, create_fio_map

# Page configuration
st.set_page_config(**PAGE_CONFIG)


def render_pathogen_tab(pop_df, year, pop_factor, fio_overrides):
    """Render the pathogen analysis - MAP FOCUSED."""
    
    # Create dynamic scenario based on user inputs
    scenario_key = 'crisis_2025_current' if year <= 2025 else 'crisis_2030_no_action' if year <= 2030 else 'crisis_2050_catastrophic'
    dynamic_scenario = config.FIO_SCENARIOS[scenario_key].copy()
    dynamic_scenario['fio_removal_override'] = fio_overrides
    
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
            "Open defecation impact", 
            "Population pressure areas",
            "Future growth (2030)"
        ]
    )
    
    # Generate simple, powerful map
    with st.spinner("Loading map..."):
        if "Overall contamination" in map_story:
            fio_map = create_fio_map(fio_gdf, 'ward_total_fio_cfu_day', 'Total Contamination (CFU/day)', 'YlOrRd')
            description = "**Total daily pathogen load per ward** - Combined contamination from all sources"
            
        elif "Open defecation" in map_story:
            fio_map = create_fio_map(fio_gdf, 'open_share_percent', 'Open Defecation Share (%)', 'Reds')
            description = "**Open defecation impact** - Areas with highest disease risk from open defecation"
            
        elif "Population pressure" in map_story:
            fio_map = create_fio_map(fio_gdf, 'ward_total_population', 'Population per Ward', 'Blues')
            description = "**Population pressure** - Where population density amplifies contamination impact"
            
        else:  # Future growth
            # Calculate 2030 projection data
            future_scenario = dynamic_scenario.copy()
            future_scenario['pop_factor'] = 1.25
            future_fio_data = fio_load.apply_scenario(pop_df, future_scenario)
            future_fio_agg = fio_load.aggregate_ward(future_fio_data)
            future_gdf = preprocess.attach_geometry(future_fio_agg)
            
            # Show growth projection
            growth_gdf = fio_gdf.copy()
            growth_gdf['contamination_growth'] = ((future_gdf['ward_total_fio_cfu_day'] - fio_gdf['ward_total_fio_cfu_day']) / fio_gdf['ward_total_fio_cfu_day'] * 100).fillna(0)
            fio_map = create_fio_map(growth_gdf, 'contamination_growth', 'Contamination Growth by 2030 (%)', 'Oranges')
            description = "**Future growth projection** - Where contamination will increase most by 2030 without intervention"
    
    # Display simple description
    st.info(description)
    
    # LARGE, CLEAN MAP DISPLAY
    st.components.v1.html(fio_map._repr_html_(), height=700)
    
    # One key insight below map
    if "Overall contamination" in map_story:
        total_contamination = fio_gdf['ward_total_fio_cfu_day'].sum()
        highest_ward = fio_gdf.loc[fio_gdf['ward_total_fio_cfu_day'].idxmax(), 'ward_name']
        st.caption(f"💡 **Island total:** {total_contamination:.1e} CFU daily | **Highest ward:** {highest_ward}")
    elif "Open defecation" in map_story:
        avg_od_percent = fio_gdf['open_share_percent'].mean()
        wards_with_od = (fio_gdf['open_share_percent'] > 0).sum()
        st.caption(f"💡 **Island average:** {avg_od_percent:.1f}% open defecation | **Wards affected:** {wards_with_od}")
    elif "Population pressure" in map_story:
        total_population = fio_gdf['ward_total_population'].sum()
        most_populated = fio_gdf.loc[fio_gdf['ward_total_population'].idxmax(), 'ward_name']
        st.caption(f"💡 **Island population:** {total_population:,} people | **Largest ward:** {most_populated}")
    else:  # Future growth
        avg_growth = growth_gdf['contamination_growth'].mean()
        highest_growth_ward = growth_gdf.loc[growth_gdf['contamination_growth'].idxmax(), 'ward_name']
        st.caption(f"💡 **Average growth:** +{avg_growth:.1f}% by 2030 | **Fastest growing:** {highest_growth_ward}")


def main():
    """Main dashboard application - MAP FOCUSED."""
    st.title("🗺️ Zanzibar Contamination Map")
    st.markdown("*Interactive pathogen analysis*")
    
    initialize_session_state()
    
    with st.spinner("Loading data..."):
        pop_df, _, _ = load_base_data()
    
    # Sidebar - clean controls only
    st.sidebar.header("⚙️ Map Controls")
    year, pop_factor = create_time_slider()
    fio_overrides = create_fio_efficiency_sliders()
    
    # Main area - pure map focus
    render_pathogen_tab(pop_df, year, pop_factor, fio_overrides)


if __name__ == "__main__":
    main() 