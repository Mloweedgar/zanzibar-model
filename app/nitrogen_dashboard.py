"""Nitrogen dashboard using precomputed nitrogen load data."""

from pathlib import Path
from typing import Dict, Any, Optional
import os
import json

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk


# Support both package and script execution
try:
    from app import fio_config as config  # when executed as a script by Streamlit
    from app import n_runner
except Exception:
    from . import fio_config as config  # when imported as a package
    from . import n_runner


def _format_large(x) -> str:
    # Robust formatter: accepts numbers or numeric strings; returns '-' if not parseable
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


def _load_nitrogen_outputs() -> Dict[str, pd.DataFrame]:
    outputs = {}
    paths = {
        'nitrogen_loads': config.NET_NITROGEN_LOAD_PATH,
    }
    for k, p in paths.items():
        outputs[k] = pd.read_csv(p) if p.exists() else pd.DataFrame()
    return outputs


def _apply_template_to_state(params: Dict[str, Any]) -> None:
    """Prefill Streamlit session state for the Scenario Builder from a template dict."""
    ss = st.session_state
    try:
        ss['od_reduction_percent'] = int(params.get('od_reduction_percent', 0))
    except Exception:
        ss['od_reduction_percent'] = 0
    try:
        ss['infrastructure_upgrade_percent'] = int(params.get('infrastructure_upgrade_percent', 0))
    except Exception:
        ss['infrastructure_upgrade_percent'] = 0
    try:
        ss['fecal_sludge_treatment_percent'] = int(params.get('fecal_sludge_treatment_percent', 0))
    except Exception:
        ss['fecal_sludge_treatment_percent'] = 0
    ss['centralized_treatment_enabled'] = bool(params.get('centralized_treatment_enabled', False))
    try:
        ss['pop_factor'] = float(params.get('pop_factor', 1.0))
    except Exception:
        ss['pop_factor'] = 1.0


def _webgl_deck_nitrogen(nitrogen_data: pd.DataFrame, *, show_nitrogen_loads: bool = True, show_ward_boundaries: bool = False):
    """High-performance WebGL renderer for nitrogen data using pydeck."""

    center = [-6.165, 39.202]

    def prepare_nitrogen_data(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=['id', 'lat', 'long', 'toilet_category_id', 'nitrogen_load'])
        # Keep only needed columns early to reduce memory/transport size
        keep_cols = ['id', 'lat', 'long', 'toilet_category_id', 'nitrogen_load']
        present = [c for c in keep_cols if c in df.columns]
        d = df[present].dropna(subset=['lat', 'long']).copy()
        # Downcast dtypes to minimize payload
        try:
            if 'lat' in d.columns: d['lat'] = pd.to_numeric(d['lat'], errors='coerce').astype('float32')
            if 'long' in d.columns: d['long'] = pd.to_numeric(d['long'], errors='coerce').astype('float32')
            if 'nitrogen_load' in d.columns: d['nitrogen_load'] = pd.to_numeric(d['nitrogen_load'], errors='coerce').astype('float32')
            if 'toilet_category_id' in d.columns: d['toilet_category_id'] = pd.to_numeric(d['toilet_category_id'], errors='coerce').fillna(0).astype('int8')
        except Exception:
            pass

        # If the dataset is very large, sample to stay under Streamlit message limits
        # Target max rows ~120k to keep payload < 200 MB post-serialization
        MAX_POINTS = 120_000
        if len(d) > MAX_POINTS:
            # Stratified sampling by toilet type to preserve composition
            try:
                d = d.groupby('toilet_category_id', group_keys=False, observed=True).apply(
                    lambda g: g.sample(n=max(1, int(len(g) * (MAX_POINTS / len(df)))), random_state=42)
                )
            except Exception:
                d = d.sample(n=MAX_POINTS, random_state=42)
        
        # Create nitrogen load categories
        def nitrogen_category(load: float) -> str:
            try:
                x = float(load)
            except Exception:
                return 'unknown'
            if pd.isna(x) or x < 0:
                return 'unknown'
            if x < 20:
                return 'low'
            if x < 40:
                return 'moderate'
            if x < 60:
                return 'high'
            return 'very high'

        d['nitrogen_category'] = d['nitrogen_load'].apply(nitrogen_category)
        
        # Create toilet type labels
        def toilet_type_label(cat_id: int) -> str:
            cat_map = {1: 'Sewered', 2: 'Pit Latrine', 3: 'Septic', 4: 'Open Defecation'}
            return cat_map.get(int(cat_id), 'Unknown')
        
        d['toilet_type_label'] = d['toilet_category_id'].apply(toilet_type_label)
        
        # Build tooltip HTML (disable for very large datasets to reduce payload)
        try:
            if len(d) <= 60_000:
                def _row_html(row: pd.Series) -> str:
                    toilet_id = str(row.get('id') or '-')
                    toilet_type = str(row.get('toilet_type_label') or '-')
                    nitrogen_load = _format_large(row.get('nitrogen_load'))
                    return (
                        f"<div><b>Toilet ID: {toilet_id}</b><br>"
                        f"Type: <b>{toilet_type}</b><br>"
                        f"Nitrogen Load: <b>{nitrogen_load} kg N/year</b><br>"
                        f"</div>"
                    )
                d['tooltip_html'] = d.apply(_row_html, axis=1)
            else:
                d['tooltip_html'] = ''
        except Exception:
            d['tooltip_html'] = ''
        
        return d

    nitrogen_df = prepare_nitrogen_data(nitrogen_data)

    # Color schemes
    def color_from_nitrogen_cat(c: str):
        c = (c or '').lower()
        if c == 'low': return [46, 204, 113, 200]      # green
        if c == 'moderate': return [52, 152, 219, 200] # blue
        if c == 'high': return [243, 156, 18, 200]     # orange
        if c == 'very high': return [231, 76, 60, 200] # red
        return [160, 160, 160, 200]                   # gray

    # removed toilet type color mapping from nitrogen view

    # Size based on nitrogen load (scaled)
    def size_from_load(load: float) -> float:
        try:
            x = float(load)
            if pd.isna(x) or x < 0:
                return 3.0
            # Scale: 3-15 pixels based on load
            return min(15.0, max(3.0, 3.0 + (x / 10.0)))
        except Exception:
            return 3.0

    if not nitrogen_df.empty:
        nitrogen_df['size_px'] = nitrogen_df['nitrogen_load'].apply(size_from_load)
        nitrogen_df['nitrogen_color'] = nitrogen_df['nitrogen_category'].apply(color_from_nitrogen_cat)

    layers = []
    view_state = pdk.ViewState(latitude=center[0], longitude=center[1], zoom=10, pitch=0)

    # Nitrogen load layer (color by load intensity, size by load magnitude)
    if not nitrogen_df.empty and show_nitrogen_loads:
        layers.append(pdk.Layer(
            'ScatterplotLayer',
            data=nitrogen_df,
            get_position='[long, lat]',
            get_fill_color='nitrogen_color',
            get_radius='size_px',
            radius_min_pixels=3,
            radius_max_pixels=15,
            pickable=True,
            auto_highlight=True,
            stroked=False,
            opacity=0.7,
            visible=bool(show_nitrogen_loads),
            id='layer-nitrogen-loads'
        ))

    # removed toilet type layer; shown in dedicated dashboard

    # Ward boundaries
    try:
        p = config.INPUT_DATA_DIR / 'wards.geojson'
        if p.exists():
            with open(p, 'r', encoding='utf-8') as fh:
                wards_geo = json.load(fh)
            # Flatten fields for tooltip
            try:
                feats = wards_geo.get('features', [])
                for f in feats:
                    props = f.get('properties') or {}
                    f['ward_label'] = props.get('ward_name') or ''
                    f['div_name'] = props.get('div_name') or ''
                    f['counc_name'] = props.get('counc_name') or ''
                    f['dist_name'] = props.get('dist_name') or ''
                    f['reg_name'] = props.get('reg_name') or ''
                    f['tooltip_html'] = (
                        f"<div><b>{f['ward_label']}</b><br><small>"
                        f"Division: {f['div_name']} &nbsp;•&nbsp; Council: {f['counc_name']}<br>"
                        f"District: {f['dist_name']} &nbsp;•&nbsp; Region: {f['reg_name']}"
                        f"</small></div>"
                    )
            except Exception:
                pass
            layers.append(pdk.Layer(
                'GeoJsonLayer',
                data=wards_geo,
                stroked=True,
                filled=True,
                get_fill_color='[0,0,0,0]',
                get_line_color='[40,40,40,160]',
                line_width_min_pixels=1,
                pickable=True,
                visible=bool(show_ward_boundaries),
                id='layer-ward-outline'
            ))
    except Exception:
        pass

    # Map style handling
    map_style = None
    mapbox_token = None
    try:
        mapbox_token = st.secrets.get('MAPBOX_API_KEY')  # type: ignore[attr-defined]
    except Exception:
        mapbox_token = None
    if mapbox_token:
        map_style = 'mapbox://styles/mapbox/light-v9'
    else:
        map_style = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'

    # Tooltip
    tooltip = {
        'html': '{tooltip_html}',
        'style': {
            'backgroundColor': 'rgba(255,255,255,0.95)',
            'color': '#111',
            'fontSize': '12px',
            'borderRadius': '6px',
            'padding': '6px 8px',
            'boxShadow': '0 2px 6px rgba(0,0,0,0.15)'
        }
    }

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=map_style,
        tooltip=tooltip,
    )
    if mapbox_token:
        deck.mapbox_key = mapbox_token
    return deck


def _scenario_selector() -> Dict[str, Any]:
    items = list(config.SCENARIOS.items())
    default_key = 'crisis_2025_current' if 'crisis_2025_current' in config.SCENARIOS else items[0][0]
    with st.sidebar.expander('Select Scenario template to pre-fill Template builder', expanded=True):
        labels = [cfg.get('label', key) for key, cfg in items]
        keys = [key for key, _ in items]
        idx = keys.index(default_key) if default_key in keys else 0
        selected_label = st.selectbox('Template', options=labels, index=idx, key='scenario_template_select')
        selected_key = keys[labels.index(selected_label)]
        desc = config.SCENARIOS[selected_key].get('description')
        if desc:
            st.caption(desc)
        if st.button('Use this template', key='apply_template_btn'):
            _apply_template_to_state(config.SCENARIOS[selected_key])
            st.success('Template applied to Scenario Builder')
    return {"name": selected_key, "params": dict(config.SCENARIOS[selected_key])}


def _tunable_controls(base: Dict[str, Any]) -> Dict[str, Any]:
    st.sidebar.markdown('---')
    st.sidebar.subheader('Scenario Builder')
    st.sidebar.caption('Open the form below to edit settings. Changes apply only when you click Run scenario.')
    scenario = {
        'show_nitrogen_loads': bool(base.get('show_nitrogen_loads', True)),
        'show_ward_boundaries': bool(base.get('show_ward_boundaries', False)),
    }
    return scenario


def _legend_and_toggles(defaults: Dict[str, bool]) -> Dict[str, bool]:
    # Legend for nitrogen loads
    html = """
    <style>
    .legend-top { display: flex; align-items: center; gap: 16px; margin: 8px 0 6px 0; padding: 10px 12px; background: #ffffff;
                  border: 1px solid #e0e0e0; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); font-size: 13px; }
    .legend-top .title { font-weight: 600; margin-right: 6px; color: #333; }
    .legend-top .entry { display: inline-flex; align-items: center; gap: 6px; color: #333; }
    .legend-top .dot { width: 10px; height: 10px; border-radius: 50%%; display: inline-block; }
    .legend-top .sep { width: 1px; height: 14px; background: #e0e0e0; margin: 0 2px; }
    @media (max-width: 768px) { .legend-top { flex-wrap: wrap; gap: 10px; } }
    </style>
    <div class="legend-top">
      <div class="title">Nitrogen Load (kg N/year):</div>
      <div class="entry"><span class="dot" style="background:#2ecc71"></span>Low (&lt;20) </div>
      <div class="sep"></div>
      <div class="entry"><span class="dot" style="background:#3498db"></span>Moderate (20-40) </div>
      <div class="sep"></div>
      <div class="entry"><span class="dot" style="background:#f39c12"></span>High (40-60) </div>
      <div class="sep"></div>
      <div class="entry"><span class="dot" style="background:#e74c3c"></span>Very High (&gt;60) </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    
    # Toggles
    col1, col3 = st.columns([3, 2])
    with col1:
        show_nitrogen_loads = st.checkbox('Nitrogen Load Intensity', value=bool(defaults.get('show_nitrogen_loads', True)))
    with col3:
        show_ward_boundaries = st.checkbox('Ward boundaries', value=bool(defaults.get('show_ward_boundaries', False)))
    return {
        'show_nitrogen_loads': bool(show_nitrogen_loads),
        'show_ward_boundaries': bool(show_ward_boundaries),
    }


def main():
    # Page config is set in the parent dashboard.py

    sel = _scenario_selector()
    tuned = _tunable_controls(sel['params'])

    # Single-submit scenario form
    with st.sidebar.form('scenario_form'):
        st.markdown('#### Edit scenario settings')
        pop_factor = st.number_input('Population factor', min_value=0.1, max_value=5.0, value=float(sel['params'].get('pop_factor', 1.0)), step=0.05)
        full_ct = st.checkbox('Centralized treatment (sewered)', value=bool(sel['params'].get('centralized_treatment_enabled', False)))
        od_red = st.slider('Convert OD to septic (%)', 0, 100, int(sel['params'].get('od_reduction_percent', 0)))
        upgrade = st.slider('Upgrade pit latrines to septic (%)', 0, 100, int(sel['params'].get('infrastructure_upgrade_percent', 0)))
        fecal_sludge = st.slider('Fecal sludge treatment (%)', 0, 100, int(sel['params'].get('fecal_sludge_treatment_percent', 0)))

        submitted = st.form_submit_button('Run scenario')
        if submitted:
            with st.spinner(f"Running nitrogen scenario pipeline..."):
                scenario_payload = dict(sel['params'])
                scenario_payload.update({
                    'scenario_name': f"custom__{sel['name']}",
                    'pop_factor': float(pop_factor),
                    'centralized_treatment_enabled': bool(full_ct),
                    'od_reduction_percent': float(od_red),
                    'infrastructure_upgrade_percent': float(upgrade),
                    'fecal_sludge_treatment_percent': float(fecal_sludge),
                })
                n_runner.run_scenario(scenario_payload)
        st.success('Nitrogen scenario outputs updated.')

    outs = _load_nitrogen_outputs()
    toggled = _legend_and_toggles({
        'show_nitrogen_loads': bool(tuned.get('show_nitrogen_loads', True)),
        'show_ward_boundaries': bool(tuned.get('show_ward_boundaries', False)),
    })
    
    deck = _webgl_deck_nitrogen(
        outs['nitrogen_loads'],
        show_nitrogen_loads=bool(toggled.get('show_nitrogen_loads', True)),
        show_ward_boundaries=bool(toggled.get('show_ward_boundaries', False))
    )
    st.pydeck_chart(deck, use_container_width=True)


if __name__ == '__main__':
    main()
