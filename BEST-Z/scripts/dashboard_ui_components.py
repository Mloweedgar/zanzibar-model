"""UI components for the BEST-Z Interactive Dashboard."""

import streamlit as st
import pandas as pd
from . import config
from .dashboard_constants import SYSTEM_CATEGORY_NAMES

# Upload-related functions removed as upload functionality is no longer supported


# Upload-related UI functions removed as upload functionality is no longer supported


def create_fio_efficiency_sliders():
    """Create FIO removal efficiency sliders (car dashboard style)."""
    st.sidebar.markdown("**🚽 Treatment Efficiency**")
    
    fio_overrides = {}
    
    # Sewer connections
    sewer_eff = st.sidebar.slider(
        "Sewer Treatment",
        min_value=0,
        max_value=95,
        value=55,  # Display as percentage
        step=5,
        format="%d%%"
    )
    fio_overrides['SewerConnection'] = sewer_eff / 100.0  # Convert to decimal for calculations
    
    # Septic tanks
    septic_eff = st.sidebar.slider(
        "Septic Tanks", 
        min_value=0,
        max_value=80,
        value=20,  # Display as percentage
        step=5,
        format="%d%%"
    )
    fio_overrides['SepticTank'] = septic_eff / 100.0  # Convert to decimal for calculations
    
    # Pit latrines
    pit_eff = st.sidebar.slider(
        "Pit Latrines",
        min_value=0, 
        max_value=60,
        value=20,  # Display as percentage
        step=5,
        format="%d%%"
    )
    fio_overrides['PitLatrine'] = pit_eff / 100.0  # Convert to decimal for calculations
    
    # Open defecation (always 0%)
    fio_overrides['None'] = 0.0
    
    return fio_overrides


def create_time_slider():
    """Create time slider for crisis progression (car dashboard style)."""
    st.sidebar.markdown("**📅 Year**")
    
    year = st.sidebar.slider(
        "Select Year",
        min_value=2025,
        max_value=2050, 
        value=2025,
        step=5
    )
    
    # Convert year to population factor based on projections
    if year == 2025:
        pop_factor = 1.0
        status = "🟡"
    elif year <= 2030:
        pop_factor = 1.25
        status = "🟠" 
    else:  # 2050
        pop_factor = 2.48
        status = "🔴"
    
    # Simple visual indicator
    st.sidebar.markdown(f"{status} **{year}**: {pop_factor:.1f}x load")
    
    return year, pop_factor


def create_crisis_metrics():
    """Create clean crisis metrics (car dashboard style)."""
    real_data = config.REAL_WORLD_CONTAMINATION
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        eu_limit = real_data['eu_bathing_water_enterococci_limit']
        actual = real_data['africa_house_enterococci']
        times_over = actual / eu_limit
        st.metric("🏖️ Beaches", f"{times_over:.0f}x OVER")
    
    with col2:
        st.metric("🚰 Outfalls", f"{real_data['untreated_outfalls_count']}")
    
    with col3:
        discharge = real_data['daily_untreated_discharge_m3']
        st.metric("💧 Daily", f"{discharge/1000:.0f}K m³")
    
    with col4:
        current_ww = config.WASTEWATER_PROJECTIONS['2025']
        future_ww = config.WASTEWATER_PROJECTIONS['2050']
        growth = future_ww / current_ww
        st.metric("📈 2050", f"{growth:.1f}x")


def create_population_slider():
    """Population factor slider."""
    return st.sidebar.slider(
        "Population Factor",
        min_value=0.5,
        max_value=3.0,
        value=1.0,
        step=0.1
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


def create_economic_impact_section():
    """Create section showing economic costs of contamination crisis."""
    from . import config
    
    st.subheader("💰 Economic Impact of Contamination Crisis")
    
    real_data = config.REAL_WORLD_CONTAMINATION
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.error("**🏖️ TOURISM LOSSES**")
        # Zanzibar tourism contributes ~$500M annually
        tourism_value = 500_000_000  # USD
        at_risk_percent = 30  # Conservative estimate for contaminated areas
        potential_loss = tourism_value * (at_risk_percent / 100)
        
        st.metric(
            "Tourism Revenue at Risk",
            f"${potential_loss/1_000_000:.0f}M",
            f"From ${tourism_value/1_000_000:.0f}M total",
            help="Contaminated beaches threaten 30% of tourism revenue"
        )
        
        # Beach closures
        eu_violations = real_data['africa_house_enterococci'] / real_data['eu_bathing_water_enterococci_limit']
        st.metric(
            "Beach Safety Violations",
            f"{eu_violations:.0f}x",
            "EU Standards",
            help="Stone Town beaches would be closed in EU countries"
        )
    
    with col2:
        st.warning("**🏥 HEALTH COSTS**")
        # Diarrheal disease costs
        population_at_risk = real_data['total_zanzibar_population_2022'] * 0.82  # 82% without proper sanitation
        annual_cases_per_1000 = 200  # Conservative estimate for contaminated water diseases
        cost_per_case = 50  # USD treatment cost
        
        annual_health_cost = (population_at_risk * annual_cases_per_1000 / 1000 * cost_per_case)
        
        st.metric(
            "Annual Health Costs",
            f"${annual_health_cost/1_000_000:.1f}M",
            "Waterborne diseases",
            help=f"Treatment costs for ~{annual_cases_per_1000} cases per 1,000 people annually"
        )
        
        st.metric(
            "People at Risk",
            f"{population_at_risk/1_000_000:.1f}M",
            "No proper sanitation",
            help="Population without access to proper sanitation systems"
        )
    
    with col3:
        st.info("**🔄 INFRASTRUCTURE COSTS**")
        # Based on report projections
        current_ww = config.WASTEWATER_PROJECTIONS['2025']
        future_ww = config.WASTEWATER_PROJECTIONS['2050']
        
        # Cost estimates for treatment infrastructure
        cost_per_m3_treatment = 2000  # USD capital cost per m³/day capacity
        treatment_cost = future_ww * cost_per_m3_treatment
        
        st.metric(
            "Treatment Infrastructure",
            f"${treatment_cost/1_000_000:.0f}M",
            "Capital investment needed",
            help=f"To treat {future_ww:,} m³/day by 2050"
        )
        
        # Cost of inaction
        annual_damage = potential_loss + annual_health_cost
        st.metric(
            "Annual Cost of Inaction",
            f"${annual_damage/1_000_000:.0f}M",
            "Per year",
            help="Combined tourism and health costs annually"
        )

    # Economic message
    st.warning(f"""
    💡 **ECONOMIC REALITY:** The contamination crisis costs Zanzibar **${annual_damage/1_000_000:.0f}M annually** in lost tourism and health costs. 
    While treating all wastewater requires **${treatment_cost/1_000_000:.0f}M capital investment**, the return on investment is clear: 
    **every $1 spent on sanitation saves $5 in economic losses**.
    """)


def create_crisis_dashboard():
    """Create a high-impact crisis dashboard showing the scale of contamination problem."""
    from . import config
    
    st.markdown("### 🚨 ZANZIBAR CONTAMINATION CRISIS - AT A GLANCE")
    
    real_data = config.REAL_WORLD_CONTAMINATION
    
    # Top row - Most shocking statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        eu_limit = real_data['eu_bathing_water_enterococci_limit'] 
        actual_level = real_data['africa_house_enterococci']
        times_over = actual_level / eu_limit
        st.metric(
            "🏖️ Beach Safety",
            f"{times_over:.0f}x UNSAFE",
            "vs EU Standards",
            delta_color="inverse",
            help=f"Stone Town beaches: {actual_level:,} CFU vs EU limit {eu_limit} CFU"
        )
    
    with col2:
        outfalls = real_data['untreated_outfalls_count']
        st.metric(
            "🚰 Untreated Outfalls",
            f"{outfalls}",
            "Direct to Ocean",
            delta_color="inverse", 
            help="27 pipes dumping raw sewage into Indian Ocean"
        )
    
    with col3:
        daily_discharge = real_data['daily_untreated_discharge_m3']
        st.metric(
            "💧 Daily Sewage Discharge", 
            f"{daily_discharge:,} m³",
            "Per Day (Untreated)",
            delta_color="inverse",
            help="From just 3 major outfalls - total is much higher"
        )
    
    with col4:
        current_ww = config.WASTEWATER_PROJECTIONS['2025']
        future_ww = config.WASTEWATER_PROJECTIONS['2050']
        growth = ((future_ww - current_ww) / current_ww) * 100
        st.metric(
            "📈 Crisis Growth",
            f"+{growth:.0f}%",
            "by 2050",
            delta_color="inverse",
            help=f"Wastewater will grow from {current_ww:,} to {future_ww:,} m³/day"
        )

    # Bottom row - Context and scale
    col1, col2, col3 = st.columns(3)
    
    with col1:
        port_contamination = real_data['stone_town_port_total_coliform']
        st.metric(
            "🦠 Port Contamination",
            f"{port_contamination:,}",
            "CFU Total Coliform",
            help="Extremely dangerous bacterial levels where tourists and fishers work"
        )
    
    with col2:
        coverage = real_data['sewer_coverage_percent']
        st.metric(
            "🏘️ Proper Treatment",
            f"{coverage}%",
            "Population Covered",
            help="Only 18% connected to sewers (which discharge untreated anyway!)"
        )
    
    with col3:
        population = real_data['total_zanzibar_population_2022']
        at_risk = population * (100 - coverage) / 100
        st.metric(
            "👥 People at Risk",
            f"{at_risk:,.0f}",
            "No Proper Sanitation", 
            help=f"Out of {population:,} total population (2022 census)"
        )

    # Critical alert message
    st.error("""
    ⚠️ **CRISIS SUMMARY**: Zanzibar's tourism economy and public health face an unprecedented contamination crisis. 
    Stone Town beaches are **87x more contaminated** than EU safety standards, while **1.5 million people** lack proper sanitation. 
    Without immediate action, wastewater volumes will **nearly triple by 2050**.
    """)


def create_pathogen_key_insights(total_fio, total_open_fio, wards_with_od, total_wards):
    """Create key insights section for pathogen analysis."""
    from . import config
    
    contamination_percent = (total_open_fio/total_fio*100) if total_fio > 0 else 0
    real_data = config.REAL_WORLD_CONTAMINATION
    
    # Create three columns for dashboard-style metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.error("🚨 **CRISIS SCALE**")
        st.metric(
            "Untreated Ocean Discharge", 
            f"{real_data['daily_untreated_discharge_m3']:,} m³/day",
            help="From just 3 major outfalls in Stone Town (27 total outfalls exist)"
        )
        st.metric(
            "Sewer Coverage", 
            f"{real_data['sewer_coverage_percent']}%",
            help="Only 18% of urban population connected to sewers (and these discharge untreated!)"
        )
    
    with col2:
        st.warning("🏖️ **TOURISM IMPACT**") 
        eu_limit = real_data['eu_bathing_water_enterococci_limit']
        stone_town_level = real_data['africa_house_enterococci']
        times_over_limit = stone_town_level / eu_limit
        
        st.metric(
            "Stone Town Beach Contamination",
            f"{times_over_limit:.0f}x OVER",
            f"EU Safe Bathing Limit",
            help=f"Enterococci: {stone_town_level:,} CFU vs EU limit of {eu_limit} CFU"
        )
        st.metric(
            "Port Area Contamination",
            f"{real_data['stone_town_port_total_coliform']:,} CFU",
            help="Total coliform levels - extremely dangerous for human contact"
        )
    
    with col3:
        st.info("📈 **GROWING CRISIS**")
        current_ww = config.WASTEWATER_PROJECTIONS['2025']
        future_ww = config.WASTEWATER_PROJECTIONS['2050'] 
        growth_factor = future_ww / current_ww
        
        st.metric(
            "Wastewater by 2050",
            f"{growth_factor:.1f}x MORE",
            f"Current: {current_ww:,} m³/day",
            help=f"Will grow from {current_ww:,} to {future_ww:,} m³/day without intervention"
        )
        st.metric(
            "Open Defecation",
            f"{real_data['open_defecation_percent']}%",
            help="Current prevalence - direct pathogen contamination to environment"
        )

    # Critical message for decision makers
    st.error(f"""
    🎯 **DECISION MAKER ALERT:** Stone Town's beaches exceed EU safe bathing standards by **{times_over_limit:.0f}x**. 
    With wastewater volumes growing **{growth_factor:.1f}x** by 2050, this contamination crisis threatens both public health and Zanzibar's $500M+ tourism economy.
    """)
    
    # Additional context
    st.info(f"""
    **Model Results Context:** Your analysis shows **{contamination_percent:.0f}%** of pathogen contamination comes from open defecation 
    across **{wards_with_od}** wards, but the real-world measurements above reveal the total scale of contamination from all sources.
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


def create_data_export_section(gdf, pop_factor, tab_type="nitrogen"):
    """Export data (car dashboard style)."""
    st.subheader("📁 Export")
    
    if tab_type == "nitrogen":
        if st.button("Download CSV", key=f"{tab_type}_csv"):
            export_df = gdf.drop(columns=['geometry']).copy()
            export_df['ward_total_n_load_tonnes'] = export_df['ward_total_n_load_kg'] / 1000
            
            csv = export_df.to_csv(index=False)
            st.download_button(
                label="⬇️ CSV",
                data=csv,
                file_name=f"nitrogen_loads_{pop_factor:.1f}x.csv",
                mime="text/csv",
                key=f"{tab_type}_download_csv"
            )
    else:  # pathogen tab
        if st.button("Download CSV", key=f"{tab_type}_csv"):
            export_df = gdf.drop(columns=['geometry']).copy()
            
            csv = export_df.to_csv(index=False)
            st.download_button(
                label="⬇️ CSV",
                data=csv,
                file_name=f"pathogen_loads.csv",
                mime="text/csv",
                key=f"{tab_type}_download_csv"
            )
    
    # Clean stats only
    if tab_type == "nitrogen":
        total_load = gdf['ward_total_n_load_kg'].sum() / 1000
        st.caption(f"Total: {total_load:.1f} tonnes/year | Factor: {pop_factor:.1f}x | Wards: {len(gdf)}")
    else:
        total_fio = gdf['ward_total_fio_cfu_day'].sum()
        st.caption(f"Total: {total_fio:.1e} CFU/day | Wards: {len(gdf)}")


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