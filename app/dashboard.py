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
import json
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

@st.cache_data
def load_geojson(path: Path):
    if not path.exists():
        return None
    try:
        with path.open() as f:
            return json.load(f)
    except Exception:
        return None

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
        # Dramatic color palette: Blue (Safe) -> Lime (Low) -> Yellow (Moderate) -> Orange (High) -> Deep Red (Critical)
        stops = {
            0.00: [0, 120, 255],    # Bright Blue (Safe)
            0.25: [0, 255, 0],      # Lime Green (Low)
            0.50: [255, 255, 0],    # Yellow (Moderate)
            0.60: [255, 165, 0],    # Orange (High) - standard orange
            0.90: [255, 69, 0],     # Orange-Red (Very High) - subtle transition
            1.00: [200, 0, 0]       # Deep Red (Critical) - darker red for maximum
        }
        
        # Find lower and upper stops
        sorted_stops = sorted(stops.keys())
        
        # If norm is at or beyond max, use max color
        if norm >= sorted_stops[-1]:
            return stops[sorted_stops[-1]] + [200]
        
        # If norm is at or below min, use min color
        if norm <= sorted_stops[0]:
            return stops[sorted_stops[0]] + [200]
        
        # Find the two stops to interpolate between
        lower = sorted_stops[0]
        upper = sorted_stops[-1]
        
        for i in range(len(sorted_stops) - 1):
            if sorted_stops[i] <= norm < sorted_stops[i + 1]:
                lower = sorted_stops[i]
                upper = sorted_stops[i + 1]
                break
                
        # Interpolate
        t = (norm - lower) / (upper - lower)
        c1 = np.array(stops[lower])
        c2 = np.array(stops[upper])
        c = c1 + (c2 - c1) * t
        return [int(c[0]), int(c[1]), int(c[2]), 200]

    elif palette == 'nitrogen':
        # Green → Yellow → Red gradient to match category emojis (🟢🟡🔴)
        stops = {
            0.00: [100, 200, 100],  # Light green (Low)
            0.33: [50, 200, 50],    # Medium green
            0.50: [255, 255, 0],    # Yellow (Moderate)
            0.67: [255, 200, 0],    # Orange-yellow
            1.00: [255, 0, 0]       # Red (High)
        }
        
        sorted_stops = sorted(stops.keys())
        if norm >= sorted_stops[-1]:
            return stops[sorted_stops[-1]] + [200]
        if norm <= sorted_stops[0]:
            return stops[sorted_stops[0]] + [200]
        
        lower = sorted_stops[0]
        upper = sorted_stops[-1]
        for i in range(len(sorted_stops) - 1):
            if sorted_stops[i] <= norm < sorted_stops[i + 1]:
                lower = sorted_stops[i]
                upper = sorted_stops[i + 1]
                break
        
        t = (norm - lower) / (upper - lower)
        c1 = np.array(stops[lower])
        c2 = np.array(stops[upper])
        c = c1 + (c2 - c1) * t
        return [int(c[0]), int(c[1]), int(c[2]), 200]
    
    elif palette == 'phosphorus':
        # Blue → Purple → Brown gradient to match category emojis (🔵🟣🟤)
        stops = {
            0.00: [100, 150, 255],  # Light blue (Low)
            0.33: [50, 100, 255],   # Medium blue
            0.50: [150, 50, 200],   # Purple (Moderate)
            0.67: [120, 80, 120],   # Purple-brown
            1.00: [139, 69, 19]     # Brown (High)
        }
        
        sorted_stops = sorted(stops.keys())
        if norm >= sorted_stops[-1]:
            return stops[sorted_stops[-1]] + [200]
        if norm <= sorted_stops[0]:
            return stops[sorted_stops[0]] + [200]
        
        lower = sorted_stops[0]
        upper = sorted_stops[-1]
        for i in range(len(sorted_stops) - 1):
            if sorted_stops[i] <= norm < sorted_stops[i + 1]:
                lower = sorted_stops[i]
                upper = sorted_stops[i + 1]
                break
        
        t = (norm - lower) / (upper - lower)
        c1 = np.array(stops[lower])
        c2 = np.array(stops[upper])
        c = c1 + (c2 - c1) * t
        return [int(c[0]), int(c[1]), int(c[2]), 200]
        
    else:
        return [100, 100, 100, 200]

def build_wards_layer():
    """Optional ward boundaries overlay with informative tooltip."""
    geojson = load_geojson(config.WARDS_GEOJSON_PATH)
    if not geojson:
        return None
    return pdk.Layer(
        "GeoJsonLayer",
        data=geojson,
        stroked=True,
        filled=True,
        get_fill_color=[0, 0, 0, 0],  # invisible fill for easier hover
        get_line_color=[30, 30, 30, 160],
        get_line_width=2,
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True
    )

# --- Views ---

def view_pathogen_risk(map_style, viz_type="Scatterplot", extra_layers=None, tooltip=None):
    extra_layers = extra_layers or []
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
        # Matched to new palette: Blue(0-25), Green(25-50), Yellow(50-60), Orange(60-90), Red(90+)
        bins = [-1, 25, 50, 60, 90, 101]
        labels = ['Safe', 'Moderate', 'High', 'Very High', 'Critical']
        # Use a temporary column for counting
        cats = pd.cut(df['risk_score'], bins=bins, labels=labels)
        counts = cats.value_counts()
        total = len(df)
        
        cols = st.columns(5)
        
        # Safe (Blue)
        c = counts.get('Safe', 0)
        p = (c / total) * 100 if total > 0 else 0
        cols[0].metric("🔵 Safe (0-25)", f"{c:,}", f"{p:.1f}%")
        
        # Moderate (Green)
        c = counts.get('Moderate', 0)
        p = (c / total) * 100 if total > 0 else 0
        cols[1].metric("🟢 Moderate (25-50)", f"{c:,}", f"{p:.1f}%")
        
        # High (Yellow)
        c = counts.get('High', 0)
        p = (c / total) * 100 if total > 0 else 0
        cols[2].metric("🟡 High (50-60)", f"{c:,}", f"{p:.1f}%")
        
        # Very High (Orange)
        c = counts.get('Very High', 0)
        p = (c / total) * 100 if total > 0 else 0
        cols[3].metric("🟠 V. High (60-90)", f"{c:,}", f"{p:.1f}%")
        
        # Critical (Red)
        c = counts.get('Critical', 0)
        p = (c / total) * 100 if total > 0 else 0
        cols[4].metric("🔴 Critical (>90)", f"{c:,}", f"{p:.1f}%")

        # Use Risk Score for coloring
        df['color'] = df['risk_score'].apply(lambda x: get_color(x, 0, 100, palette='risk'))
        
    else:
        # Fallback for old data
        c1, c2, c3 = st.columns(3)
        c1.metric("Boreholes", len(df))
        c2.metric("Avg Concentration", f"{df['concentration_CFU_per_100mL'].mean():.1f}")
        c3.metric("High Conc (>100)", len(df[df['concentration_CFU_per_100mL'] > 100]))
        
        df['color'] = df['concentration_CFU_per_100mL'].apply(lambda x: get_color(np.log1p(x), 0, np.log1p(1000), palette='risk'))

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
    elif viz_type == "Risk Reduction (Impact)":
        # Load Baseline
        baseline_path = config.OUTPUT_DATA_DIR / 'baseline_risk.csv'
        if not baseline_path.exists():
            st.error("Baseline file not found. Run 'baseline_2025' first.")
            return
            
        base_df = pd.read_csv(baseline_path)
        
        # Merge on FID
        merged = df.merge(base_df[['fid', 'risk_score']], on='fid', suffixes=('', '_base'))
        
        # Calculate Improvement (Positive = Good)
        merged['improvement'] = merged['risk_score_base'] - merged['risk_score']
        
        # Filter for positive improvement
        improved = merged[merged['improvement'] > 0.1].copy()
        
        if improved.empty:
            st.warning("No risk reduction detected in this scenario.")
            return
            
        st.metric("Total Risk Reduced", f"{improved['improvement'].sum():.1f} points")
        
        # Color: Green intensity based on improvement
        # 0 -> Dark Green, 20+ -> Bright Neon Green
        improved['color'] = improved['improvement'].apply(lambda x: [0, 255, 0, int(np.clip(x*10 + 50, 100, 255))])
        
        # Radius: Bigger improvement = Bigger bubble
        improved['radius'] = improved['improvement'].apply(lambda x: np.clip(x * 10, 50, 300))
        
        layer = pdk.Layer(
            "ScatterplotLayer",
            improved,
            get_position=['long', 'lat'],
            get_fill_color='color',
            get_radius='radius',
            pickable=False
        )
        
        deck_kwargs = dict(
            layers=[layer] + extra_layers,
            initial_view_state=pdk.ViewState(latitude=-6.165, longitude=39.202, zoom=10),
            map_style=map_style
        )
        if tooltip:
            deck_kwargs["tooltip"] = tooltip
        st.pydeck_chart(pdk.Deck(**deck_kwargs))
        return

    else:
        layer = pdk.Layer(
            "ScatterplotLayer",
            df,
            get_position=['long', 'lat'],
            get_fill_color='color',
            get_radius='radius',
            pickable=False
        )
    
    deck_kwargs = dict(
        layers=[layer] + extra_layers,
        initial_view_state=pdk.ViewState(latitude=-6.165, longitude=39.202, zoom=10),
        map_style=map_style
    )
    if tooltip:
        deck_kwargs["tooltip"] = tooltip
    st.pydeck_chart(pdk.Deck(**deck_kwargs))
    st.caption("Risk score is 0–100 = 20·log10(conc+1); each 10× jump ≈ +20 points. Buckets: 0–25 Safe, 25–50 Moderate, 50–60 High, 60–90 Very High, >90 Critical.")

def view_nitrogen_load(map_style, viz_type="Scatterplot", extra_layers=None, tooltip=None):
    extra_layers = extra_layers or []
    st.header("🌱 Nitrogen Load")
    
    df = load_data(config.NET_NITROGEN_LOAD_PATH)
    if df.empty:
        st.warning("No data found. Run the Nitrogen pipeline first.")
        return
        
    # Stats - Total Load
    total = df['nitrogen_load'].sum()/1000
    st.metric("Total Nitrogen Load", f"{total:.1f} tonnes/yr")
    
    # Load Categories - Simpler 3-category system that handles edge cases
    # Based on data tertiles (33rd, 67th percentiles)
    q33 = df['nitrogen_load'].quantile(0.33)
    q67 = df['nitrogen_load'].quantile(0.67)
    
    # Handle edge case where all values are very similar
    if q33 == q67:
        df['load_cat'] = 'Moderate'
        cats = df['load_cat'].value_counts()
        total_points = len(df)
        
        cols = st.columns(3)
        cols[0].metric("🟢 Low", "0", "0.0%")
        cols[1].metric("🟡 Moderate (~uniform)", f"{total_points:,}", "100.0%")
        cols[2].metric("🔴 High", "0", "0.0%")
    else:
        bins = [0, q33, q67, df['nitrogen_load'].max() + 1]
        labels = ['Low', 'Moderate', 'High']
        df['load_cat'] = pd.cut(df['nitrogen_load'], bins=bins, labels=labels)
        cats = df['load_cat'].value_counts()
        total_points = len(df)
        
        cols = st.columns(3)
        
        # Low (Green)
        c = cats.get('Low', 0)
        p = (c / total_points) * 100 if total_points > 0 else 0
        cols[0].metric(f"🟢 Low (≤{q33:.1f})", f"{c:,}", f"{p:.1f}%")
        
        # Moderate (Yellow)
        c = cats.get('Moderate', 0)
        p = (c / total_points) * 100 if total_points > 0 else 0
        cols[1].metric(f"🟡 Moderate ({q33:.1f}-{q67:.1f})", f"{c:,}", f"{p:.1f}%")
        
        # High (Red)
        c = cats.get('High', 0)
        p = (c / total_points) * 100 if total_points > 0 else 0
        cols[2].metric(f"🔴 High (>{q67:.1f})", f"{c:,}", f"{p:.1f}%")
    
    # Map - Dynamic color scale based on data distribution
    # Use 95th percentile as max to show variation in most of the data
    scale_max = max(df['nitrogen_load'].quantile(0.95), 0.1)  # Avoid divide by zero
    df['color'] = df['nitrogen_load'].apply(lambda x: get_color(x, 0, scale_max, palette='nitrogen'))
    
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
            get_radius=100,
            pickable=False
        )
    
    deck_kwargs = dict(
        layers=[layer] + extra_layers,
        initial_view_state=pdk.ViewState(latitude=-6.165, longitude=39.202, zoom=10),
        map_style=map_style
    )
    if tooltip:
        deck_kwargs["tooltip"] = tooltip
    st.pydeck_chart(pdk.Deck(**deck_kwargs))
    st.caption("Buckets are based on this run’s 33rd/67th percentiles (kg/yr): Low ≤P33, Moderate P33–P67, High >P67. If values cluster tightly, everything shows “Moderate (~uniform)” to signal there’s no real gradient.")

def view_phosphorus_load(map_style, viz_type="Scatterplot", extra_layers=None, tooltip=None):
    extra_layers = extra_layers or []
    st.header("🧼 Phosphorus Load")
    
    df = load_data(config.NET_PHOSPHORUS_LOAD_PATH)
    if df.empty:
        st.warning("No data found. Run the Phosphorus pipeline first.")
        return
        
    # Stats - Total Load
    total = df['phosphorus_load'].sum()/1000
    st.metric("Total Phosphorus Load", f"{total:.1f} tonnes/yr")
    
    # Load Categories - Simpler 3-category system that handles edge cases
    # Based on data tertiles (33rd, 67th percentiles)
    q33 = df['phosphorus_load'].quantile(0.33)
    q67 = df['phosphorus_load'].quantile(0.67)
    
    # Handle edge case where all values are very similar
    if q33 == q67:
        df['load_cat'] = 'Moderate'
        cats = df['load_cat'].value_counts()
        total_points = len(df)
        
        cols = st.columns(3)
        cols[0].metric("🔵 Low", "0", "0.0%")
        cols[1].metric("🟣 Moderate (~uniform)", f"{total_points:,}", "100.0%")
        cols[2].metric("🟤 High", "0", "0.0%")
    else:
        bins = [0, q33, q67, df['phosphorus_load'].max() + 1]
        labels = ['Low', 'Moderate', 'High']
        df['load_cat'] = pd.cut(df['phosphorus_load'], bins=bins, labels=labels)
        cats = df['load_cat'].value_counts()
        total_points = len(df)
        
        cols = st.columns(3)
        
        # Low (Blue)
        c = cats.get('Low', 0)
        p = (c / total_points) * 100 if total_points > 0 else 0
        cols[0].metric(f"🔵 Low (≤{q33:.3f})", f"{c:,}", f"{p:.1f}%")
        
        # Moderate (Purple)
        c = cats.get('Moderate', 0)
        p = (c / total_points) * 100 if total_points > 0 else 0
        cols[1].metric(f"🟣 Moderate ({q33:.3f}-{q67:.3f})", f"{c:,}", f"{p:.1f}%")
        
        # High (Brown)
        c = cats.get('High', 0)
        p = (c / total_points) * 100 if total_points > 0 else 0
        cols[2].metric(f"🟤 High (>{q67:.3f})", f"{c:,}", f"{p:.1f}%")
    
    # Map - Dynamic color scale based on data distribution
    # Use 95th percentile as max to show variation in most of the data
    scale_max = max(df['phosphorus_load'].quantile(0.95), 0.01)  # Avoid divide by zero
    df['color'] = df['phosphorus_load'].apply(lambda x: get_color(x, 0, scale_max, palette='phosphorus'))
    
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
            get_radius=100,
            pickable=False
        )
    
    deck_kwargs = dict(
        layers=[layer] + extra_layers,
        initial_view_state=pdk.ViewState(latitude=-6.165, longitude=39.202, zoom=10),
        map_style=map_style
    )
    if tooltip:
        deck_kwargs["tooltip"] = tooltip
    st.pydeck_chart(pdk.Deck(**deck_kwargs))

def view_toilet_inventory(map_style, extra_layers=None, tooltip=None):
    extra_layers = extra_layers or []
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
        pickable=False
    )
    
    deck_kwargs = dict(
        layers=[layer] + extra_layers,
        initial_view_state=pdk.ViewState(latitude=-6.165, longitude=39.202, zoom=10),
        map_style=map_style
    )
    if tooltip:
        deck_kwargs["tooltip"] = tooltip
    st.pydeck_chart(pdk.Deck(**deck_kwargs))

# --- Main Layout ---

def main():
    st.sidebar.title("Zanzibar Model")
    view = st.sidebar.radio("View", ["Pathogen Risk", "Nitrogen Load", "Phosphorus Load", "Toilet Inventory"])
    
    # Scenario Selection
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📋 Select Scenario")
    
    # Create mapping of display names to scenario keys
    scenario_display_names = {
        key: scenario.get('display_name', key) 
        for key, scenario in config.SCENARIOS.items()
    }
    
    # Reverse mapping for lookup
    display_to_key = {v: k for k, v in scenario_display_names.items()}
    
    # Dropdown with display names
    selected_display_name = st.sidebar.selectbox(
        "Choose intervention scenario:",
        options=list(scenario_display_names.values()),
        index=0,  # Default to baseline
        label_visibility="collapsed"
    )
    
    # Get actual scenario key
    scenario_name = display_to_key[selected_display_name]
    
    # Show scenario description in an info box
    scenario_config = config.SCENARIOS[scenario_name]
    if 'display_name' in scenario_config:
        st.sidebar.markdown(f"**Selected:** {scenario_config['display_name']}")
    if 'description' in scenario_config:
        st.sidebar.info(scenario_config['description'])
    
    # Infer model type from view
    if view == "Nitrogen Load":
        model_type = "nitrogen"
    elif view == "Phosphorus Load":
        model_type = "phosphorus"
    else:
        model_type = "fio"
    
    # Get selected scenario config
    selected_scenario = config.SCENARIOS[scenario_name]
    
    # Interactive Parameter Controls (prefilled from scenario)
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎛️ Intervention Parameters")
    st.sidebar.caption("Adjust these to explore custom scenarios")
    
    # OD Reduction
    od_reduction = st.sidebar.slider(
        "Open Defecation Reduction (%)",
        min_value=0,
        max_value=100,
        value=int(selected_scenario.get('od_reduction_percent', 0)),
        step=5,
        help="% of OD households upgraded to improved sanitation"
    )
    
    # Infrastructure Upgrade
    infra_upgrade = st.sidebar.slider(
        "Pit → Septic Upgrade (%)",
        min_value=0,
        max_value=100,
        value=int(selected_scenario.get('infrastructure_upgrade_percent', 0)),
        step=5,
        help="% of pit latrines upgraded to septic systems"
    )
    
    # FSM Treatment
    fsm_treatment = st.sidebar.slider(
        "FSM Treatment Coverage (%)",
        min_value=0,
        max_value=100,
        value=int(selected_scenario.get('fecal_sludge_treatment_percent', 0)),
        step=5,
        help="% of septic systems with regulated emptying/treatment"
    )
    
    # Stone Town WWTP Toggle
    stone_town_sewer = st.sidebar.checkbox(
        "Enable Stone Town WWTP",
        value=selected_scenario.get('stone_town_sewer_enabled', False),
        help="Connect Stone Town to centralized wastewater treatment"
    )
    
    # Build scenario override with slider values
    scenario_override = {
        'od_reduction_percent': float(od_reduction),
        'infrastructure_upgrade_percent': float(infra_upgrade),
        'fecal_sludge_treatment_percent': float(fsm_treatment),
        'stone_town_sewer_enabled': stone_town_sewer,
        'centralized_treatment_enabled': stone_town_sewer or selected_scenario.get('centralized_treatment_enabled', False)
    }
    
    # Auto-run when scenario changes (but not sliders)
    if 'last_scenario' not in st.session_state:
        st.session_state.last_scenario = scenario_name
        
    if st.session_state.last_scenario != scenario_name:
        with st.spinner(f"Running {scenario_name}..."):
            engine.run_pipeline(model_type, scenario_name, scenario_override)
        st.session_state.last_scenario = scenario_name
        st.success(f"✅ {scenario_name} complete!")
        st.experimental_rerun()
    
    # Manual run button (with custom slider values)
    if st.sidebar.button(f"▶️ Run with Custom Parameters"):
        with st.spinner(f"Running custom scenario..."):
            engine.run_pipeline(model_type, scenario_name, scenario_override)
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
        show_wards = st.checkbox(
            "Show wards layer",
            value=False,
            help="Toggle administrative boundaries with ward/district/region names."
        )
    
    style_map = {
        "Light": "mapbox://styles/mapbox/light-v9",
        "Dark": "mapbox://styles/mapbox/dark-v9",
        "Satellite": "mapbox://styles/mapbox/satellite-v9",
        "Road": "mapbox://styles/mapbox/streets-v11"
    }
    current_style = style_map.get(map_style, "mapbox://styles/mapbox/light-v9")

    extra_layers = []
    tooltip = None
    if show_wards:
        wards_layer = build_wards_layer()
        if wards_layer:
            extra_layers.append(wards_layer)
            tooltip = {"text": "Ward: {ward_name}\nDistrict: {dist_name}\nRegion: {reg_name}"}
        else:
            st.sidebar.warning("Wards GeoJSON missing or invalid.")

    if view == "Pathogen Risk":
        view_pathogen_risk(current_style, viz_type, extra_layers, tooltip)
    elif view == "Nitrogen Load":
        view_nitrogen_load(current_style, viz_type, extra_layers, tooltip)
    elif view == "Phosphorus Load":
        view_phosphorus_load(current_style, viz_type, extra_layers, tooltip)
    elif view == "Toilet Inventory":
        view_toilet_inventory(current_style, extra_layers, tooltip) # Keep inventory as scatter for categorical clarity
    elif view == "Toilet Inventory":
        view_toilet_inventory(current_style, extra_layers, tooltip) # Keep inventory as scatter for categorical clarity

if __name__ == "__main__":
    main()
