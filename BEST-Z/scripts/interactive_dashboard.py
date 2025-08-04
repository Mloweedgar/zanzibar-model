"""Interactive BEST-Z Model Dashboard using Streamlit - Refactored Version."""

import streamlit as st

from . import config, fio_load, preprocess
from .dashboard_constants import PAGE_CONFIG
from .dashboard_data_loader import load_base_data
from .dashboard_ui_components import (
    create_open_defecation_intervention_slider,
    create_sanitation_upgrade_slider,
    create_centralized_treatment_slider,
    create_fecal_sludge_treatment_slider,
    create_year_slider,
    create_population_growth_slider,
    initialize_session_state,
    format_large_number
)
from .dashboard_maps import create_contamination_map, create_fio_map

# Page configuration
st.set_page_config(**PAGE_CONFIG)


def render_pathogen_tab(pop_df, year, pop_factor, fio_overrides, od_reduction, infrastructure_upgrade, centralized_treatment, fecal_sludge_treatment):
    """Render the pathogen analysis - MAP FOCUSED."""
    
    # Create dynamic scenario based on user inputs
    if year <= 2025:
        scenario_key = 'crisis_2025_current'
    elif year <= 2030:
        scenario_key = 'crisis_2030_no_action'
    else:  # 2035, 2040, 2045, 2050
        scenario_key = 'crisis_2050_catastrophic'
    
    dynamic_scenario = config.FIO_SCENARIOS[scenario_key].copy()
    # Override with actual population factor for precise years
    dynamic_scenario['pop_factor'] = pop_factor
    dynamic_scenario['fio_removal_override'] = fio_overrides
    dynamic_scenario['od_reduction_percent'] = od_reduction
    dynamic_scenario['infrastructure_upgrade_percent'] = infrastructure_upgrade
    dynamic_scenario['centralized_treatment_percent'] = centralized_treatment
    dynamic_scenario['fecal_sludge_treatment_percent'] = fecal_sludge_treatment
    
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
    
    # Add problem scale and intervention context to description
    context_parts = []
    
    # Problem scale context
    if year > 2025:
        context_parts.append(f"Year {year}")
    if pop_factor > 1.0:
        context_parts.append(f"{pop_factor:.1f}x population")
    
    # Intervention context
    interventions_active = []
    if od_reduction > 0:
        interventions_active.append(f"OD: {od_reduction}% eliminated")
    if infrastructure_upgrade > 0:
        interventions_active.append(f"Infrastructure: {infrastructure_upgrade}% upgraded")
    if centralized_treatment > 0:
        interventions_active.append(f"Wastewater treatment: {centralized_treatment}% built")
    if fecal_sludge_treatment > 0:
        interventions_active.append(f"FSM facilities: {fecal_sludge_treatment}% built")
    
    if interventions_active:
        context_parts.append("Interventions: " + ", ".join(interventions_active))
    
    # Build final description
    if context_parts:
        context_text = " | ".join(context_parts)
        description = f"{base_description} | {context_text}"
    else:
        description = base_description
    
    # Display with appropriate styling based on problem scale
    if year >= 2040 or pop_factor >= 2.0:
        st.error(description)  # Red for severe scenarios
    elif year >= 2030 or pop_factor >= 1.5:
        st.warning(description)  # Yellow for moderate scenarios
    else:
        st.info(description)  # Blue for current/mild scenarios
    
    # LARGE, CLEAN MAP DISPLAY
    st.components.v1.html(fio_map._repr_html_(), height=700)
    
    # Simple key insight below map with scenario context
    if "Overall contamination" in map_story:
        total_contamination = fio_gdf['ward_total_fio_cfu_day'].sum()
        highest_ward = fio_gdf.loc[fio_gdf['ward_total_fio_cfu_day'].idxmax(), 'ward_name']
        total_formatted = format_large_number(total_contamination)
        
        # Add scenario context
        scenario_emoji = "💡" if year == 2025 and pop_factor == 1.0 else "📈" if year <= 2030 and pop_factor < 1.5 else "🚨"
        st.caption(f"{scenario_emoji} **Island total:** {total_formatted} CFU daily | **Highest ward:** {highest_ward}")
    else:  # Open defecation
        avg_od_percent = fio_gdf['open_share_percent'].mean()
        wards_with_od = (fio_gdf['open_share_percent'] > 0).sum()
        
        # Add scenario context
        scenario_emoji = "💡" if year == 2025 and pop_factor == 1.0 else "📈" if year <= 2030 and pop_factor < 1.5 else "🚨"
        st.caption(f"{scenario_emoji} **Island average:** {avg_od_percent:.1f}% open defecation | **Wards affected:** {wards_with_od}")


def main():
    """Main dashboard application - MAP FOCUSED."""
    st.title("BEST-Z Model Dashboard")
    st.markdown("*Interactive pathogen analysis*")
    
    initialize_session_state()
    
    with st.spinner("Loading data..."):
        pop_df, _, _ = load_base_data()
    
    # Sidebar - organized into problem scale and interventions
    
    # Problem Scale Section
    st.sidebar.header("📊 Problem Scale")
    year = create_year_slider()
    pop_factor = create_population_growth_slider()
    
    # Interventions Section  
    st.sidebar.header("🎯 Interventions")
    od_reduction = create_open_defecation_intervention_slider()
    infrastructure_upgrade = create_sanitation_upgrade_slider()
    centralized_treatment = create_centralized_treatment_slider()
    fecal_sludge_treatment = create_fecal_sludge_treatment_slider()
    
    # Use defaults for removed manual controls
    fio_overrides = {}  # Use default efficiencies
    
    # Main area - pure map focus
    render_pathogen_tab(pop_df, year, pop_factor, fio_overrides, od_reduction, infrastructure_upgrade, centralized_treatment, fecal_sludge_treatment)


if __name__ == "__main__":
    main() 