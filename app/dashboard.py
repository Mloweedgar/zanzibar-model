"""Unified Dashboard for Zanzibar Model.

Combines:
1. Pathogen Risk Map (FIO)
2. Nitrogen Load Map
3. Phosphorus Load Map
4. Toilet Inventory Map
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

def get_color(val, min_val, max_val, palette='risk'):
    """Return color [r,g,b,a] based on value."""
    # Normalize
    if max_val == min_val:
        norm = 0.5
    else:
        norm = np.clip((val - min_val) / (max_val - min_val), 0, 1)
    
    if palette == 'risk':
        # Multi-stop: Blue (0) -> Green (0.25) -> Yellow (0.5) -> Orange (0.75) -> Red (1.0)
        # This gives more resolution than simple 2-stop interpolation
        stops = {
            0.00: [0, 0, 255],      # Blue (Safe)
            0.25: [0, 255, 0],      # Green (Low)
            0.50: [255, 255, 0],    # Yellow (Moderate)
            0.75: [255, 165, 0],    # Orange (High)
            1.00: [255, 0, 0]       # Red (Critical)
        }
        
        # Find lower and upper stops
        lower = 0.0
        for s in sorted(stops.keys()):
            if s <= norm:
                lower = s
            else:
                break
        
        upper = 1.0
        for s in sorted(stops.keys(), reverse=True):
            if s >= norm:
                upper = s
            else:
                break
                
        if lower == upper:
            return stops[lower] + [200]
            
        # Interpolate
        t = (norm - lower) / (upper - lower)
        c1 = np.array(stops[lower])
        c2 = np.array(stops[upper])
        c = c1 + (c2 - c1) * t
        return [int(c[0]), int(c[1]), int(c[2]), 200]

    elif palette == 'blue': # Light -> Dark Blue
        r, g = 0, 0
        b = int(50 + 205 * norm)
        return [r, g, b, 200]
        
    else:
        return [100, 100, 100, 200]

# --- Views ---

def view_pathogen_risk(map_style, viz_type="Scatterplot"):
    st.header("🦠 Pathogen Risk")
    
    df = load_data(config.FIO_CONCENTRATION_PATH)
    if df.empty:
        st.warning("No data found. Run the FIO pipeline first.")
        return

    # Filters
    btype = st.multiselect("Borehole Type", df['borehole_type'].unique(), default=df['borehole_type'].unique())
    df = df[df['borehole_type'].isin(btype)]
    
    # Borehole Counts
    c_total = len(df)
    c_gov = len(df[df['borehole_type'] == 'government'])
    c_priv = len(df[df['borehole_type'] == 'private'])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Boreholes", f"{c_total:,}")
    m2.metric("ZAWA (Gov)", f"{c_gov:,}")
    m3.metric("Private", f"{c_priv:,}")
    
    st.markdown("---") # Separator
    
    # Stats: Risk Categories
    if 'risk_score' in df.columns:
        # Calculate categories
        bins = [-1, 25, 50, 75, 90, 101]
        labels = ['Safe', 'Moderate', 'High', 'Very High', 'Critical']
        # Use a temporary column for counting
        cats = pd.cut(df['risk_score'], bins=bins, labels=labels)
        counts = cats.value_counts()
        total = len(df)
        
        cols = st.columns(5)
        
        # Safe (Blue)
        c = counts.get('Safe', 0)
        p = (c / total) * 100 if total > 0 else 0
        cols[0].metric("🔵 Safe", f"{c:,}", f"{p:.1f}%")
        
        # Moderate (Green)
        c = counts.get('Moderate', 0)
        p = (c / total) * 100 if total > 0 else 0
        cols[1].metric("🟢 Moderate", f"{c:,}", f"{p:.1f}%")
        
        # High (Yellow)
        c = counts.get('High', 0)
        p = (c / total) * 100 if total > 0 else 0
        cols[2].metric("🟡 High", f"{c:,}", f"{p:.1f}%")
        
        # Very High (Orange)
        c = counts.get('Very High', 0)
        p = (c / total) * 100 if total > 0 else 0
        cols[3].metric("🟠 V. High", f"{c:,}", f"{p:.1f}%")
        
        # Critical (Red)
        c = counts.get('Critical', 0)
        p = (c / total) * 100 if total > 0 else 0
        cols[4].metric("🔴 Critical", f"{c:,}", f"{p:.1f}%")

        # Use Risk Score for coloring
        df['color'] = df['risk_score'].apply(lambda x: get_color(x, 0, 100, palette='risk'))
        tooltip_text = "ID: {id}\nConc: {concentration_CFU_per_100mL:.1f} CFU\nRisk Score: {risk_score:.1f}"
        
    else:
        # Fallback for old data
        c1, c2, c3 = st.columns(3)
        c1.metric("Boreholes", len(df))
        c2.metric("Avg Concentration", f"{df['concentration_CFU_per_100mL'].mean():.1f}")
        c3.metric("High Conc (>100)", len(df[df['concentration_CFU_per_100mL'] > 100]))
        
        df['color'] = df['concentration_CFU_per_100mL'].apply(lambda x: get_color(np.log1p(x), 0, np.log1p(1000), palette='risk'))
        tooltip_text = "ID: {id}\nConc: {concentration_CFU_per_100mL:.1f} CFU"

    # Sort by risk score so high risk renders on top (z-order)
    if 'risk_score' in df.columns:
        df = df.sort_values('risk_score', ascending=True)
    else:
        df = df.sort_values('concentration_CFU_per_100mL', ascending=True)

    # Fixed radius for equal visibility (100m = matches model capture zone)
    df['radius'] = 100
    
    if viz_type == "Heatmap":
        # Use Risk Score for weight if available
        weight_col = 'risk_score' if 'risk_score' in df.columns else 'concentration_CFU_per_100mL'
        layer = pdk.Layer(
            "HeatmapLayer",
            df,
            get_position=['long', 'lat'],
            get_weight=weight_col,
            radiusPixels=30,
            intensity=1,
            threshold=0.1
        )
    else:
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
        tooltip={"text": tooltip_text}
    ))

def view_nitrogen_load(map_style, viz_type="Scatterplot"):
    st.header("🌱 Nitrogen Load")
    
    df = load_data(config.NET_NITROGEN_LOAD_PATH)
    if df.empty:
        st.warning("No data found. Run the Nitrogen pipeline first.")
        return
        
    # Stats
    st.metric("Total Nitrogen Load", f"{df['nitrogen_load'].sum()/1000:.1f} tonnes/yr")
    
    # Map
    df['color'] = df['nitrogen_load'].apply(lambda x: get_color(x, 0, 50, palette='blue'))
    
    if viz_type == "Heatmap":
        layer = pdk.Layer(
            "HeatmapLayer",
            df,
            get_position=['long', 'lat'],
            get_weight='nitrogen_load',
            radiusPixels=40,
            intensity=1,
            threshold=0.05
        )
    else:
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

def view_phosphorus_load(map_style, viz_type="Scatterplot"):
    st.header("🧼 Phosphorus Load")
    
    df = load_data(config.NET_PHOSPHORUS_LOAD_PATH)
    if df.empty:
        st.warning("No data found. Run the Phosphorus pipeline first.")
        return
        
    # Stats
    st.metric("Total Phosphorus Load", f"{df['phosphorus_load'].sum()/1000:.1f} tonnes/yr")
    
    # Map
    df['color'] = df['phosphorus_load'].apply(lambda x: get_color(x, 0, 50, palette='blue'))
    
    if viz_type == "Heatmap":
        layer = pdk.Layer(
            "HeatmapLayer",
            df,
            get_position=['long', 'lat'],
            get_weight='phosphorus_load',
            radiusPixels=40,
            intensity=1,
            threshold=0.05
        )
    else:
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
        tooltip={"text": "Load: {phosphorus_load} kg/yr"}
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
    view = st.sidebar.radio("View", ["Pathogen Risk", "Nitrogen Load", "Phosphorus Load", "Toilet Inventory", "Model vs Reality"])
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Run Scenario")
    
    scenario_name = st.sidebar.selectbox("Scenario", list(config.SCENARIOS.keys()))
    
    # Infer model type from view
    if view == "Nitrogen Load":
        model_type = "nitrogen"
    elif view == "Phosphorus Load":
        model_type = "phosphorus"
    else:
        model_type = "fio"
    
    if st.sidebar.button(f"Run {model_type.upper()} Pipeline"):
        with st.spinner(f"Running {model_type}..."):
            engine.run_pipeline(model_type, scenario_name)
        st.success("Done!")
        st.experimental_rerun()

    with st.sidebar.expander("Settings"):
        st.markdown("**Map Style**")
        map_style = st.selectbox(
            "Theme", 
            ["Light", "Dark", "Satellite", "Road"],
            index=0
        )
        
        st.markdown("**Visualization**")
        viz_type = st.selectbox(
            "Type",
            ["Scatterplot", "Heatmap"],
            index=0,
            help="Scatterplot shows individual points. Heatmap shows density/intensity."
        )
    
    style_map = {
        "Light": "mapbox://styles/mapbox/light-v9",
        "Dark": "mapbox://styles/mapbox/dark-v9",
        "Satellite": "mapbox://styles/mapbox/satellite-v9",
        "Road": "mapbox://styles/mapbox/streets-v11"
    }
    current_style = style_map.get(map_style, "mapbox://styles/mapbox/light-v9")

    if view == "Pathogen Risk":
        view_pathogen_risk(current_style, viz_type)
    elif view == "Nitrogen Load":
        view_nitrogen_load(current_style, viz_type)
    elif view == "Phosphorus Load":
        view_phosphorus_load(current_style, viz_type)
    elif view == "Toilet Inventory":
        view_toilet_inventory(current_style) # Keep inventory as scatter for categorical clarity
    elif view == "Model vs Reality":
        view_model_vs_reality(current_style)

def view_model_vs_reality(map_style):
    st.header("⚖️ Model vs Reality (Calibration)")
    
    from app.calibration_engine import CalibrationEngine
    
    # Initialize Engine
    calib = CalibrationEngine()
    
    # Load Model Data (Default to FIO for now)
    if not calib.load_model_results('fio'):
        st.error("Could not load model results. Run the pipeline first.")
        return
        
    # Match Points
    with st.spinner("Matching model predictions to government data..."):
        matched = calib.match_points()
        
    if matched.empty:
        st.warning("No matching data found.")
        return
        
    # Calculate Metrics
    metrics = calib.calculate_metrics(matched)
    
    # Display Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Samples", metrics.get('n_samples', 0))
    c2.metric("RMSE (Log)", f"{metrics.get('rmse_log', 0):.2f}")
    c3.metric("Correlation", f"{metrics.get('correlation', 0):.2f}")
    
    # Scatter Plot (Observed vs Predicted)
    st.subheader("Observed vs Predicted")
    st.scatter_chart(
        matched,
        x='fio_obs',
        y='model_conc',
        color='#ff0000'
    )
    
    # Map of Residuals (Error)
    st.subheader("Error Map (Log Difference)")
    # Calculate residual for visualization
    # Positive = Model Overestimates, Negative = Model Underestimates
    matched['log_diff'] = np.log1p(matched['model_conc']) - np.log1p(matched['fio_obs'])
    matched['abs_diff'] = matched['log_diff'].abs()
    
    # Color scale: Blue (Under) -> White (Good) -> Red (Over)
    matched['color'] = matched['log_diff'].apply(lambda x: 
        [255, 0, 0, 200] if x > 1 else       # Overestimate
        [0, 0, 255, 200] if x < -1 else      # Underestimate
        [0, 255, 0, 200]                     # Good match
    )
    
    layer = pdk.Layer(
        "ScatterplotLayer",
        matched,
        get_position=['long', 'lat'],
        get_fill_color='color',
        get_radius=100,
        pickable=True
    )
    
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(latitude=-6.165, longitude=39.202, zoom=10),
        map_style=map_style,
        tooltip={"text": "Obs (Total Coli): {fio_obs}\nPred: {model_conc}\nDiff: {log_diff:.2f}"}
    ))

if __name__ == "__main__":
    main()
