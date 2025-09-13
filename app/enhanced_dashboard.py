"""Enhanced Streamlit dashboard with simple form-based UI for pathogen scenario modeling.

This dashboard provides a simplified user interface for building and running pathogen 
scenarios in alignment with World Bank TOR requirements for Zanzibar sanitation modeling.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import json
import datetime

import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import Fullscreen, HeatMap

# Support both package and script execution
try:
    from app import fio_config as config
    from app import fio_runner
except Exception:
    from . import fio_config as config
    from . import fio_runner


def set_page_config():
    """Configure the Streamlit page with appropriate settings."""
    st.set_page_config(
        page_title="Zanzibar Pathogen Model - World Bank",
        page_icon="🌊",
        layout="wide",
        initial_sidebar_state="expanded"
    )


def load_outputs() -> Dict[str, pd.DataFrame]:
    """Load output CSV files for visualization."""
    outputs = {}
    paths = {
        'hh_loads_markers': config.DASH_TOILETS_MARKERS_PATH,
        'hh_loads_heat': config.DASH_TOILETS_HEATMAP_PATH,
        'bh_conc': config.FIO_CONCENTRATION_AT_BOREHOLES_PATH,
        'priv_bh_dash': config.DASH_PRIVATE_BH_PATH,
        'gov_bh_dash': config.DASH_GOVERNMENT_BH_PATH,
    }
    
    for key, path in paths.items():
        if path.exists():
            try:
                outputs[key] = pd.read_csv(path)
            except Exception as e:
                st.warning(f"Could not load {key}: {e}")
                outputs[key] = pd.DataFrame()
        else:
            outputs[key] = pd.DataFrame()
    
    return outputs


def format_large_number(x) -> str:
    """Format large numbers for display."""
    try:
        if isinstance(x, str):
            s = x.strip().replace(',', '')
            x = float(s)
        if pd.isna(x):
            return "-"
        x = float(x)
        a = abs(x)
        if a >= 1e12: return f"{x/1e12:.1f}T"
        if a >= 1e9: return f"{x/1e9:.1f}B"
        if a >= 1e6: return f"{x/1e6:.1f}M"
        if a >= 1e3: return f"{x/1e3:.1f}K"
        return f"{x:.0f}"
    except Exception:
        return "-"


def create_scenario_form() -> Dict[str, Any]:
    """Create a simple form for scenario building."""
    st.sidebar.title("🌊 Zanzibar Pathogen Model")
    st.sidebar.markdown("**World Bank - Ocean Health & Sanitation Nexus**")
    
    with st.sidebar.expander("ℹ️ About this Model", expanded=False):
        st.markdown("""
        This model analyzes pathogen contamination from sanitation systems 
        to groundwater boreholes in Zanzibar, supporting the World Bank's 
        ocean health and sanitation nexus study.
        
        **Key Features:**
        - Household pathogen load calculation
        - Spatial transport modeling with decay
        - Borehole contamination concentration
        """)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Scenario Builder")
    
    # Scenario Template Selection
    scenario_names = list(config.SCENARIOS.keys())
    selected_template = st.sidebar.selectbox(
        "Base Scenario Template",
        options=scenario_names,
        index=scenario_names.index('calibrated_trend_baseline') if 'calibrated_trend_baseline' in scenario_names else 0,
        help="Choose a pre-configured scenario as starting point"
    )
    
    base_params = dict(config.SCENARIOS[selected_template])
    
    # Main Intervention Parameters
    st.sidebar.subheader("🚰 Sanitation Interventions")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        od_reduction = st.slider(
            "Open Defecation Reduction (%)",
            min_value=0, max_value=100,
            value=int(base_params.get('od_reduction_percent', 0)),
            help="% of open defecation practices converted to septic systems"
        )
    
    with col2:
        infrastructure_upgrade = st.slider(
            "Infrastructure Upgrade (%)",
            min_value=0, max_value=100,
            value=int(base_params.get('infrastructure_upgrade_percent', 0)),
            help="% of pit latrines upgraded to septic systems"
        )
    
    fecal_sludge_treatment = st.sidebar.slider(
        "Fecal Sludge Treatment (%)",
        min_value=0, max_value=100,
        value=int(base_params.get('fecal_sludge_treatment_percent', 0)),
        help="% of fecal sludge receiving proper treatment"
    )
    
    centralized_treatment = st.sidebar.checkbox(
        "Enable Centralized Treatment",
        value=bool(base_params.get('centralized_treatment_enabled', False)),
        help="Connect sewered systems to centralized treatment"
    )
    
    # Population and Environmental Parameters
    st.sidebar.subheader("🏘️ Population & Environment")
    
    population_factor = st.sidebar.slider(
        "Population Growth Factor",
        min_value=0.5, max_value=3.0,
        value=float(base_params.get('pop_factor', 1.0)),
        step=0.1,
        help="Multiplier for current population (1.0 = current, 1.5 = 50% growth)"
    )
    
    # Advanced Settings in Expander
    with st.sidebar.expander("⚙️ Advanced Settings", expanded=False):
        st.markdown("**Pathogen Parameters**")
        
        efio_override = st.text_input(
            "EFIO Override (CFU/person/day)",
            value=str(base_params.get('EFIO_override', '')),
            help="Leave blank for default (1.0e7). Override for sensitivity analysis."
        )
        
        spatial_decay = st.slider(
            "Spatial Decay Rate (1/m)",
            min_value=0.01, max_value=0.15,
            value=float(base_params.get('ks_per_m', config.KS_PER_M_DEFAULT)),
            step=0.01,
            format="%.3f",
            help="Rate of pathogen die-off with distance"
        )
        
        st.markdown("**Search Radii (meters)**")
        radius_params = base_params.get('radius_by_type', config.RADIUS_BY_TYPE_DEFAULT)
        
        col3, col4 = st.columns(2)
        with col3:
            private_radius = st.number_input(
                "Private Boreholes",
                min_value=10, max_value=500,
                value=int(radius_params.get('private', 35)),
                step=5
            )
        with col4:
            government_radius = st.number_input(
                "Government Boreholes", 
                min_value=10, max_value=1000,
                value=int(radius_params.get('government', 100)),
                step=10
            )
        
        st.markdown("**Containment Efficiencies**")
        eff_base = base_params.get('efficiency_override', config.CONTAINMENT_EFFICIENCY_DEFAULT)
        
        col5, col6 = st.columns(2)
        with col5:
            eff_sewered = st.slider("Sewered Systems", 0.0, 1.0, float(eff_base.get(1, 0.50)), 0.05)
            eff_septic = st.slider("Septic/Improved", 0.0, 1.0, float(eff_base.get(3, 0.30)), 0.05)
        with col6:
            eff_pit = st.slider("Basic Pit Latrines", 0.0, 1.0, float(eff_base.get(2, 0.10)), 0.05)
            eff_od = st.slider("Open Defecation", 0.0, 1.0, float(eff_base.get(4, 0.00)), 0.05)
    
    # Visualization Settings
    st.sidebar.subheader("🗺️ Map Settings")
    heatmap_radius = st.sidebar.slider(
        "Heatmap Radius",
        min_value=8, max_value=40,
        value=int(base_params.get('heatmap_radius', 18)),
        help="Radius for toilet load heatmap visualization"
    )
    
    # Build scenario dictionary
    scenario = {
        'scenario_name': f"{selected_template}_custom",
        'pop_factor': float(population_factor),
        'od_reduction_percent': float(od_reduction),
        'infrastructure_upgrade_percent': float(infrastructure_upgrade),
        'fecal_sludge_treatment_percent': float(fecal_sludge_treatment),
        'centralized_treatment_enabled': bool(centralized_treatment),
        'ks_per_m': float(spatial_decay),
        'radius_by_type': {
            'private': int(private_radius),
            'government': int(government_radius)
        },
        'efficiency_override': {
            1: float(eff_sewered),
            2: float(eff_pit), 
            3: float(eff_septic),
            4: float(eff_od)
        },
        'heatmap_radius': int(heatmap_radius),
        'link_batch_size': base_params.get('link_batch_size', 1000),
        'rebuild_standardized': False
    }
    
    # Handle EFIO override
    try:
        if efio_override.strip():
            scenario['EFIO_override'] = float(efio_override)
        else:
            scenario['EFIO_override'] = base_params.get('EFIO_override')
    except Exception:
        scenario['EFIO_override'] = base_params.get('EFIO_override')
    
    return scenario


def create_map(outputs: Dict[str, pd.DataFrame], heatmap_radius: int = 18) -> folium.Map:
    """Create the interactive map with pathogen concentrations."""
    if outputs['bh_conc'].empty:
        # Create empty map centered on Zanzibar
        m = folium.Map(location=[-6.165, 39.19], zoom_start=10)
        folium.Marker(
            [-6.165, 39.19],
            popup="No data available. Please run a scenario first.",
            icon=folium.Icon(color='gray', icon='info-sign')
        ).add_to(m)
        return m
    
    # Get map bounds from data
    all_lats = []
    all_longs = []
    
    for df_name in ['bh_conc', 'priv_bh_dash', 'gov_bh_dash']:
        df = outputs[df_name]
        if not df.empty and 'lat' in df.columns and 'long' in df.columns:
            all_lats.extend(df['lat'].dropna().tolist())
            all_longs.extend(df['long'].dropna().tolist())
    
    if all_lats and all_longs:
        center_lat = np.mean(all_lats)
        center_long = np.mean(all_longs)
    else:
        center_lat, center_long = -6.165, 39.19
    
    m = folium.Map(location=[center_lat, center_long], zoom_start=10)
    Fullscreen().add_to(m)
    
    # Add borehole concentration markers
    bh_conc = outputs['bh_conc']
    if not bh_conc.empty:
        # Add private boreholes
        for _, row in bh_conc[bh_conc['borehole_type'] == 'private'].iterrows():
            conc = row.get('concentration_CFU_per_100mL', 0)
            
            # Categorize concentration
            if conc < 10:
                color, category = 'green', 'Low'
            elif conc < 100:
                color, category = 'blue', 'Moderate'
            elif conc < 1000:
                color, category = 'orange', 'High'
            else:
                color, category = 'red', 'Very High'
            
            popup_text = f"""
            <b>Private Borehole {row.get('borehole_id', 'Unknown')}</b><br>
            Concentration: {conc:.1f} CFU/100mL<br>
            Category: {category}<br>
            Flow Rate: {row.get('Q_L_per_day', 'Unknown')} L/day
            """
            
            folium.Marker(
                [row['lat'], row['long']],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=f"Private BH: {conc:.1f} CFU/100mL",
                icon=folium.Icon(color=color, icon='tint', prefix='fa')
            ).add_to(m)
        
        # Add government boreholes
        for _, row in bh_conc[bh_conc['borehole_type'] == 'government'].iterrows():
            conc = row.get('concentration_CFU_per_100mL', 0)
            
            # Categorize concentration
            if conc < 10:
                color, category = 'green', 'Low'
            elif conc < 100:
                color, category = 'blue', 'Moderate'
            elif conc < 1000:
                color, category = 'orange', 'High'
            else:
                color, category = 'red', 'Very High'
            
            popup_text = f"""
            <b>Government Borehole {row.get('borehole_id', 'Unknown')}</b><br>
            Concentration: {conc:.1f} CFU/100mL<br>
            Category: {category}<br>
            Flow Rate: {row.get('Q_L_per_day', 'Unknown')} L/day
            """
            
            folium.Marker(
                [row['lat'], row['long']],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=f"Gov BH: {conc:.1f} CFU/100mL",
                icon=folium.Icon(color=color, icon='university', prefix='fa')
            ).add_to(m)
    
    # Add household load heatmap
    hh_heat = outputs.get('hh_loads_heat', pd.DataFrame())
    if not hh_heat.empty and len(hh_heat) > 0:
        # Create heatmap data
        heat_data = []
        for _, row in hh_heat.iterrows():
            if pd.notna(row.get('lat')) and pd.notna(row.get('long')) and pd.notna(row.get('logL')):
                heat_data.append([row['lat'], row['long'], row['logL']])
        
        if heat_data:
            HeatMap(
                heat_data,
                radius=heatmap_radius,
                blur=max(10, heatmap_radius-4),
                min_opacity=0.3,
                max_zoom=18,
                name="Household Pathogen Loads"
            ).add_to(m)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 200px; height: 130px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <h4>Pathogen Concentration</h4>
    <p><i class="fa fa-circle" style="color:green"></i> Low (&lt;10 CFU/100mL)</p>
    <p><i class="fa fa-circle" style="color:blue"></i> Moderate (10-99 CFU/100mL)</p>
    <p><i class="fa fa-circle" style="color:orange"></i> High (100-999 CFU/100mL)</p>
    <p><i class="fa fa-circle" style="color:red"></i> Very High (≥1000 CFU/100mL)</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m


def display_scenario_summary(scenario: Dict[str, Any]):
    """Display a summary of the current scenario parameters."""
    st.subheader("📊 Current Scenario Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Population Factor", f"{scenario.get('pop_factor', 1.0):.1f}x")
        st.metric("OD Reduction", f"{scenario.get('od_reduction_percent', 0):.0f}%")
        st.metric("Infrastructure Upgrade", f"{scenario.get('infrastructure_upgrade_percent', 0):.0f}%")
    
    with col2:
        st.metric("Fecal Sludge Treatment", f"{scenario.get('fecal_sludge_treatment_percent', 0):.0f}%")
        centralized = "Enabled" if scenario.get('centralized_treatment_enabled', False) else "Disabled"
        st.metric("Centralized Treatment", centralized)
        efio = scenario.get('EFIO_override', 'Default')
        if isinstance(efio, (int, float)):
            efio = format_large_number(efio)
        st.metric("EFIO", efio)
    
    with col3:
        st.metric("Spatial Decay Rate", f"{scenario.get('ks_per_m', 0.06):.3f} 1/m")
        radii = scenario.get('radius_by_type', {})
        st.metric("Private Radius", f"{radii.get('private', 35)} m")
        st.metric("Government Radius", f"{radii.get('government', 100)} m")


def display_results_summary(outputs: Dict[str, pd.DataFrame]):
    """Display summary statistics from model results."""
    bh_conc = outputs.get('bh_conc', pd.DataFrame())
    
    if bh_conc.empty:
        st.info("📈 Run a scenario to see results summary")
        return
    
    st.subheader("📈 Results Summary")
    
    # Calculate statistics
    total_boreholes = len(bh_conc)
    private_boreholes = len(bh_conc[bh_conc['borehole_type'] == 'private'])
    government_boreholes = len(bh_conc[bh_conc['borehole_type'] == 'government'])
    
    concentrations = bh_conc['concentration_CFU_per_100mL'].dropna()
    if len(concentrations) > 0:
        avg_conc = concentrations.mean()
        max_conc = concentrations.max()
        high_risk = len(concentrations[concentrations >= 100])
    else:
        avg_conc = max_conc = high_risk = 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Boreholes", total_boreholes)
        st.metric("Private Boreholes", private_boreholes)
    
    with col2:
        st.metric("Government Boreholes", government_boreholes)
        st.metric("High Risk Boreholes", f"{high_risk} ({high_risk/len(concentrations)*100:.1f}%)" if len(concentrations) > 0 else "0")
    
    with col3:
        st.metric("Average Concentration", f"{avg_conc:.1f} CFU/100mL" if avg_conc > 0 else "0")
        st.metric("Maximum Concentration", f"{max_conc:.1f} CFU/100mL" if max_conc > 0 else "0")
    
    with col4:
        # Progress tracking for TOR deliverables
        st.markdown("**TOR Progress Tracking**")
        deliverables_complete = 0
        total_deliverables = 8
        
        # Check which deliverables are ready
        if config.FIO_CONCENTRATION_AT_BOREHOLES_PATH.exists():
            deliverables_complete += 1
        if config.NET_SURVIVING_PATHOGEN_LOAD_LINKS_PATH.exists():
            deliverables_complete += 1
        if config.DASH_TOILETS_MARKERS_PATH.exists():
            deliverables_complete += 1
        if config.OUTPUT_DATA_DIR.joinpath('last_scenario.json').exists():
            deliverables_complete += 1
        
        progress = deliverables_complete / total_deliverables
        st.metric("Deliverables Ready", f"{deliverables_complete}/{total_deliverables}")
        st.progress(progress)


def main():
    """Main dashboard application."""
    set_page_config()
    
    # Header
    st.title("🌊 Zanzibar Pathogen Model Dashboard")
    st.markdown("**World Bank Grant: Ocean Health and Sanitation Nexus in Zanzibar**")
    
    # Create scenario form
    scenario = create_scenario_form()
    
    # Run scenario button
    run_button = st.sidebar.button(
        "🚀 Run Scenario", 
        type="primary",
        help="Execute the pathogen model with current parameters"
    )
    
    if run_button:
        with st.spinner("Running pathogen model... This may take a few minutes."):
            try:
                # Save scenario info for TOR compliance
                scenario['timestamp'] = datetime.datetime.utcnow().isoformat() + 'Z'
                scenario['run_type'] = 'enhanced_dashboard'
                
                fio_runner.run_scenario(scenario)
                st.success("✅ Scenario completed successfully!")
                st.experimental_rerun()  # Refresh to show new results
            except Exception as e:
                st.error(f"❌ Error running scenario: {str(e)}")
                st.exception(e)
    
    # Load and display results
    outputs = load_outputs()
    
    # Scenario summary
    display_scenario_summary(scenario)
    
    # Results summary
    display_results_summary(outputs)
    
    # Map visualization
    st.subheader("🗺️ Interactive Map")
    
    if not outputs['bh_conc'].empty:
        heatmap_radius = scenario.get('heatmap_radius', 18)
        map_obj = create_map(outputs, heatmap_radius)
        st.components.v1.html(map_obj._repr_html_(), height=600)
        
        # Data export options
        st.subheader("📁 Data Export")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Download Borehole Results"):
                csv = outputs['bh_conc'].to_csv(index=False)
                st.download_button(
                    label="📊 Borehole Concentrations CSV",
                    data=csv,
                    file_name=f"borehole_concentrations_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime='text/csv'
                )
        
        with col2:
            if st.button("Download Scenario Parameters"):
                scenario_json = json.dumps(scenario, indent=2)
                st.download_button(
                    label="⚙️ Scenario Parameters JSON",
                    data=scenario_json,
                    file_name=f"scenario_parameters_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.json",
                    mime='application/json'
                )
        
        with col3:
            if st.button("Generate TOR Report"):
                st.info("📄 Report generation feature coming soon. For now, use the data exports above for manual report preparation.")
    
    else:
        st.info("👆 Use the sidebar form to configure and run a scenario to see results.")
        
        # Show sample map of Zanzibar
        sample_map = folium.Map(location=[-6.165, 39.19], zoom_start=10)
        folium.Marker(
            [-6.165, 39.19],
            popup="Zanzibar - Run a scenario to see pathogen modeling results",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(sample_map)
        st.components.v1.html(sample_map._repr_html_(), height=400)
    
    # Footer with TOR information
    st.markdown("---")
    st.markdown("""
    **Terms of Reference Compliance**: This dashboard supports the World Bank STC Geospatial Programming Specialist 
    deliverables including automated geospatial data workflows, GIS-based pathogen flow analysis models, 
    and interactive visualizations for stakeholder engagement.
    
    **Model Description**: 3-layer pathogen transport model analyzing household sanitation impacts on groundwater 
    and marine environments in Zanzibar. Layer 1: pathogen loads, Layer 2: spatial transport with decay, 
    Layer 3: borehole concentrations.
    """)


if __name__ == '__main__':
    main()