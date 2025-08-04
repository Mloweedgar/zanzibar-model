"""Interactive BEST-Z Model Dashboard using Streamlit - Refactored Version."""

import streamlit as st

from . import config, fio_load, preprocess
from .dashboard_constants import PAGE_CONFIG
from .dashboard_data_loader import load_base_data
from .dashboard_ui_components import (
    create_time_slider,
    create_fio_efficiency_sliders,
    create_data_export_section,
    initialize_session_state
)
from .dashboard_maps import create_contamination_map

# Page configuration
st.set_page_config(**PAGE_CONFIG)


def render_pathogen_tab(pop_df, year, pop_factor, fio_overrides):
    """Render the pathogen analysis tab."""
    st.header("Pathogens Load")
    
    # Create dynamic scenario based on user inputs
    scenario_key = 'crisis_2025_current' if year <= 2025 else 'crisis_2030_no_action' if year <= 2030 else 'crisis_2050_catastrophic'
    dynamic_scenario = config.FIO_SCENARIOS[scenario_key].copy()
    dynamic_scenario['fio_removal_override'] = fio_overrides
    
    with st.spinner("Loading..."):
        fio_ward_data = fio_load.apply_scenario(pop_df, dynamic_scenario)
        fio_ward_agg = fio_load.aggregate_ward(fio_ward_data)
        fio_gdf = preprocess.attach_geometry(fio_ward_agg)
    
    # Simple metrics
    total_fio = fio_gdf['ward_total_fio_cfu_day'].sum()
    total_open_fio = fio_gdf['ward_open_fio_cfu_day'].sum()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Daily Load", f"{total_fio:.1e}")
    with col2:
        contamination_pct = (total_open_fio/total_fio*100) if total_fio > 0 else 0
        st.metric("From Open Defecation", f"{contamination_pct:.0f}%")
    with col3:
        st.metric("Wards at Risk", f"{(fio_gdf['ward_open_fio_cfu_day'] > 0).sum()}")
    
    # Map stories
    st.subheader("🗺️ Contamination Map")
    
    map_story = st.selectbox(
        "View Data By:",
        [
            "Concentration levels",
            "Total pathogen load", 
            "High-value areas"
        ]
    )
    
    with st.spinner("Loading map..."):
        fio_map, description = create_contamination_map(fio_gdf, f"Show me the {map_story.lower()}")
        
    # Display map (streamlit will auto-refresh when data changes)
    st.components.v1.html(fio_map._repr_html_(), height=600)
    
    # Multi-perspective analysis
    st.subheader("📊 Different Perspectives")
    
    perspective = st.radio(
        "View the same data through different lenses:",
        ["📈 Growth Trend", "🌍 Reference Standards", "🏭 Infrastructure Benchmark", "💰 Coverage Analysis"],
        horizontal=True
    )
    
    col1, col2 = st.columns(2)
    
    if perspective == "📈 Growth Trend":
        with col1:
            current_load = total_fio
            growth_2030 = current_load * 1.25  # From config
            st.metric("2025 Load", f"{current_load:.1e}", help="Current pathogen load")
        with col2:
            st.metric("2030 Projection", f"{growth_2030:.1e}", 
                     delta=f"+{((growth_2030-current_load)/current_load*100):.0f}%",
                     delta_color="inverse",
                     help="With current infrastructure")
                     
    elif perspective == "🌍 Reference Standards":
        # Use reference standards
        refs = config.REFERENCE_STANDARDS
        current_enterococci = config.REAL_WORLD_CONTAMINATION['africa_house_enterococci']
        
        # Show multiple reference points like a speedometer
        st.markdown("**Current Level: 8,748 CFU** | Reference Points:")
        
        ref_col1, ref_col2, ref_col3 = st.columns(3)
        with ref_col1:
            st.metric("EU Standard", f"{refs['eu_bathing_water_enterococci']} CFU", 
                     help="European bathing water directive")
        with ref_col2:
            st.metric("WHO Recreational", f"{refs['who_recreational_enterococci']} CFU", 
                     help="WHO recreational water guideline")
        with ref_col3:
            st.metric("US EPA Standard", f"{refs['us_epa_recreational_enterococci']} CFU", 
                     help="US Environmental Protection Agency")
                     
    elif perspective == "🏭 Infrastructure Benchmark":
        # Use reference standards  
        refs = config.REFERENCE_STANDARDS
        current_coverage = config.REAL_WORLD_CONTAMINATION['sewer_coverage_percent']
        
        # Show current vs reference points
        st.markdown(f"**Current Coverage: {current_coverage}%** | Reference Points:")
        
        inf_col1, inf_col2, inf_col3 = st.columns(3)
        with inf_col1:
            st.metric("African Urban Avg", f"{refs['africa_urban_sewer_average']}%", 
                     help="Typical African urban sewer coverage")
        with inf_col2:
            st.metric("WHO Basic Threshold", f"{refs['who_basic_sanitation_threshold']}%", 
                     help="WHO basic sanitation coverage")
        with inf_col3:
            st.metric("Middle Income Typical", f"{refs['middle_income_sewer_typical']}%", 
                     help="Typical middle-income country coverage")
                     
    else:  # Coverage Analysis
        with col1:
            high_concentration_wards = (fio_gdf['ward_open_fio_cfu_day'] > fio_gdf['ward_open_fio_cfu_day'].quantile(0.75)).sum()
            st.metric("High Concentration Wards", f"{high_concentration_wards}", help="Top 25% contamination levels")
        with col2:
            total_wards = len(fio_gdf)
            concentration_area = (high_concentration_wards / total_wards * 100)
            st.metric("Coverage Area", f"{concentration_area:.0f}%", 
                     help="Percentage of wards with highest levels")
    
    # Simple intervention
    st.subheader("💡 Impact")
    od_reduction = st.slider("Open defecation reduction %", 0, 100, 50, 10)
    
    if od_reduction > 0:
        scenario_with_reduction = dynamic_scenario.copy()
        scenario_with_reduction['od_reduction_percent'] = float(od_reduction)
        
        with st.spinner("Calculating..."):
            scenario_fio_data = fio_load.apply_scenario(pop_df, scenario_with_reduction)
            scenario_fio_agg = fio_load.aggregate_ward(scenario_fio_data)
            
            baseline_total_od = total_open_fio
            scenario_total_od = scenario_fio_agg['ward_open_fio_cfu_day'].sum()
            reduction_percent = ((baseline_total_od - scenario_total_od) / baseline_total_od * 100) if baseline_total_od > 0 else 0
        
        st.success(f"**{reduction_percent:.0f}%** contamination reduction")
    
    create_data_export_section(fio_gdf, pop_factor, "pathogen")


def main():
    """Main dashboard application."""
    st.title("🌊 BEST-Z Dashboard")
    st.markdown("Zanzibar pathogen contamination analysis")
    
    initialize_session_state()
    
    with st.spinner("Loading..."):
        pop_df, _, _ = load_base_data()
    
    st.sidebar.header("🎛️ Controls")
    year, pop_factor = create_time_slider()
    fio_overrides = create_fio_efficiency_sliders()
    
    render_pathogen_tab(pop_df, year, pop_factor, fio_overrides)


if __name__ == "__main__":
    main() 