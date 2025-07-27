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
        create_preset_scenario_buttons,
        create_population_slider,
        create_efficiency_override_sliders,
        create_metrics_row,
        create_pathogen_key_insights,
        create_intervention_impact_section,
        create_priority_wards_table,
        create_nitrogen_summary_metrics,
        create_data_export_section,
        create_technical_note_expander,
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
        create_preset_scenario_buttons,
        create_population_slider,
        create_efficiency_override_sliders,
        create_metrics_row,
        create_pathogen_key_insights,
        create_intervention_impact_section,
        create_priority_wards_table,
        create_nitrogen_summary_metrics,
        create_data_export_section,
        create_technical_note_expander,
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


def render_pathogen_tab(pop_df):
    """Render the pathogen analysis tab."""
    st.header("🦠 Pathogen Contamination Analysis")
    st.markdown("*Understanding disease risk from sanitation practices*")
    
    # Calculate FIO scenario
    with st.spinner("Analyzing pathogen contamination..."):
        fio_ward_data = fio_load.apply_scenario(pop_df, config.FIO_SCENARIOS['baseline_2022'])
        fio_ward_agg = fio_load.aggregate_ward(fio_ward_data)
        fio_gdf = preprocess.attach_geometry(fio_ward_agg)
        
        # Get top contamination hot-spots
        od_top_wards = fio_gdf.nlargest(10, 'ward_open_fio_cfu_day')[
            ['ward_name', 'ward_open_fio_cfu_day', 'open_share_percent', 'ward_total_population']
        ].copy()
    
    # The Story: Public Health Impact
    st.subheader("🚨 The Public Health Challenge")
    
    total_fio = fio_gdf['ward_total_fio_cfu_day'].sum()
    total_open_fio = fio_gdf['ward_open_fio_cfu_day'].sum()
    wards_with_od = (fio_gdf['ward_open_fio_cfu_day'] > 0).sum()
    
    # Create metrics
    metrics = [
        ("Daily Pathogen Load", f"{total_fio:.1e} bacteria/day", "Total disease-causing bacteria released daily across Zanzibar"),
        ("From Open Defecation", f"{(total_open_fio/total_fio*100):.0f}%", "Percentage of contamination from open defecation (most dangerous)"),
        ("Wards at Risk", f"{wards_with_od} of {len(fio_gdf)}", "Wards with open defecation contamination")
    ]
    create_metrics_row(metrics)
    
    # Key message for decision makers  
    create_pathogen_key_insights(total_fio, total_open_fio, wards_with_od, len(fio_gdf))
    
    # Interactive Map Story
    st.subheader("🗺️ Where is the Contamination?")
    
    # Map selector with clear stories
    map_story = st.selectbox(
        "Select contamination story to explore:",
        [
            "Show me the disease hot-spots (Open Defecation)",
            "Show me overall contamination levels", 
            "Show me intervention priorities"
        ],
        help="Each view tells a different story about pathogen contamination risk"
    )
    
    # Create appropriate map based on story
    with st.spinner("Generating contamination map..."):
        fio_map, description = create_contamination_map(fio_gdf, map_story)
        st.markdown(description)
    
    # Display map
    st.components.v1.html(fio_map._repr_html_(), height=600)
    
    # Intervention Impact Modeling
    od_reduction = create_intervention_impact_section(fio_gdf, od_top_wards)
    
    if od_reduction > 0:
        # Calculate impact
        scenario_with_reduction = config.FIO_SCENARIOS['baseline_2022'].copy()
        scenario_with_reduction['od_reduction_percent'] = float(od_reduction)
        
        with st.spinner("Calculating health impact..."):
            scenario_fio_data = fio_load.apply_scenario(pop_df, scenario_with_reduction)
            scenario_fio_agg = fio_load.aggregate_ward(scenario_fio_data)
            
            baseline_total_od = fio_gdf['ward_open_fio_cfu_day'].sum()
            scenario_total_od = scenario_fio_agg['ward_open_fio_cfu_day'].sum()
            reduction_achieved = baseline_total_od - scenario_total_od
            reduction_percent = (reduction_achieved / baseline_total_od * 100) if baseline_total_od > 0 else 0
        
        # Show impact in relatable terms
        impact_metrics = [
            ("Contamination Reduced", f"{reduction_percent:.0f}%", "Reduction in dangerous pathogen contamination"),
            ("People Helped", f"~{od_top_wards['ward_total_population'].sum() * (od_reduction/100):,.0f}", "Estimated people who would benefit from improved sanitation"),
            ("Priority Wards", f"{len(od_top_wards[od_top_wards['open_share_percent'] > 20])}", "High-risk wards that need immediate attention")
        ]
        create_metrics_row(impact_metrics)
        
        st.success(f"""
        **Health Impact:** Converting {od_reduction}% of open defecation to basic toilets would reduce dangerous 
        pathogen contamination by **{reduction_percent:.0f}%**, directly protecting ~**{od_top_wards['ward_total_population'].sum() * (od_reduction/100):,.0f} people** 
        from water-borne diseases like cholera and diarrhea.
        """)
    
    # Priority Action Table
    create_priority_wards_table(od_top_wards)
    
    # Technical note
    create_technical_note_expander()


def render_nitrogen_tab(pop_df, pop_factor, nre_overrides):
    """Render the nitrogen analysis tab."""
    st.header("Nitrogen Load Analysis")
    
    # Calculate nitrogen scenario
    with st.spinner("Calculating nitrogen loads..."):
        n_gdf = calculate_nitrogen_scenario(pop_df, pop_factor, nre_overrides)
    
    # Display summary statistics
    create_nitrogen_summary_metrics(n_gdf)

    # Create and display map
    with st.spinner("Generating nitrogen map..."):
        n_map = create_nitrogen_map(n_gdf)
    
    # Display map
    st.subheader("Nitrogen Load Map")
    st.components.v1.html(n_map._repr_html_(), height=600)
    
    # Data export section
    create_data_export_section(n_gdf, pop_factor)


def main():
    """Main dashboard application."""
    st.title("🌊 BEST-Z Model Dashboard")
    st.markdown("Interactive tool for exploring nitrogen and pathogen load scenarios in Zanzibar")
    
    # Initialize session state
    initialize_session_state()
    
    # Load base data (always use default data)
    with st.spinner("Loading data..."):
        pop_df, wards_gdf, toilet_types_df = load_base_data()
    
    # Sidebar controls
    st.sidebar.header("🎛️ Scenario Parameters")
    
    # Preset scenario buttons
    preset_applied = create_preset_scenario_buttons()
    if preset_applied:
        st.session_state.preset_applied = preset_applied
    
    # Population growth factor
    pop_factor = create_population_slider()
    
    # Nitrogen removal efficiency overrides
    nre_overrides = create_efficiency_override_sliders(
        toilet_types_df, pop_df, st.session_state.get('preset_applied')
    )
    
    # Create simplified tabs - focus on key stories [[memory:4467168]]
    tab1, tab2 = st.tabs(["🦠 Pathogen Analysis", "🧪 Nitrogen Analysis"])
    
    with tab1:
        render_pathogen_tab(pop_df)
    
    with tab2:
        render_nitrogen_tab(pop_df, pop_factor, nre_overrides)


if __name__ == "__main__":
    main() 