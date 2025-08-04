"""Map creation functions for the BEST-Z dashboard."""

import folium
from folium.plugins import Fullscreen
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
from . import config
from .dashboard_constants import (
    MAP_CENTER, 
    MAP_ZOOM_START, 
    NITROGEN_BINS, 
    FIXED_SCALE_MAX,
    TILE_LAYERS,
    LEGEND_CSS
)


def ensure_wgs84_crs(gdf):
    """Ensure GeoDataFrame is in WGS84 CRS for Folium compatibility."""
    if gdf.crs and gdf.crs.to_string() != 'EPSG:4326':
        return gdf.to_crs(epsg=4326)
    return gdf


def add_base_layers(m):
    """Add base tile layers to a Folium map."""
    # Add OpenStreetMap as default basemap
    folium.TileLayer(
        name=TILE_LAYERS['openstreetmap']['name'],
        overlay=TILE_LAYERS['openstreetmap']['overlay'],
        control=TILE_LAYERS['openstreetmap']['control']
    ).add_to(m)
    
    # Add satellite tile layer as optional basemap
    folium.TileLayer(
        tiles=TILE_LAYERS['satellite']['tiles'],
        attr=TILE_LAYERS['satellite']['attr'],
        name=TILE_LAYERS['satellite']['name'],
        overlay=TILE_LAYERS['satellite']['overlay'],
        control=TILE_LAYERS['satellite']['control'],
        show=TILE_LAYERS['satellite']['show']
    ).add_to(m)


def add_map_controls(m):
    """Add standard controls to a Folium map."""
    Fullscreen().add_to(m)
    folium.LayerControl().add_to(m)


def create_base_map():
    """Create a base Folium map with standard configuration."""
    m = folium.Map(
        location=MAP_CENTER, 
        zoom_start=MAP_ZOOM_START, 
        control_scale=True
    )
    add_base_layers(m)
    return m


def create_nitrogen_map(gdf):
    """Create Folium map with nitrogen load data."""
    # Ensure CRS is WGS84 for Folium
    gdf = ensure_wgs84_crs(gdf)
    
    # Create a copy with capped values for choropleth visualization only
    # Keep original values for tooltips and popups
    gdf_viz = gdf.copy()
    gdf_viz['ward_total_n_load_kg_viz'] = gdf['ward_total_n_load_kg'].clip(upper=FIXED_SCALE_MAX)
    # Add tonnes columns for display
    gdf['ward_total_n_load_tonnes'] = gdf['ward_total_n_load_kg'] / 1000
    gdf_viz['ward_total_n_load_tonnes_viz'] = gdf_viz['ward_total_n_load_kg_viz'] / 1000
    
    # Create base map
    m = create_base_map()
    
    # Add choropleth layer with fixed scale
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
        bins=NITROGEN_BINS
    ).add_to(m)
    
    # Add custom CSS to make legend more visible
    m.get_root().html.add_child(folium.Element(LEGEND_CSS))
    
    # Add ward details layer for tooltips/popups
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
    add_map_controls(m)
    
    return m


def format_large_number(value):
    """Convert large numbers to readable format with K/M/B/T suffixes."""
    if pd.isna(value) or value == 0:
        return "0"
    
    if abs(value) >= 1e12:
        return f"{value/1e12:.1f}T"
    elif abs(value) >= 1e9:
        return f"{value/1e9:.1f}B"
    elif abs(value) >= 1e6:
        return f"{value/1e6:.1f}M"
    elif abs(value) >= 1e3:
        return f"{value/1e3:.1f}K"
    else:
        return f"{value:.0f}"

def create_fio_map(gdf, column, legend_name, colormap='YlOrRd', scale_max=5000):
    """Create folium map with FIO load choropleth with dynamic scaling."""
    # Ensure CRS is WGS84 for Folium
    gdf = ensure_wgs84_crs(gdf)
    
    # Add formatted versions of large number columns for tooltips
    if 'ward_total_fio_cfu_day' in gdf.columns:
        gdf['total_fio_formatted'] = gdf['ward_total_fio_cfu_day'].apply(format_large_number)
    if 'ward_open_fio_cfu_day' in gdf.columns:
        gdf['open_fio_formatted'] = gdf['ward_open_fio_cfu_day'].apply(format_large_number)
    
    # Create base map
    m = create_base_map()
    
    # Handle large FIO values by scaling for better legend display
    display_column = column
    display_legend_name = legend_name
    
    if 'ward_total_fio_cfu_day' == column or 'ward_open_fio_cfu_day' == column:
        # Scale down large FIO values to fit user-selected range (displayed as 0-scale_max billions)
        scale_factor = 1e9
        scaled_column = f"{column}_billions"
        gdf[scaled_column] = gdf[column] / scale_factor
        
        # CLAMP VALUES TO FIT USER-SELECTED RANGE (0-scale_max billions)
        # This ensures all data fits within our chosen speedometer scale
        gdf[scaled_column] = gdf[scaled_column].clip(lower=0, upper=scale_max)  # 0 to scale_max billion range
        
        display_column = scaled_column
        # Update legend name to show billions
        if 'total' in column:
            display_legend_name = f'Total Contamination (0-{scale_max:,} Billions CFU/day)'
        else:
            display_legend_name = f'Open Defecation (0-{scale_max:,} Billions CFU/day)'
    
    # USER-SELECTABLE SCALE: 0 to scale_max for consistent visual reference like speedometer  
    if 'log10' in display_column:
        # For log scale data, use appropriate log range
        bins = [0, 2, 4, 6, 8, 10, 12, 14]  # Log scale from 1 to 10^14
    elif 'percent' in display_column:
        # For percentage data, use 0-100 scale
        bins = [0, 5, 10, 20, 30, 50, 70, 90, 100]
    elif 'billions' in display_column:
        # DYNAMIC SCALE: 0 to scale_max billion CFU/day based on user selection
        bins = [0, scale_max*0.05, scale_max*0.1, scale_max*0.2, scale_max*0.4, scale_max*0.6, scale_max*0.8, scale_max]
    else:
        # For raw contamination values - scale based on scale_max (converted from billions)
        max_raw = scale_max * 1e9  # Convert billions back to raw CFU/day
        bins = [0, max_raw*0.05, max_raw*0.1, max_raw*0.2, max_raw*0.4, max_raw*0.6, max_raw*0.8, max_raw]
    
    # Get actual data range AFTER scaling/clamping to ensure bins cover all values
    valid_data = gdf[display_column].dropna()
    
    # SAFETY: Ensure bins cover all data (especially important after clamping)
    if len(valid_data) > 0:
        actual_min = valid_data.min()
        actual_max = valid_data.max()
        
        # Ensure minimum is covered
        if actual_min < bins[0]:
            bins[0] = actual_min
            
        # Ensure maximum is covered - but limit to scale maximum
        if actual_max > bins[-1]:
            if 'billions' in display_column:
                bins[-1] = min(scale_max, actual_max * 1.01)  # Cap at scale_max billion max
            else:
                bins[-1] = actual_max * 1.01  # Small padding for other scales
    
    # Ensure bins are properly formatted and sorted
    bins = sorted([float(b) for b in bins])
    
    # Add choropleth with explicit bins for consistent visual scaling
    choropleth = folium.Choropleth(
        geo_data=gdf,
        data=gdf,
        columns=['ward_name', display_column],
        key_on='feature.properties.ward_name',
        fill_color=colormap,
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=display_legend_name,
        name="📊 Contamination Levels",
        bins=list(bins),  # Ensure bins is a list
        nan_fill_color='lightgray',  # Handle NaN values
        reset=True  # Force recalculation of scale
    )
    choropleth.add_to(m)
    
    # Add toilet types layer
    m = create_toilet_types_layer(m)
    
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
            fields=['ward_name', 'total_fio_formatted', 'open_fio_formatted', 'open_share_percent'],
            aliases=['Ward:', 'Total Contamination:', 'Open Defecation:', 'Open Share (%):'],
            localize=True,
            labels=True
        ),
        popup=folium.GeoJsonPopup(
            fields=['ward_name', 'total_fio_formatted', 'open_fio_formatted', 'open_share_percent', 'ward_total_population'],
            aliases=['Ward:', 'Total Contamination:', 'Open Defecation:', 'Open Share (%):', 'Population:'],
        )
    ).add_to(m)
    
    # Add controls (includes LayerControl)
    add_map_controls(m)
    
    return m


def create_hotspots_map(gdf, top_wards):
    """Create folium map highlighting open defecation hot-spots."""
    # Ensure CRS is WGS84 for Folium
    gdf = ensure_wgs84_crs(gdf)
    
    # Add formatted versions for display
    gdf['open_fio_formatted'] = gdf['ward_open_fio_cfu_day'].apply(format_large_number)
    
    # Create base map
    m = create_base_map()
    
    # Ensure percentage data fits 0-100 range
    gdf['open_share_percent'] = gdf['open_share_percent'].clip(lower=0, upper=100)
    
    # Add base choropleth for open defecation share with fixed 0-100 scale
    folium.Choropleth(
        geo_data=gdf,
        data=gdf,
        columns=['ward_name', 'open_share_percent'],
        key_on='feature.properties.ward_name',
        fill_color='Oranges',
        fill_opacity=0.6,
        line_opacity=0.2,
        legend_name='Open Defecation Share (0-100%)',
        name='All Wards',
        bins=[0, 5, 10, 20, 30, 50, 70, 90, 100],  # Fixed 0-100 scale for consistency
        nan_fill_color='lightgray'  # Handle NaN values
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
            fields=['ward_name', 'open_fio_formatted', 'open_share_percent', 'ward_total_population'],
            aliases=['Ward:', 'OD Contamination:', 'OD Share (%):', 'Population:'],
            localize=True,
            labels=True
        ),
        popup=folium.GeoJsonPopup(
            fields=['ward_name', 'open_fio_formatted', 'open_share_percent', 'ward_total_population'],
            aliases=['Ward:', 'OD Contamination:', 'OD Share (%):', 'Population:'],
        )
    ).add_to(m)
    
    # Add controls
    add_map_controls(m)
    
    return m


def create_contamination_map(gdf, map_story):
    """
    Create appropriate contamination map based on story selection.
    
    Args:
        gdf: GeoDataFrame with contamination data
        map_story: Story type to display
        
    Returns:
        tuple: (map_object, description)
    """
    if "disease hot-spots" in map_story:
        description = "**🔴 Red areas show highest open defecation contamination = highest disease risk**"
        fio_map = create_fio_map(gdf, 'open_share_percent', 'Disease Risk: Open Defecation Share (%)', 'Reds')
    elif "overall contamination" in map_story:
        description = "**🟠 Darker areas show higher total pathogen loads**"
        gdf['ward_total_fio_cfu_day_log10'] = np.log10(gdf['ward_total_fio_cfu_day'] + 1)
        fio_map = create_fio_map(gdf, 'ward_total_fio_cfu_day_log10', 'Total Pathogen Load (Log scale)', 'YlOrRd')
    else:  # intervention priorities
        description = "**🎯 Highlighted wards show top 10 priorities for intervention**"
        # Get top wards for hotspots map
        od_top_wards = gdf.nlargest(10, 'ward_open_fio_cfu_day')[
            ['ward_name', 'ward_open_fio_cfu_day', 'open_share_percent', 'ward_total_population']
        ].copy()
        fio_map = create_hotspots_map(gdf, od_top_wards)
    
    return fio_map, description 


def load_toilet_locations():
    """Load toilet location data with coordinates."""
    try:
        # Load the toilet locations data
        data_path = Path(__file__).resolve().parents[1] / 'data_raw' / 'toilet_types_locations.csv'
        df = pd.read_csv(data_path)
        
        # Filter out rows without coordinates
        df = df.dropna(subset=['H_LONGITUDE', 'H_LATITUDE'])
        
        # Map toilet text descriptions to specific categories based on actual data
        def categorize_toilet(toilet_text):
            toilet_lower = str(toilet_text).lower()
            
            # Flush systems (highest treatment potential)
            if 'piped sewer' in toilet_lower:
                return {'name': 'Piped Sewer', 'color': '#2E86AB', 'category': 'flush_sewer', 'efficiency': 'high'}
            elif 'septic tank' in toilet_lower:
                return {'name': 'Septic Tank', 'color': '#A23B72', 'category': 'flush_septic', 'efficiency': 'medium'}
            elif 'covered pit' in toilet_lower:
                return {'name': 'Covered Pit', 'color': '#F18F01', 'category': 'flush_pit', 'efficiency': 'medium'}
            elif 'somewhere else' in toilet_lower:
                return {'name': 'No Containment', 'color': '#C73E1D', 'category': 'flush_none', 'efficiency': 'none'}
            
            # Dry pit systems (medium treatment)
            elif 'vip' in toilet_lower or 'ventilated' in toilet_lower:
                return {'name': 'VIP Latrine', 'color': '#6A994E', 'category': 'pit_vip', 'efficiency': 'medium'}
            elif 'with lid' in toilet_lower:
                return {'name': 'Pit + Lid', 'color': '#BC4749', 'category': 'pit_lid', 'efficiency': 'low'}
            elif 'washable slab without lid' in toilet_lower:
                return {'name': 'Pit + Slab', 'color': '#F2CC8F', 'category': 'pit_slab', 'efficiency': 'low'}
            elif 'not-washable' in toilet_lower or 'soil slab' in toilet_lower:
                return {'name': 'Soil Slab Pit', 'color': '#81B29A', 'category': 'pit_soil', 'efficiency': 'very_low'}
            elif 'without slab' in toilet_lower or 'open pit' in toilet_lower:
                return {'name': 'Open Pit', 'color': '#E07A5F', 'category': 'pit_open', 'efficiency': 'very_low'}
            
            # No treatment systems
            elif 'bucket' in toilet_lower:
                return {'name': 'Bucket', 'color': '#3D5A80', 'category': 'none_bucket', 'efficiency': 'none'}
            elif any(word in toilet_lower for word in ['no facility', 'bush', 'field', 'beach']):
                return {'name': 'Open Defecation', 'color': '#ee0000', 'category': 'none_open', 'efficiency': 'none'}
            else:
                return {'name': 'Other', 'color': '#666666', 'category': 'unknown', 'efficiency': 'unknown'}
        
        # Add toilet type info
        df['toilet_info'] = df['TOILET'].apply(categorize_toilet)
        df['toilet_name'] = df['toilet_info'].apply(lambda x: x['name'])
        df['toilet_color'] = df['toilet_info'].apply(lambda x: x['color'])
        df['toilet_category'] = df['toilet_info'].apply(lambda x: x['category'])
        df['toilet_efficiency'] = df['toilet_info'].apply(lambda x: x['efficiency'])
        
        return df, None
        
    except Exception as e:
        print(f"Error loading toilet locations: {e}")
        return None, None


def create_toilet_types_layer(m):
    """Add toilet types point layer to the map."""
    toilet_df, _ = load_toilet_locations()
    
    if toilet_df is None:
        return m
    
    # Sample data if too large (for performance)
    if len(toilet_df) > 5000:
        toilet_df = toilet_df.sample(n=5000, random_state=42)
    
    # Create feature groups for each toilet category with color indicators
    feature_groups = {}
    
    # Get unique combinations of category, name, and color
    unique_types = toilet_df[['toilet_category', 'toilet_name', 'toilet_color']].drop_duplicates()
    
    for _, row in unique_types.iterrows():
        if row['toilet_category'] != 'unknown':
            # Create color swatch HTML
            color_swatch = f'<span style="display:inline-block;width:12px;height:12px;background-color:{row["toilet_color"]};border:1px solid #000;margin-right:5px;"></span>'
            
            # Create layer name with color indicator
            group_name = f"{color_swatch}{row['toilet_name']}"
            feature_groups[row['toilet_category']] = folium.FeatureGroup(name=group_name, show=False)
    
    # Add points to appropriate feature groups
    for _, row in toilet_df.iterrows():
        try:
            category = row['toilet_category']
            if category in feature_groups:
                folium.CircleMarker(
                    location=[row['H_LATITUDE'], row['H_LONGITUDE']],
                    radius=3,
                    popup=f"<b>{row['toilet_name']}</b><br/>Ward: {row.get('H_WARD_NAME', 'Unknown')}",
                    tooltip=row['toilet_name'],
                    color=row['toilet_color'],
                    fillColor=row['toilet_color'],
                    fillOpacity=0.7,
                    weight=1
                ).add_to(feature_groups[category])
        except Exception as e:
            continue  # Skip problematic rows
    
    # Add feature groups to map
    for group in feature_groups.values():
        group.add_to(m)
    
    return m 