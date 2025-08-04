"""Interactive BEST-Z Model Dashboard using Streamlit - Refactored Version."""

import streamlit as st

from . import config, fio_load, preprocess
from .dashboard_constants import PAGE_CONFIG
from .dashboard_data_loader import load_base_data
from .dashboard_ui_components import (
    create_time_slider,
    create_fio_efficiency_sliders,
    create_open_defecation_intervention_slider,
    create_sanitation_upgrade_slider,
    initialize_session_state,
    format_large_number
)
from .dashboard_maps import create_contamination_map, create_fio_map

# Page configuration
st.set_page_config(**PAGE_CONFIG)


def render_pathogen_tab(pop_df, year, pop_factor, fio_overrides, od_reduction, infrastructure_upgrade):
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
    
    # Add intervention and time context to description
    context_parts = []
    
    if od_reduction > 0:
        context_parts.append(f"🚨 **{od_reduction}% OD intervention active** - Watch contamination decrease!")
    
    if infrastructure_upgrade > 0:
        context_parts.append(f"🏗️ **{infrastructure_upgrade}% infrastructure upgraded** - Pit latrines → Septic tanks!")
    
    if year > 2025:
        if year == 2030:
            time_context = f"📅 **{year}**: +25% population growth - Crisis intensifying!"
        elif year == 2035:
            time_context = f"📅 **{year}**: +55% population growth - Major crisis developing!"
        elif year == 2040:
            time_context = f"📅 **{year}**: Nearly double population - Severe contamination crisis!"
        elif year == 2045:
            time_context = f"📅 **{year}**: 2.2x population - **CRITICAL CONTAMINATION DISASTER!**"
        else:  # 2050
            time_context = f"📅 **{year}**: 2.5x population - **CATASTROPHIC CONTAMINATION CRISIS!**"
        context_parts.append(time_context)
    
    # Build final description
    if context_parts:
        description = base_description + " | " + " | ".join(context_parts)
    else:
        description = base_description
    
    # Display description with dynamic context
    if year >= 2045:
        st.error(description)  # Red alert for catastrophic crisis years
    elif year >= 2040:
        st.error(description)  # Red alert for severe crisis years  
    elif year >= 2030:
        st.warning(description)  # Yellow warning for growing crisis
    else:
        st.info(description)  # Blue info for current state
    
    # LARGE, CLEAN MAP DISPLAY
    st.components.v1.html(fio_map._repr_html_(), height=700)
    
    # One key insight below map with crisis context
    if "Overall contamination" in map_story:
        total_contamination = fio_gdf['ward_total_fio_cfu_day'].sum()
        highest_ward = fio_gdf.loc[fio_gdf['ward_total_fio_cfu_day'].idxmax(), 'ward_name']
        total_formatted = format_large_number(total_contamination)
        
        # Add dramatic crisis context
        if year > 2025:
            baseline_factor = 1.0  # 2025 baseline
            increase_factor = pop_factor - baseline_factor
            increase_percent = increase_factor * 100
            crisis_emoji = "📈" if year <= 2030 else "🚨" if year <= 2035 else "🆘" if year <= 2040 else "💀" if year <= 2045 else "☠️"
            st.caption(f"{crisis_emoji} **Island total:** {total_formatted} CFU daily ({increase_percent:+.0f}% vs 2025) | **Highest ward:** {highest_ward}")
        else:
            st.caption(f"💡 **Island total:** {total_formatted} CFU daily | **Highest ward:** {highest_ward}")
    else:  # Open defecation
        avg_od_percent = fio_gdf['open_share_percent'].mean()
        wards_with_od = (fio_gdf['open_share_percent'] > 0).sum()
        
        # Add time context for open defecation impact
        if year > 2025:
            crisis_emoji = "📈" if year <= 2030 else "🚨" if year <= 2035 else "🆘" if year <= 2040 else "💀" if year <= 2045 else "☠️"
            st.caption(f"{crisis_emoji} **Island average:** {avg_od_percent:.1f}% open defecation ({pop_factor:.1f}x population) | **Wards affected:** {wards_with_od}")
        else:
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
    
    # Most impactful interventions first
    od_reduction = create_open_defecation_intervention_slider()
    infrastructure_upgrade = create_sanitation_upgrade_slider()
    
    # Secondary controls
    year, pop_factor = create_time_slider()
    fio_overrides = create_fio_efficiency_sliders()
    
    # Main area - pure map focus
    render_pathogen_tab(pop_df, year, pop_factor, fio_overrides, od_reduction, infrastructure_upgrade)


if __name__ == "__main__":
    main() 