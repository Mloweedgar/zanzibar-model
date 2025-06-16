"""Interactive BEST-Z Nitrogen Model Dashboard using Streamlit."""

import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import Fullscreen
import logging
from pathlib import Path
import tempfile
import os
import io

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

def main():
    """Main dashboard application."""
    st.title("🌊 BEST-Z Nitrogen Model Dashboard")
    st.markdown("Interactive tool for exploring nitrogen load scenarios in Zanzibar")
    
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
    
    # Calculate scenario
    with st.spinner("Calculating nitrogen loads..."):
        gdf = calculate_scenario(pop_df, pop_factor, nre_overrides)
    
    # Display summary statistics
    col1, col2, col3, col4 = st.columns(4)
    
    total_n_load = gdf['ward_total_n_load_kg'].sum() / 1000  # Convert to tonnes
    max_ward_load = gdf['ward_total_n_load_kg'].max() / 1000  # Convert to tonnes
    min_ward_load = gdf['ward_total_n_load_kg'].min() / 1000  # Convert to tonnes
    avg_ward_load = gdf['ward_total_n_load_kg'].mean() / 1000  # Convert to tonnes
    
    col1.metric("Total N Load", f"{total_n_load:,.1f} t/year")
    col2.metric("Max Ward Load", f"{max_ward_load:,.1f} t/year")
    col3.metric("Min Ward Load", f"{min_ward_load:,.1f} t/year")
    col4.metric("Average Ward Load", f"{avg_ward_load:,.1f} t/year")

    
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
            # Prepare data for export with both kg and tonnes
            export_df = gdf.drop(columns=['geometry']).copy()
            export_df['ward_total_n_load_tonnes'] = export_df['ward_total_n_load_kg'] / 1000
            csv = export_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"nitrogen_load_scenario_{pop_factor}x_pop.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("Download GeoJSON"):
            # Include both kg and tonnes in GeoJSON
            geojson_df = gdf[['ward_name', 'ward_total_n_load_kg', 'ward_total_n_load_tonnes', 'geometry']].copy()
            geojson = geojson_df.to_json()
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
            # Group overrides by system category for cleaner display
            overrides_by_category = {}
            for toilet_type, efficiency in nre_overrides.items():
                toilet_info = toilet_types_df[toilet_types_df['toilet_type_id'] == toilet_type]
                if not toilet_info.empty:
                    system_category = toilet_info['system_category'].iloc[0]
                    if system_category not in overrides_by_category:
                        overrides_by_category[system_category] = []
                    toilet_name = toilet_info['toilet_type'].iloc[0]
                    overrides_by_category[system_category].append((toilet_name, efficiency))
            
            for system_category, toilet_list in overrides_by_category.items():
                # Create user-friendly category name
                if system_category == 'septic_tank_sewer':
                    category_display = "Sewer & Septic Tank Toilet Types"
                elif system_category == 'septic_tank':
                    category_display = "Septic Tank Toilet Types"
                elif system_category == 'pit_latrine':
                    category_display = "Pit Latrine Toilet Types"
                elif system_category == 'open_defecation':
                    category_display = "Open Defecation Toilet Types"
                else:
                    category_display = f"{system_category.replace('_', ' ').title()} Toilet Types"
                
                # Show efficiency (all toilets in category have same efficiency)
                efficiency = toilet_list[0][1]  # Get efficiency from first toilet
                st.write(f"- **{category_display}**: {efficiency:.2%}")
                
                # Show which specific toilet types are affected
                for toilet_name, _ in toilet_list:
                    st.write(f"  • {toilet_name}")
        else:
            st.write("- None (using default efficiencies)")

if __name__ == "__main__":
    main()