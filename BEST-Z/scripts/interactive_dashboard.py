"""Interactive BEST-Z Nitrogen Model Dashboard using Streamlit."""

import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
import folium
from folium.plugins import Fullscreen
import logging
from pathlib import Path
import tempfile
import os
import io

# Handle imports for both direct execution and module execution
try:
    from . import config, ingest, preprocess, n_load, fio_load
except ImportError:
    # If relative imports fail, try absolute imports
    import sys
    from pathlib import Path
    
    # Add the BEST-Z directory to Python path
    best_z_dir = Path(__file__).parent.parent
    if str(best_z_dir) not in sys.path:
        sys.path.insert(0, str(best_z_dir))
    
    from scripts import config, ingest, preprocess, n_load, fio_load

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Page configuration
st.set_page_config(
    page_title="BEST-Z Nitrogen Model Dashboard",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def save_uploaded_file(uploaded_file, target_path):
    """Save uploaded file to target path."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

def validate_census_data(df):
    """Validate census data has required columns."""
    required_cols = ['ward_name', 'TOILET', 'SEX', 'AGE']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return False, f"Missing required columns: {missing_cols}"
    return True, "Valid"

def validate_sanitation_data(df):
    """Validate sanitation efficiency data has required columns."""
    required_cols = ['toilet_type_id', 'toilet_type', 'system_category', 'nitrogen_removal_efficiency']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return False, f"Missing required columns: {missing_cols}"
    return True, "Valid"

def validate_geojson_data(gdf):
    """Validate GeoJSON has required columns and geometry."""
    if 'geometry' not in gdf.columns:
        return False, "Missing geometry column"
    required_cols = ['ward_name']
    missing_cols = [col for col in required_cols if col not in gdf.columns]
    if missing_cols:
        return False, f"Missing required columns: {missing_cols}"
    return True, "Valid"

@st.cache_data
def load_base_data(use_uploaded=False):
    """Load and preprocess base data (cached for performance)."""
    if use_uploaded and 'uploaded_files' in st.session_state:
        # Use uploaded files
        uploaded_files = st.session_state.uploaded_files
        
        # Load household data from uploaded census file
        census_df = pd.read_csv(io.StringIO(uploaded_files['census'].decode('utf-8')))
        
        # Create temporary files for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            
            # Save uploaded files to temp directory
            census_path = temp_dir / 'census.csv'
            sanitation_path = temp_dir / 'sanitation.csv'
            geojson_path = temp_dir / 'wards.geojson'
            
            census_df.to_csv(census_path, index=False)
            
            sanitation_df = pd.read_csv(io.StringIO(uploaded_files['sanitation'].decode('utf-8')))
            sanitation_df.to_csv(sanitation_path, index=False)
            
            # Handle GeoJSON
            geojson_str = uploaded_files['geojson'].decode('utf-8')
            with open(geojson_path, 'w') as f:
                f.write(geojson_str)
            
            # Temporarily update config paths
            original_data_raw = config.DATA_RAW
            config.DATA_RAW = temp_dir
            
            try:
                # Process data using existing functions
                hh = preprocess.clean_households_from_path(census_path)
                pop = preprocess.group_population(hh)
                pop = preprocess.add_removal_efficiency_from_path(pop, sanitation_path)
                wards_gdf = ingest.read_geojson(geojson_path)
                
                # Load toilet type names for better UX
                toilet_types_df = sanitation_df[['toilet_type_id', 'toilet_type', 'system_category']].copy()
                toilet_types_df['toilet_type_id'] = toilet_types_df['toilet_type_id'].astype(str).str.strip()
                
            finally:
                # Restore original config
                config.DATA_RAW = original_data_raw
                
    else:
        # Use default files
        # Load household data
        hh = preprocess.clean_households()
        
        # Group population by ward and toilet type
        pop = preprocess.group_population(hh)
        
        # Add removal efficiency data
        pop = preprocess.add_removal_efficiency(pop)
        
        # Load ward geometry
        wards_gdf = ingest.read_geojson(config.DATA_RAW / 'unguja_wards.geojson')
        
        # Load toilet type names for better UX
        toilet_types_df = ingest.read_csv(config.DATA_RAW / 'sanitation_removal_efficiencies_Zanzibar.csv')
        toilet_types_df = toilet_types_df[['toilet_type_id', 'toilet_type', 'system_category']].copy()
        toilet_types_df['toilet_type_id'] = toilet_types_df['toilet_type_id'].astype(str).str.strip()
    
    return pop, wards_gdf, toilet_types_df

# Fixed scale maximum for consistent visualization (in kg)
FIXED_SCALE_MAX = 10000
# Fixed scale maximum for display (in tonnes)
FIXED_SCALE_MAX_TONNES = FIXED_SCALE_MAX / 1000

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
    # Add tonnes columns for display
    gdf['ward_total_n_load_tonnes'] = gdf['ward_total_n_load_kg'] / 1000
    gdf_viz['ward_total_n_load_tonnes_viz'] = gdf_viz['ward_total_n_load_kg_viz'] / 1000
    
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
    
    # Add choropleth layer with fixed scale (0 to 10 tonnes/year)
    # Use 1 tonne steps - 10 intervals for better granularity
    bins = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    folium.Choropleth(
        geo_data=gdf_viz,
        data=gdf_viz,
        columns=['ward_name', 'ward_total_n_load_tonnes_viz'],
        key_on='feature.properties.ward_name',
        fill_color='YlOrRd',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Annual Nitrogen Load (t)',
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
            fields=['ward_name', 'ward_total_n_load_tonnes', 'H_DISTRICT_NAME', 'reg_name'],
            aliases=['Ward:', 'N Load (t):', 'District:', 'Region:'],
            localize=True
        ),
        popup=folium.GeoJsonPopup(
            fields=['ward_name', 'ward_total_n_load_tonnes', 'H_DISTRICT_NAME', 'reg_name'],
            aliases=['Ward:', 'N Load (t):', 'District:', 'Region:'],
        )
    ).add_to(m)
    
    # Add controls
    Fullscreen().add_to(m)
    folium.LayerControl().add_to(m)
    
    return m


def create_fio_map(gdf, column, legend_name, colormap='YlOrRd'):
    """Create folium map with FIO load choropleth."""
    # Ensure CRS is WGS84 for Folium
    if gdf.crs and gdf.crs.to_string() != 'EPSG:4326':
        gdf = gdf.to_crs(epsg=4326)
    
    # Create base map
    m = folium.Map(
        location=[-6.1659, 39.2026], 
        zoom_start=10, 
        control_scale=True
    )
    
    # Add choropleth
    folium.Choropleth(
        geo_data=gdf,
        data=gdf,
        columns=['ward_name', column],
        key_on='feature.properties.ward_name',
        fill_color=colormap,
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=legend_name,
        name=legend_name
    ).add_to(m)
    
    # Add tooltip with FIO data
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
            fields=['ward_name', 'ward_total_fio_cfu_day', 'ward_open_fio_cfu_day', 'open_share_percent'],
            aliases=['Ward:', 'Total FIO Load:', 'Open Def. Load:', 'Open Share (%):'],
            localize=True,
            labels=True
        ),
        popup=folium.GeoJsonPopup(
            fields=['ward_name', 'ward_total_fio_cfu_day', 'ward_open_fio_cfu_day', 'open_share_percent', 'ward_total_population'],
            aliases=['Ward:', 'Total FIO (cfu/day):', 'Open Def. (cfu/day):', 'Open Share (%):', 'Population:'],
        )
    ).add_to(m)
    
    # Add controls
    Fullscreen().add_to(m)
    folium.LayerControl().add_to(m)
    
    return m


def create_hotspots_map(gdf, top_wards):
    """Create folium map highlighting open defecation hot-spots."""
    # Ensure CRS is WGS84 for Folium
    if gdf.crs and gdf.crs.to_string() != 'EPSG:4326':
        gdf = gdf.to_crs(epsg=4326)
    
    # Create base map
    m = folium.Map(
        location=[-6.1659, 39.2026], 
        zoom_start=10, 
        control_scale=True
    )
    
    # Add base choropleth for open defecation share
    folium.Choropleth(
        geo_data=gdf,
        data=gdf,
        columns=['ward_name', 'open_share_percent'],
        key_on='feature.properties.ward_name',
        fill_color='Oranges',
        fill_opacity=0.6,
        line_opacity=0.2,
        legend_name='Open Defecation Share (%)',
        name='All Wards'
    ).add_to(m)
    
    # Highlight top 10 wards with different style
    top_ward_names = set(top_wards['ward_name'].tolist())
    
    def style_function(feature):
        if feature['properties']['ward_name'] in top_ward_names:
            return {
                'fillColor': 'red',
                'color': 'darkred',
                'weight': 3,
                'fillOpacity': 0.8,
                'dashArray': '5, 5'
            }
        else:
            return {
                'fillColor': 'transparent',
                'color': 'transparent',
                'weight': 0,
                'fillOpacity': 0
            }
    
    # Add highlighted layer for hot-spots
    folium.GeoJson(
        gdf,
        name='Top 10 Hot-Spots',
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=['ward_name', 'ward_open_fio_cfu_day', 'open_share_percent', 'ward_total_population'],
            aliases=['Ward:', 'OD Load (cfu/day):', 'OD Share (%):', 'Population:'],
            localize=True,
            labels=True
        ),
        popup=folium.GeoJsonPopup(
            fields=['ward_name', 'ward_open_fio_cfu_day', 'open_share_percent', 'ward_total_population'],
            aliases=['Ward:', 'OD Load (cfu/day):', 'OD Share (%):', 'Population:'],
        )
    ).add_to(m)
    
    # Add controls
    Fullscreen().add_to(m)
    folium.LayerControl().add_to(m)
    
    return m


def main():
    """Main dashboard application."""
    st.title("🌊 BEST-Z Model Dashboard")
    st.markdown("Interactive tool for exploring nitrogen and pathogen load scenarios in Zanzibar")
    
    # Data source selection
    st.sidebar.header("📁 Data Source")
    data_source = st.sidebar.radio(
        "Choose data source:",
        ["Use Default Data", "Upload Custom Data"],
        help="Use default Zanzibar data or upload your own files"
    )
    
    use_uploaded = False
    
    if data_source == "Upload Custom Data":
        st.sidebar.subheader("Upload Data Files")
        
        # File upload widgets
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
        
        # Validate and process uploaded files
        if census_file and sanitation_file and geojson_file:
            try:
                # Read and validate files
                census_df = pd.read_csv(census_file)
                sanitation_df = pd.read_csv(sanitation_file)
                geojson_str = geojson_file.read().decode('utf-8')
                wards_gdf = gpd.read_file(io.StringIO(geojson_str))
                
                # Validate data
                census_valid, census_msg = validate_census_data(census_df)
                sanitation_valid, sanitation_msg = validate_sanitation_data(sanitation_df)
                geojson_valid, geojson_msg = validate_geojson_data(wards_gdf)
                
                if census_valid and sanitation_valid and geojson_valid:
                    # Store uploaded files in session state
                    st.session_state.uploaded_files = {
                        'census': census_file.getvalue(),
                        'sanitation': sanitation_file.getvalue(),
                        'geojson': geojson_file.getvalue()
                    }
                    use_uploaded = True
                    st.sidebar.success("✅ All files uploaded and validated successfully!")
                    
                    # Show data summary
                    with st.sidebar.expander("📊 Data Summary"):
                        st.write(f"**Census records:** {len(census_df):,}")
                        st.write(f"**Toilet types:** {len(sanitation_df)}")
                        st.write(f"**Wards:** {len(wards_gdf)}")
                        st.write(f"**Unique wards in census:** {census_df['ward_name'].nunique()}")
                        
                else:
                    # Show validation errors
                    if not census_valid:
                        st.sidebar.error(f"❌ Census data: {census_msg}")
                    if not sanitation_valid:
                        st.sidebar.error(f"❌ Sanitation data: {sanitation_msg}")
                    if not geojson_valid:
                        st.sidebar.error(f"❌ GeoJSON data: {geojson_msg}")
                        
            except Exception as e:
                st.sidebar.error(f"❌ Error processing files: {str(e)}")
        
        elif census_file or sanitation_file or geojson_file:
            st.sidebar.warning("⚠️ Please upload all three required files")
        else:
            st.sidebar.info("📤 Upload all three data files to use custom data")
            
            # Show data format requirements
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
                
                # Download template files
                if st.button("📥 Download Template Files"):
                    # Create sample census data
                    sample_census = pd.DataFrame({
                        'reg_name': ['Sample Region'] * 10,
                        'H_DISTRICT_NAME': ['Sample District'] * 10,
                        'H_COUNCIL_NAME': ['Sample Council'] * 10,
                        'H_CONSTITUENCY_NAME': ['Sample Constituency'] * 10,
                        'H_DIVISION_NAME': ['Sample Division'] * 10,
                        'ward_name': ['Ward A'] * 5 + ['Ward B'] * 5,
                        'H_INSTITUTION_TYPE': [' '] * 10,
                        'TOILET': [1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
                        'SEX': [1, 2, 1, 2, 1, 2, 1, 2, 1, 2],
                        'AGE': [25, 30, 35, 40, 45, 28, 32, 38, 42, 48]
                    })
                    
                    # Create sample sanitation data
                    sample_sanitation = pd.DataFrame({
                        'toilet_type_id': ['1', '2', '3', '4', '5'],
                        'toilet_type': [
                            'Flush to sewer',
                            'Flush to septic tank',
                            'Flush to pit',
                            'Flush elsewhere',
                            'VIP latrine'
                        ],
                        'system_category': [
                            'septic_tank_sewer',
                            'septic_tank',
                            'septic_tank',
                            'septic_tank',
                            'pit_latrine'
                        ],
                        'nitrogen_removal_efficiency': [0.0, 0.0, 0.0, 0.0, 0.0]
                    })
                    
                    # Create sample GeoJSON
                    sample_geojson = {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "properties": {"ward_name": "Ward A"},
                                "geometry": {
                                    "type": "Polygon",
                                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                                }
                            },
                            {
                                "type": "Feature", 
                                "properties": {"ward_name": "Ward B"},
                                "geometry": {
                                    "type": "Polygon",
                                    "coordinates": [[[1, 0], [2, 0], [2, 1], [1, 1], [1, 0]]]
                                }
                            }
                        ]
                    }
                    
                    # Provide download buttons
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
                        import json
                        st.download_button(
                            "GeoJSON Template",
                            json.dumps(sample_geojson, indent=2),
                            "wards_template.geojson",
                            "application/json"
                        )
    
    # Load base data
    with st.spinner("Loading data..."):
        pop_df, wards_gdf, toilet_types_df = load_base_data(use_uploaded=use_uploaded)
    
    # Sidebar controls
    st.sidebar.header("🎛️ Scenario Parameters")
    
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
    st.sidebar.markdown("*Adjust removal efficiency for toilet types*")
    
    # Group toilet types by system category
    system_categories = toilet_types_df['system_category'].unique()
    system_categories = sorted([cat for cat in system_categories if pd.notna(cat)])
    
    nre_overrides = {}
    
    # Create sliders for each system category
    for system_category in system_categories:
        # Get toilet types in this system category
        category_toilets = toilet_types_df[toilet_types_df['system_category'] == system_category]
        
        # Get toilet type IDs that exist in our population data
        existing_toilet_ids = pop_df['toilet_type_id'].unique()
        category_toilet_ids = category_toilets['toilet_type_id'].astype(str).str.strip()
        relevant_toilet_ids = [tid for tid in category_toilet_ids if tid in existing_toilet_ids]
        
        if not relevant_toilet_ids:
            continue
            
        # Get default efficiency (use the first toilet type's efficiency as representative)
        first_toilet_id = relevant_toilet_ids[0]
        default_eff = pop_df[pop_df['toilet_type_id'] == first_toilet_id]['nitrogen_removal_efficiency'].iloc[0]
        if pd.isna(default_eff):
            default_eff = 0.0
        
        # Create help text with all toilet types in this category
        help_text_lines = [f"Default: {default_eff:.2f}", "Toilet types in this category:"]
        for toilet_id in relevant_toilet_ids:
            toilet_info = toilet_types_df[toilet_types_df['toilet_type_id'] == toilet_id]
            if not toilet_info.empty:
                toilet_name = toilet_info['toilet_type'].iloc[0]
                help_text_lines.append(f"• {toilet_name}")
        help_text = "\n".join(help_text_lines)
        
        # Determine value based on preset
        slider_value = float(default_eff)
        if st.session_state.preset_applied == 'improved' and any(tid in ['1', '2', '3', '4'] for tid in relevant_toilet_ids):
            slider_value = 0.80
        
        # Create user-friendly label (just say "toilet types" not "system category")
        if system_category == 'septic_tank_sewer':
            display_label = "Sewer & Septic Tank Toilet Types"
        elif system_category == 'septic_tank':
            display_label = "Septic Tank Toilet Types"
        elif system_category == 'pit_latrine':
            display_label = "Pit Latrine Toilet Types"
        elif system_category == 'open_defecation':
            display_label = "Open Defecation Toilet Types"
        else:
            display_label = f"{system_category.replace('_', ' ').title()} Toilet Types"
        
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
        if abs(override_val - default_eff) > 0.001:
            for toilet_id in relevant_toilet_ids:
                nre_overrides[str(toilet_id)] = override_val
    
    # Create simplified tabs - focus on key stories
    tab1, tab2 = st.tabs(["🦠 Pathogen Analysis", "🧪 Nitrogen Analysis"])
    
    with tab1:
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
        avg_open_share = fio_gdf['open_share_percent'].mean()
        wards_with_od = (fio_gdf['ward_open_fio_cfu_day'] > 0).sum()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Daily Pathogen Load", 
                f"{total_fio:.1e} bacteria/day",
                help="Total disease-causing bacteria released daily across Zanzibar"
            )
        
        with col2:
            st.metric(
                "From Open Defecation", 
                f"{(total_open_fio/total_fio*100):.0f}%",
                help="Percentage of contamination from open defecation (most dangerous)"
            )
        
        with col3:
            st.metric(
                "Wards at Risk", 
                f"{wards_with_od} of {len(fio_gdf)}",
                help="Wards with open defecation contamination"
            )
        
        # Key message for decision makers
        st.info(f"""
        **Key Insight for Decision Makers:** Open defecation contributes **{(total_open_fio/total_fio*100):.0f}%** of pathogen contamination 
        while affecting **{wards_with_od}** wards. This creates direct disease transmission risks through contaminated groundwater and surface runoff.
        """)
        
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
            if "disease hot-spots" in map_story:
                st.markdown("**🔴 Red areas show highest open defecation contamination = highest disease risk**")
                fio_map = create_fio_map(fio_gdf, 'open_share_percent', 'Disease Risk: Open Defecation Share (%)', 'Reds')
            elif "overall contamination" in map_story:
                st.markdown("**🟠 Darker areas show higher total pathogen loads**")
                fio_gdf['ward_total_fio_cfu_day_log10'] = np.log10(fio_gdf['ward_total_fio_cfu_day'] + 1)
                fio_map = create_fio_map(fio_gdf, 'ward_total_fio_cfu_day_log10', 'Total Pathogen Load (Log scale)', 'YlOrRd')
            else:  # intervention priorities
                st.markdown("**🎯 Highlighted wards show top 10 priorities for intervention**")
                fio_map = create_hotspots_map(fio_gdf, od_top_wards)
        
        # Display map
        st.components.v1.html(fio_map._repr_html_(), height=600)
        
        # Intervention Impact Modeling
        st.subheader("💡 Intervention Impact: What if we build toilets?")
        
        # Simple scenario modeling
        od_reduction = st.slider(
            "If we convert X% of open defecation to basic toilets:",
            min_value=0,
            max_value=100,
            value=50,
            step=10,
            help="Model the health impact of providing basic sanitation"
        )
        
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
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Contamination Reduced", 
                    f"{reduction_percent:.0f}%",
                    help="Reduction in dangerous pathogen contamination"
                )
            
            with col2:
                affected_pop = od_top_wards['ward_total_population'].sum() * (od_reduction/100)
                st.metric(
                    "People Helped", 
                    f"~{affected_pop:,.0f}",
                    help="Estimated people who would benefit from improved sanitation"
                )
            
            with col3:
                priority_wards = len(od_top_wards[od_top_wards['open_share_percent'] > 20])
                st.metric(
                    "Priority Wards", 
                    f"{priority_wards}",
                    help="High-risk wards that need immediate attention"
                )
            
            st.success(f"""
            **Health Impact:** Converting {od_reduction}% of open defecation to basic toilets would reduce dangerous 
            pathogen contamination by **{reduction_percent:.0f}%**, directly protecting ~**{affected_pop:,.0f} people** 
            from water-borne diseases like cholera and diarrhea.
            """)
        
        # Priority Action Table
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
        
        # Simple technical note
        with st.expander("ℹ️ About Pathogen Measurements"):
            st.markdown("""
            - **Pathogens** = Disease-causing bacteria (E. coli, faecal coliforms)
            - **cfu/day** = Colony Forming Units per day (live bacteria released daily)
            - **Open defecation** contributes 100% of pathogens directly to environment
            - **Basic toilets** reduce contamination by ~20% through containment
                         - **Risk areas** = High open defecation % + high population density
             """)
    
    with tab2:
        st.header("Nitrogen Load Analysis")
        
        # Calculate nitrogen scenario
        with st.spinner("Calculating nitrogen loads..."):
            n_gdf = calculate_scenario(pop_df, pop_factor, nre_overrides)
        
        # Display summary statistics
        col1, col2, col3, col4 = st.columns(4)
        
        total_n_load = n_gdf['ward_total_n_load_kg'].sum() / 1000  # Convert to tonnes
        max_ward_load = n_gdf['ward_total_n_load_kg'].max() / 1000  # Convert to tonnes
        min_ward_load = n_gdf['ward_total_n_load_kg'].min() / 1000  # Convert to tonnes
        avg_ward_load = n_gdf['ward_total_n_load_kg'].mean() / 1000  # Convert to tonnes
        
        col1.metric("Total N Load", f"{total_n_load:,.1f} t/year")
        col2.metric("Max Ward Load", f"{max_ward_load:,.1f} t/year")
        col3.metric("Min Ward Load", f"{min_ward_load:,.1f} t/year")
        col4.metric("Average Ward Load", f"{avg_ward_load:,.1f} t/year")

        # Create and display map
        with st.spinner("Generating nitrogen map..."):
            n_map = create_map(n_gdf)
        
        # Display map
        st.subheader("Nitrogen Load Map")
        st.components.v1.html(n_map._repr_html_(), height=600)
        
        # Data export section
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

if __name__ == "__main__":
    main()