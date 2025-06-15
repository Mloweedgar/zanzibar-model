"""Interactive BEST-Z Nitrogen Model Dashboard using Streamlit."""

import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import Fullscreen
import logging
from pathlib import Path

# Handle imports for both direct execution and module execution
try:
    from . import config, ingest, preprocess, n_load
except ImportError:
    # If relative imports fail, try absolute imports
    import sys
    from pathlib import Path
    
    # Add the BEST-Z directory to Python path
    best_z_dir = Path(__file__).parent.parent
    if str(best_z_dir) not in sys.path:
        sys.path.insert(0, str(best_z_dir))
    
    from scripts import config, ingest, preprocess, n_load

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Page configuration
st.set_page_config(
    page_title="BEST-Z Nitrogen Model Dashboard",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_base_data():
    """Load and preprocess base data (cached for performance)."""
    # Load household data
    hh = preprocess.clean_households()
    
    # Group population by ward and toilet type
    pop = preprocess.group_population(hh)
    
    # Add removal efficiency data
    pop = preprocess.add_removal_efficiency(pop)
    
    # Load ward geometry
    wards_gdf = ingest.read_geojson(config.DATA_RAW / 'unguja_wards.geojson')
    
    return pop, wards_gdf

# Fixed scale maximum for consistent visualization
FIXED_SCALE_MAX = 10000

def calculate_scenario(pop_df, pop_factor, nre_overrides):
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

def create_map(gdf):
    """Create Folium map with nitrogen load data."""
    # Ensure CRS is WGS84 for Folium
    if gdf.crs and gdf.crs.to_string() != 'EPSG:4326':
        gdf = gdf.to_crs(epsg=4326)
    
    # Create a copy with capped values for choropleth visualization only
    # Keep original values for tooltips and popups
    gdf_viz = gdf.copy()
    gdf_viz['ward_total_n_load_kg_viz'] = gdf['ward_total_n_load_kg'].clip(upper=FIXED_SCALE_MAX)
    
    # Create base map
    m = folium.Map(
        location=[-6.1659, 39.2026], 
        zoom_start=10, 
        control_scale=True
    )
    
    # Add OpenStreetMap as default basemap
    folium.TileLayer(
        name='OpenStreetMap',
        overlay=False,
        control=True
    ).add_to(m)
    
    # Add satellite tile layer as optional basemap
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', 
        name='Esri Satellite', 
        overlay=False,
        control=True,
        show=False
    ).add_to(m)
    
    # Add choropleth layer with fixed scale (0 to 10,000 kg/year)
    # Use 1000 kg steps - 10 intervals for better granularity
    bins = [0, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
    
    folium.Choropleth(
        geo_data=gdf_viz,
        data=gdf_viz,
        columns=['ward_name', 'ward_total_n_load_kg_viz'],
        key_on='feature.properties.ward_name',
        fill_color='YlOrRd',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Annual Nitrogen Load (kg)',
        nan_fill_color='white',
        name='Nitrogen Load',
        bins=bins  # Use explicit bins for fixed scale
    ).add_to(m)
    
    # Add custom CSS to make legend more visible on dark satellite imagery
    legend_css = """
    <style>
    .legend {
        background-color: rgba(255, 255, 255, 0.9) !important;
        border: 2px solid rgba(0, 0, 0, 0.2) !important;
        border-radius: 5px !important;
        box-shadow: 0 0 15px rgba(0, 0, 0, 0.2) !important;
    }
    .legend .legend-title {
        color: black !important;
        font-weight: bold !important;
        font-size: 14px !important;
        text-shadow: 1px 1px 1px rgba(255, 255, 255, 0.8) !important;
    }
    .legend .legend-scale ul {
        margin: 0 !important;
        padding: 0 !important;
    }
    .legend .legend-scale ul li {
        color: black !important;
        font-weight: bold !important;
        font-size: 12px !important;
        text-shadow: 1px 1px 1px rgba(255, 255, 255, 0.8) !important;
    }
    </style>
    """
    m.get_root().html.add_child(folium.Element(legend_css))
    
    # Add ward details layer (invisible, just for popups/tooltips on choropleth)
    folium.GeoJson(
        gdf,
        name='Ward Details',
        style_function=lambda feature: {
            'fillColor': 'transparent',
            'color': 'transparent',
            'weight': 0,
            'fillOpacity': 0
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['ward_name', 'ward_total_n_load_kg', 'H_DISTRICT_NAME', 'reg_name'],
            aliases=['Ward:', 'N Load (kg):', 'District:', 'Region:'],
            localize=True
        ),
        popup=folium.GeoJsonPopup(
            fields=['ward_name', 'ward_total_n_load_kg', 'H_DISTRICT_NAME', 'reg_name'],
            aliases=['Ward:', 'N Load (kg):', 'District:', 'Region:'],
        )
    ).add_to(m)
    
    # Add controls
    Fullscreen().add_to(m)
    folium.LayerControl().add_to(m)
    
    return m

def main():
    """Main dashboard application."""
    st.title("🌊 BEST-Z Nitrogen Model Dashboard")
    st.markdown("Interactive tool for exploring nitrogen load scenarios in Zanzibar")
    
    # Load base data
    with st.spinner("Loading data..."):
        pop_df, wards_gdf = load_base_data()
    
    # Sidebar controls
    st.sidebar.header("Scenario Parameters")
    
    # Initialize session state
    if 'pop_factor' not in st.session_state:
        st.session_state.pop_factor = 1.0
    if 'preset_applied' not in st.session_state:
        st.session_state.preset_applied = None
    
    # Preset scenario buttons
    st.sidebar.subheader("Quick Presets")
    col1, col2, col3 = st.sidebar.columns(3)
    
    if col1.button("Baseline 2022"):
        st.session_state.pop_factor = 1.0
        st.session_state.preset_applied = 'baseline'
    
    if col2.button("Improved Removal"):
        st.session_state.pop_factor = 1.0
        st.session_state.preset_applied = 'improved'
    
    if col3.button("Pop Growth 2030"):
        st.session_state.pop_factor = 1.2
        st.session_state.preset_applied = 'growth'
    
    # Population growth factor
    pop_factor = st.sidebar.slider(
        "Population Growth Factor",
        min_value=0.5,
        max_value=2.0,
        value=st.session_state.pop_factor,
        step=0.1,
        help="Multiplier for population (1.0 = current population, 1.2 = 20% growth)"
    )
    
    # Nitrogen removal efficiency overrides
    st.sidebar.subheader("Nitrogen Removal Efficiency Overrides")
    st.sidebar.markdown("*Adjust removal efficiency for specific toilet types*")
    
    # Get unique toilet types from data
    toilet_types = pop_df['toilet_type_id'].unique()
    toilet_types = sorted([t for t in toilet_types if pd.notna(t)])
    
    nre_overrides = {}
    
    # Create sliders for each toilet type
    for toilet_type in toilet_types:
        # Get default efficiency
        default_eff = pop_df[pop_df['toilet_type_id'] == toilet_type]['nitrogen_removal_efficiency'].iloc[0]
        if pd.isna(default_eff):
            default_eff = 0.0
        
        # Determine value based on preset
        slider_value = float(default_eff)
        if st.session_state.preset_applied == 'improved' and toilet_type in ['1', '2', '3', '4']:
            slider_value = 0.80
        
        # Create slider
        override_val = st.sidebar.slider(
            f"Toilet Type {toilet_type}",
            min_value=0.0,
            max_value=1.0,
            value=slider_value,
            step=0.05,
            format="%.2f",
            key=f"toilet_{toilet_type}",
            help=f"Default: {default_eff:.2f}"
        )
        
        # Only add to overrides if different from default
        if abs(override_val - default_eff) > 0.001:
            nre_overrides[str(toilet_type)] = override_val
    
    # Calculate scenario
    with st.spinner("Calculating nitrogen loads..."):
        gdf = calculate_scenario(pop_df, pop_factor, nre_overrides)
    
    # Display summary statistics
    col1, col2, col3, col4 = st.columns(4)
    
    total_n_load = gdf['ward_total_n_load_kg'].sum()
    max_ward_load = gdf['ward_total_n_load_kg'].max()
    min_ward_load = gdf['ward_total_n_load_kg'].min()
    avg_ward_load = gdf['ward_total_n_load_kg'].mean()
    
    col1.metric("Total N Load", f"{total_n_load:,.0f} kg/year")
    col2.metric("Max Ward Load", f"{max_ward_load:,.0f} kg/year")
    col3.metric("Min Ward Load", f"{min_ward_load:,.0f} kg/year")
    col4.metric("Average Ward Load", f"{avg_ward_load:,.0f} kg/year")

    
    # Create and display map
    with st.spinner("Generating map..."):
        map_obj = create_map(gdf)
    
    # Display map
    st.subheader("Nitrogen Load Map")
    st.components.v1.html(map_obj._repr_html_(), height=600)
    
    # Data export section
    st.subheader("Data Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Download Ward Data (CSV)"):
            csv = gdf.drop(columns=['geometry']).to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"nitrogen_load_scenario_{pop_factor}x_pop.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("Download GeoJSON"):
            geojson = gdf[['ward_name', 'ward_total_n_load_kg', 'geometry']].to_json()
            st.download_button(
                label="Download GeoJSON",
                data=geojson,
                file_name=f"nitrogen_load_scenario_{pop_factor}x_pop.geojson",
                mime="application/json"
            )
    
    # Display current parameters
    with st.expander("Current Scenario Parameters"):
        st.write("**Population Factor:**", pop_factor)
        st.write("**Nitrogen Removal Efficiency Overrides:**")
        if nre_overrides:
            for toilet_type, efficiency in nre_overrides.items():
                st.write(f"- Toilet Type {toilet_type}: {efficiency:.2%}")
        else:
            st.write("- None (using default efficiencies)")

if __name__ == "__main__":
    main()