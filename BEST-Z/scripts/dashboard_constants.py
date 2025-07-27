"""Constants and configuration values for the BEST-Z dashboard."""

# Fixed scale maximum for consistent visualization (in kg)
FIXED_SCALE_MAX = 10000
# Fixed scale maximum for display (in tonnes)  
FIXED_SCALE_MAX_TONNES = FIXED_SCALE_MAX / 1000

# Map configuration
MAP_CENTER = [-6.1659, 39.2026]
MAP_ZOOM_START = 10

# Choropleth bins for nitrogen visualization (in tonnes)
NITROGEN_BINS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# Page configuration
PAGE_CONFIG = {
    "page_title": "BEST-Z Nitrogen Model Dashboard",
    "page_icon": "🌊",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Upload-related constants removed as upload functionality is no longer supported

# Tile layer configurations
TILE_LAYERS = {
    'openstreetmap': {
        'name': 'OpenStreetMap',
        'overlay': False,
        'control': True
    },
    'satellite': {
        'tiles': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        'attr': 'Esri',
        'name': 'Esri Satellite',
        'overlay': False,
        'control': True,
        'show': False
    }
}

# CSS styles for map legend
LEGEND_CSS = """
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

# Preset scenario configurations
PRESET_SCENARIOS = {
    'baseline': {
        'pop_factor': 1.0,
        'name': 'Baseline 2022'
    },
    'improved': {
        'pop_factor': 1.0,
        'name': 'Improved Removal',
        'improved_efficiency': 0.80
    },
    'growth': {
        'pop_factor': 1.2,
        'name': 'Pop Growth 2030'
    }
}

# System category display names
SYSTEM_CATEGORY_NAMES = {
    'septic_tank_sewer': 'Sewer & Septic Tank Toilet Types',
    'septic_tank': 'Septic Tank Toilet Types',
    'pit_latrine': 'Pit Latrine Toilet Types',
    'open_defecation': 'Open Defecation Toilet Types'
}

# Template data constants removed as upload functionality is no longer supported 