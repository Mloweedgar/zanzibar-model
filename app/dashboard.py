"""Unified Dashboard for Zanzibar Model.

Combines:
1. Pathogen Risk Map (FIO)
2. Nitrogen Load Map
3. Toilet Inventory Map
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import numpy as np
from typing import Dict, Any

import sys
from pathlib import Path

# Ensure local app package is found first
ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import config
from app import engine

st.set_page_config(page_title="Zanzibar Water Quality Model", layout="wide")

# --- Helpers ---

def load_data(path):
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)

def get_color(val, min_val, max_val, palette='red'):
    """Return color [r,g,b,a] based on value."""
    # Simple linear interpolation
    norm = np.clip((val - min_val) / (max_val - min_val + 1e-9), 0, 1)
    if palette == 'red': # Green -> Yellow -> Red
        r = int(255 * min(2 * norm, 1))
        g = int(255 * min(2 * (1 - norm), 1))
        b = 0
    elif palette == 'blue': # Light -> Dark Blue
        r, g = 0, 0
        b = int(50 + 205 * norm)
    else:
        r, g, b = 100, 100, 100
    return [r, g, b, 200]

# --- Views ---

def view_pathogen_risk(map_style):
    st.header("🦠 Pathogen Risk (E. coli)")
    
    df = load_data(config.FIO_CONCENTRATION_PATH)
    if df.empty:
        st.warning("No data found. Run the FIO pipeline first.")
        return

    # Filters
    btype = st.multiselect("Borehole Type", df['borehole_type'].unique(), default=df['borehole_type'].unique())
    df = df[df['borehole_type'].isin(btype)]
    
    # Stats
    c1, c2, c3 = st.columns(3)
    c1.metric("Boreholes", len(df))
    c2.metric("Avg Concentration", f"{df['concentration_CFU_per_100mL'].mean():.1f}")
    c3.metric("High Risk (>100)", len(df[df['concentration_CFU_per_100mL'] > 100]))

    # Map
    df['color'] = df['concentration_CFU_per_100mL'].apply(lambda x: get_color(np.log1p(x), 0, np.log1p(1000)))
    df['radius'] = df['concentration_CFU_per_100mL'].apply(lambda x: 5 + np.clip(x/10, 0, 20))
    
    layer = pdk.Layer(
        "ScatterplotLayer",
        df,
        get_position=['long', 'lat'],
        get_fill_color='color',
        get_radius='radius',
        pickable=True,
        auto_highlight=True
    )
    
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(latitude=-6.165, longitude=39.202, zoom=10),
        map_style=map_style,
        tooltip={"text": "ID: {id}\nConc: {concentration_CFU_per_100mL} CFU"}
    ))

def view_nitrogen_load(map_style):
    st.header("🌱 Nitrogen Load")
    
    df = load_data(config.NET_NITROGEN_LOAD_PATH)
    if df.empty:
        st.warning("No data found. Run the Nitrogen pipeline first.")
        return
        
    # Stats
    st.metric("Total Nitrogen Load", f"{df['nitrogen_load'].sum()/1000:.1f} tonnes/yr")
    
    # Map
    df['color'] = df['nitrogen_load'].apply(lambda x: get_color(x, 0, 50, palette='blue'))
    
    layer = pdk.Layer(
        "ScatterplotLayer",
        df.sample(min(len(df), 20000)), # Sample for performance
        get_position=['long', 'lat'],
        get_fill_color='color',
        get_radius=20,
        pickable=True
    )
    
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(latitude=-6.165, longitude=39.202, zoom=10),
        map_style=map_style,
        tooltip={"text": "Load: {nitrogen_load} kg/yr"}
    ))

def view_toilet_inventory(map_style):
    st.header("🚽 Toilet Inventory")
    
    df = load_data(config.SANITATION_STANDARDIZED_PATH)
    if df.empty:
        st.warning("No data found.")
        return
        
    # Category Map
    cat_map = {1: 'Sewer', 2: 'Pit', 3: 'Septic', 4: 'OD'}
    df['type_label'] = df['toilet_category_id'].map(cat_map)
    
    # Stats
    st.bar_chart(df['type_label'].value_counts())
    
    # Map
    color_map = {
        1: [0, 255, 0, 200],    # Sewer: Green
        2: [255, 165, 0, 200],  # Pit: Orange
        3: [0, 0, 255, 200],    # Septic: Blue
        4: [255, 0, 0, 200]     # OD: Red
    }
    df['color'] = df['toilet_category_id'].map(color_map)
    
    layer = pdk.Layer(
        "ScatterplotLayer",
        df.sample(min(len(df), 20000)),
        get_position=['long', 'lat'],
        get_fill_color='color',
        get_radius=15,
        pickable=True
    )
    
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(latitude=-6.165, longitude=39.202, zoom=10),
        map_style=map_style,
        tooltip={"text": "Type: {type_label}"}
    ))

# --- Main Layout ---

def main():
    st.sidebar.title("Zanzibar Model")
    view = st.sidebar.radio("View", ["Pathogen Risk", "Nitrogen Load", "Toilet Inventory"])
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Map Settings")
    map_style = st.sidebar.selectbox(
        "Map Style", 
        ["Light", "Dark", "Satellite", "Road"],
        index=0
    )
    
    style_map = {
        "Light": "mapbox://styles/mapbox/light-v9",
        "Dark": "mapbox://styles/mapbox/dark-v9",
        "Satellite": "mapbox://styles/mapbox/satellite-v9",
        "Road": "mapbox://styles/mapbox/streets-v11"
    }
    current_style = style_map.get(map_style, "mapbox://styles/mapbox/light-v9")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Run Scenario")
    
    scenario_name = st.sidebar.selectbox("Scenario", list(config.SCENARIOS.keys()))
    
    # Infer model type from view
    if view == "Nitrogen Load":
        model_type = "nitrogen"
    else:
        model_type = "fio"
    
    if st.sidebar.button(f"Run {model_type.upper()} Pipeline"):
        with st.spinner(f"Running {model_type}..."):
            engine.run_pipeline(model_type, scenario_name)
        st.success("Done!")
        st.experimental_rerun()

    if view == "Pathogen Risk":
        view_pathogen_risk(current_style)
    elif view == "Nitrogen Load":
        view_nitrogen_load(current_style)
    elif view == "Toilet Inventory":
        view_toilet_inventory(current_style)

if __name__ == "__main__":
    main()
