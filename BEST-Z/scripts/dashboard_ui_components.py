"""UI components and helper functions for the BEST-Z dashboard."""

import streamlit as st
import pandas as pd
import json
from .dashboard_constants import (
    PRESET_SCENARIOS,
    SYSTEM_CATEGORY_NAMES
)


def create_sidebar_data_source_section():
    """Create the data source selection section in sidebar."""
    st.sidebar.header("📁 Data Source")
    data_source = st.sidebar.radio(
        "Choose data source:",
        ["Use Default Data", "Upload Custom Data"],
        help="Use default Zanzibar data or upload your own files"
    )
    return data_source


def create_data_requirements_expander():
    """Create expandable section showing data format requirements."""
    with st.sidebar.expander("📋 Required Data Formats"):
        st.markdown("""
        **Census Data (CSV):**
        - ward_name: Ward name
        - TOILET: Toilet type ID (1-11)
        - SEX: Gender (1=Male, 2=Female)
        - AGE: Age in years
        - H_INSTITUTION_TYPE: Institution type (use ' ' for households)
        
        **Sanitation Efficiency (CSV):**
        - toilet_type_id: Toilet type ID (1-11)
        - toilet_type: Toilet type name
        - system_category: System category
        - nitrogen_removal_efficiency: Efficiency (0-1)
        
        **Ward Boundaries (GeoJSON):**
        - ward_name: Ward name (must match census data)
        - geometry: Ward polygon geometry
        """)


def create_file_upload_widgets():
    """Create file upload widgets for custom data."""
    st.sidebar.subheader("Upload Data Files")
    
    census_file = st.sidebar.file_uploader(
        "Census Data (CSV)",
        type=['csv'],
        help="CSV file with columns: ward_name, TOILET, SEX, AGE, H_INSTITUTION_TYPE"
    )
    
    sanitation_file = st.sidebar.file_uploader(
        "Sanitation Efficiency Data (CSV)",
        type=['csv'],
        help="CSV file with columns: toilet_type_id, toilet_type, system_category, nitrogen_removal_efficiency"
    )
    
    geojson_file = st.sidebar.file_uploader(
        "Ward Boundaries (GeoJSON)",
        type=['geojson', 'json'],
        help="GeoJSON file with ward geometries and ward_name column"
    )
    
    return census_file, sanitation_file, geojson_file


def create_data_summary_expander(summary):
    """Create expandable data summary section."""
    with st.sidebar.expander("📊 Data Summary"):
        st.write(f"**Census records:** {summary['census_records']:,}")
        st.write(f"**Toilet types:** {summary['toilet_types']}")
        st.write(f"**Wards:** {summary['wards_geojson']}")
        st.write(f"**Unique wards in census:** {summary['unique_wards_census']}")


def create_template_download_section(sample_census, sample_sanitation, sample_geojson):
    """Create section for downloading template files."""
    if st.button("📥 Download Template Files"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                "Census Template",
                sample_census.to_csv(index=False),
                "census_template.csv",
                "text/csv"
            )
        
        with col2:
            st.download_button(
                "Sanitation Template",
                sample_sanitation.to_csv(index=False),
                "sanitation_template.csv",
                "text/csv"
            )
        
        with col3:
            st.download_button(
                "GeoJSON Template",
                json.dumps(sample_geojson, indent=2),
                "wards_template.geojson",
                "application/json"
            )


def create_preset_scenario_buttons():
    """Create preset scenario buttons and return the selected preset."""
    st.sidebar.subheader("Quick Presets")
    col1, col2, col3 = st.sidebar.columns(3)
    
    preset_applied = None
    
    if col1.button("Baseline 2022"):
        st.session_state.pop_factor = PRESET_SCENARIOS['baseline']['pop_factor']
        preset_applied = 'baseline'
    
    if col2.button("Improved Removal"):
        st.session_state.pop_factor = PRESET_SCENARIOS['improved']['pop_factor'] 
        preset_applied = 'improved'
    
    if col3.button("Pop Growth 2030"):
        st.session_state.pop_factor = PRESET_SCENARIOS['growth']['pop_factor']
        preset_applied = 'growth'
    
    return preset_applied


def create_population_slider():
    """Create population growth factor slider."""
    return st.sidebar.slider(
        "Population Growth Factor",
        min_value=0.5,
        max_value=2.0,
        value=st.session_state.get('pop_factor', 1.0),
        step=0.1,
        help="Multiplier for population (1.0 = current population, 1.2 = 20% growth)"
    )


def create_efficiency_override_sliders(toilet_types_df, pop_df, preset_applied):
    """Create nitrogen removal efficiency override sliders."""
    st.sidebar.subheader("Nitrogen Removal Efficiency Overrides")
    st.sidebar.markdown("*Adjust removal efficiency for toilet types*")
    
    # Group toilet types by system category
    system_categories = toilet_types_df['system_category'].unique()
    system_categories = sorted([cat for cat in system_categories if pd.notna(cat)])
    
    nre_overrides = {}
    
    # Create sliders for each system category
    for system_category in system_categories:
        overrides = create_single_efficiency_slider(
            system_category, toilet_types_df, pop_df, preset_applied
        )
        nre_overrides.update(overrides)
    
    return nre_overrides


def create_single_efficiency_slider(system_category, toilet_types_df, pop_df, preset_applied):
    """Create a single efficiency slider for a system category."""
    # Get toilet types in this system category
    category_toilets = toilet_types_df[toilet_types_df['system_category'] == system_category]
    
    # Get toilet type IDs that exist in our population data
    existing_toilet_ids = pop_df['toilet_type_id'].unique()
    category_toilet_ids = category_toilets['toilet_type_id'].astype(str).str.strip()
    relevant_toilet_ids = [tid for tid in category_toilet_ids if tid in existing_toilet_ids]
    
    if not relevant_toilet_ids:
        return {}
        
    # Get default efficiency
    first_toilet_id = relevant_toilet_ids[0]
    default_eff = pop_df[pop_df['toilet_type_id'] == first_toilet_id]['nitrogen_removal_efficiency'].iloc[0]
    if pd.isna(default_eff):
        default_eff = 0.0
    
    # Create help text
    help_text = create_efficiency_help_text(default_eff, relevant_toilet_ids, toilet_types_df)
    
    # Determine value based on preset
    slider_value = float(default_eff)
    if preset_applied == 'improved' and any(tid in ['1', '2', '3', '4'] for tid in relevant_toilet_ids):
        slider_value = 0.80
    
    # Get display label
    display_label = SYSTEM_CATEGORY_NAMES.get(
        system_category, 
        f"{system_category.replace('_', ' ').title()} Toilet Types"
    )
    
    # Create slider
    override_val = st.sidebar.slider(
        display_label,
        min_value=0.0,
        max_value=1.0,
        value=slider_value,
        step=0.05,
        format="%.2f",
        key=f"system_{system_category}",
        help=help_text
    )
    
    # Apply override to all toilet types in this category if different from default
    overrides = {}
    if abs(override_val - default_eff) > 0.001:
        for toilet_id in relevant_toilet_ids:
            overrides[str(toilet_id)] = override_val
    
    return overrides


def create_efficiency_help_text(default_eff, relevant_toilet_ids, toilet_types_df):
    """Create help text for efficiency sliders."""
    help_text_lines = [f"Default: {default_eff:.2f}", "Toilet types in this category:"]
    for toilet_id in relevant_toilet_ids:
        toilet_info = toilet_types_df[toilet_types_df['toilet_type_id'] == toilet_id]
        if not toilet_info.empty:
            toilet_name = toilet_info['toilet_type'].iloc[0]
            help_text_lines.append(f"• {toilet_name}")
    return "\n".join(help_text_lines)


def create_metrics_row(metrics_data):
    """Create a row of metrics with columns."""
    cols = st.columns(len(metrics_data))
    for i, (label, value, help_text) in enumerate(metrics_data):
        with cols[i]:
            if help_text:
                st.metric(label, value, help=help_text)
            else:
                st.metric(label, value)


def create_pathogen_key_insights(total_fio, total_open_fio, wards_with_od, total_wards):
    """Create key insights section for pathogen analysis."""
    contamination_percent = (total_open_fio/total_fio*100) if total_fio > 0 else 0
    
    st.info(f"""
    **Key Insight for Decision Makers:** Open defecation contributes **{contamination_percent:.0f}%** of pathogen contamination 
    while affecting **{wards_with_od}** wards. This creates direct disease transmission risks through contaminated groundwater and surface runoff.
    """)


def create_intervention_impact_section(fio_gdf, od_top_wards):
    """Create intervention impact modeling section."""
    st.subheader("💡 Intervention Impact: What if we build toilets?")
    
    od_reduction = st.slider(
        "If we convert X% of open defecation to basic toilets:",
        min_value=0,
        max_value=100,
        value=50,
        step=10,
        help="Model the health impact of providing basic sanitation"
    )
    
    return od_reduction


def create_priority_wards_table(od_top_wards):
    """Create table showing priority wards for intervention."""
    if not od_top_wards.empty and od_top_wards['ward_open_fio_cfu_day'].sum() > 0:
        st.subheader("🎯 Top Priority Wards for Immediate Action")
        
        # Create actionable summary
        display_df = od_top_wards.head(5).copy()  # Top 5 for focus
        display_df['ward_open_fio_cfu_day'] = display_df['ward_open_fio_cfu_day'].apply(lambda x: f"{x:.1e}")
        display_df['open_share_percent'] = display_df['open_share_percent'].apply(lambda x: f"{x:.0f}%")
        display_df['ward_total_population'] = display_df['ward_total_population'].apply(lambda x: f"{x:,}")
        display_df.columns = ['Ward Name', 'Disease Risk (pathogens/day)', 'Open Defecation (%)', 'Population at Risk']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.info("""
        **Recommended Action:** Focus sanitation interventions on these 5 wards first. 
        They have the highest pathogen contamination and would provide maximum health protection per investment.
        """)


def create_nitrogen_summary_metrics(n_gdf):
    """Create summary metrics for nitrogen analysis."""
    total_n_load = n_gdf['ward_total_n_load_kg'].sum() / 1000  # Convert to tonnes
    max_ward_load = n_gdf['ward_total_n_load_kg'].max() / 1000
    min_ward_load = n_gdf['ward_total_n_load_kg'].min() / 1000
    avg_ward_load = n_gdf['ward_total_n_load_kg'].mean() / 1000
    
    metrics = [
        ("Total N Load", f"{total_n_load:,.1f} t/year", None),
        ("Max Ward Load", f"{max_ward_load:,.1f} t/year", None),
        ("Min Ward Load", f"{min_ward_load:,.1f} t/year", None),
        ("Average Ward Load", f"{avg_ward_load:,.1f} t/year", None)
    ]
    
    create_metrics_row(metrics)


def create_data_export_section(n_gdf, pop_factor):
    """Create data export section with download buttons."""
    st.subheader("Data Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Download N Ward Data (CSV)", key="n_csv"):
            # Prepare data for export with both kg and tonnes
            export_df = n_gdf.drop(columns=['geometry']).copy()
            export_df['ward_total_n_load_tonnes'] = export_df['ward_total_n_load_kg'] / 1000
            csv = export_df.to_csv(index=False)
            st.download_button(
                label="Download N CSV",
                data=csv,
                file_name=f"nitrogen_load_scenario_{pop_factor}x_pop.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("Download N GeoJSON", key="n_geojson"):
            # Include both kg and tonnes in GeoJSON
            geojson_df = n_gdf[['ward_name', 'ward_total_n_load_kg', 'ward_total_n_load_tonnes', 'geometry']].copy()
            geojson = geojson_df.to_json()
            st.download_button(
                label="Download N GeoJSON",
                data=geojson,
                file_name=f"nitrogen_load_scenario_{pop_factor}x_pop.geojson",
                mime="application/json"
            )


def create_technical_note_expander():
    """Create expandable technical note section."""
    with st.expander("ℹ️ About Pathogen Measurements"):
        st.markdown("""
        - **Pathogens** = Disease-causing bacteria (E. coli, faecal coliforms)
        - **cfu/day** = Colony Forming Units per day (live bacteria released daily)
        - **Open defecation** contributes 100% of pathogens directly to environment
        - **Basic toilets** reduce contamination by ~20% through containment
        - **Risk areas** = High open defecation % + high population density
        """)


def initialize_session_state():
    """Initialize session state variables."""
    if 'pop_factor' not in st.session_state:
        st.session_state.pop_factor = 1.0
    if 'preset_applied' not in st.session_state:
        st.session_state.preset_applied = None 