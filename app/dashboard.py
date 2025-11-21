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
        # Dramatic color palette: Cyan (Safe) -> Lime (Low) -> Yellow (Moderate) -> Orange (High) -> Deep Red (Critical)
        stops = {
            0.00: [0, 255, 255],    # Bright Cyan (Safe) - eye-catching safe zones
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
        # Green gradient: Light green (safe) -> Dark green (high load)
        # Multi-stop for dramatic effect
        stops = {
            0.00: [230, 255, 230],  # Very light green (safe)
            0.25: [144, 238, 144],  # Light green
            0.50: [34, 139, 34],    # Forest green
            0.75: [0, 100, 0],      # Dark green
            1.00: [0, 50, 0]        # Very dark green (high load)
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
        # Purple gradient: Light purple (safe) -> Dark purple (high load)
        stops = {
            0.00: [230, 230, 250],  # Lavender (safe)
            0.25: [186, 85, 211],   # Medium orchid
            0.50: [138, 43, 226],   # Blue violet
            0.75: [75, 0, 130],     # Indigo
            1.00: [50, 0, 80]       # Very dark purple (high load)
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
        # Matched to new palette: Blue(0-25), Green(25-50), Yellow(50-60), Orange(60-90), Red(90+)
        bins = [-1, 25, 50, 60, 90, 101]
        labels = ['Safe', 'Moderate', 'High', 'Very High', 'Critical']
        # Use a temporary column for counting
        cats = pd.cut(df['risk_score'], bins=bins, labels=labels)
        counts = cats.value_counts()
        total = len(df)
        
        cols = st.columns(5)
        
        # Safe (Cyan)
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
            pickable=True,
            auto_highlight=True
        )
        tooltip_text = "ID: {id}\nImprovement: +{improvement:.1f} pts"
        
        # Overwrite tooltip for this view
        st.pydeck_chart(pdk.Deck(
            layers=[layer],
            initial_view_state=pdk.ViewState(latitude=-6.165, longitude=39.202, zoom=10),
            map_style=map_style,
            tooltip={"text": tooltip_text}
        ))
        return

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
        
    # Stats - Total Load
    total = df['nitrogen_load'].sum()/1000
    st.metric("Total Nitrogen Load", f"{total:.1f} tonnes/yr")
    
    # Load Categories
    bins = [0, 5, 10, 15, 20, 100]  # Aligned with color scale (0-20)
    labels = ['Very Low', 'Low', 'Moderate', 'High', 'Very High']
    df['load_cat'] = pd.cut(df['nitrogen_load'], bins=bins, labels=labels)
    cats = df['load_cat'].value_counts()
    total_points = len(df)
    
    cols = st.columns(5)
    
    # Category metrics with color-coordinated emojis
    cat_emojis = {
        'Very Low': '🟢',    # Light green
        'Low': '🟡',         # Yellow-green  
        'Moderate': '🟠',    # Orange-green
        'High': '🔴',        # Dark green
        'Very High': '⚫'    # Very dark
    }
    
    for i, label in enumerate(labels):
        c = cats.get(label, 0)
        p = (c / total_points) * 100 if total_points > 0 else 0
        emoji = cat_emojis[label]
        cols[i].metric(f"{emoji} {label}", f"{c:,}", f"{p:.1f}%")
    
    # Map - adjusted scale for better visual contrast (baseline mean ~13.5, scenario ~1.6)
    # Using max of 20 to show dramatic difference
    df['color'] = df['nitrogen_load'].apply(lambda x: get_color(x, 0, 20, palette='nitrogen'))
    
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
        
    # Stats - Total Load
    total = df['phosphorus_load'].sum()/1000
    st.metric("Total Phosphorus Load", f"{total:.1f} tonnes/yr")
    
    # Load Categories
    bins = [0, 0.25, 0.50, 0.75, 1.0, 100]  # Aligned with color scale (0-1.0)
    labels = ['Very Low', 'Low', 'Moderate', 'High', 'Very High']
    df['load_cat'] = pd.cut(df['phosphorus_load'], bins=bins, labels=labels)
    cats = df['load_cat'].value_counts()
    total_points = len(df)
    
    cols = st.columns(5)
    
    # Category metrics with color-coordinated emojis (round circles only)
    cat_emojis = {
        'Very Low': '⚪',    # White (lightest)
        'Low': '🔵',         # Blue (light purple)
        'Moderate': '🟣',    # Purple
        'High': '🟤',        # Brown (dark purple)
        'Very High': '⚫'    # Black (darkest)
    }
    
    for i, label in enumerate(labels):
        c = cats.get(label, 0)
        p = (c / total_points) * 100 if total_points > 0 else 0
        emoji = cat_emojis[label]
        cols[i].metric(f"{emoji} {label}", f"{c:,}", f"{p:.1f}%")
    
    # Map - adjusted scale for better visual contrast (baseline mean ~0.76, scenario ~0.08)
    # Using max of 1.0 to show dramatic difference
    df['color'] = df['phosphorus_load'].apply(lambda x: get_color(x, 0, 1.0, palette='phosphorus'))
    
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
