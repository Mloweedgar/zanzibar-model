"""Streamlit dashboard (app) using precomputed small CSVs."""

from pathlib import Path
from typing import Dict, Any, Optional
import os
import json
from functools import lru_cache

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
 

# Robust imports for both script and package execution
if __package__ in (None, ''):
    import sys as _sys
    THIS_DIR = Path(__file__).resolve().parent
    PARENT_DIR = THIS_DIR.parent
    if str(PARENT_DIR) not in _sys.path:
        _sys.path.insert(0, str(PARENT_DIR))
    from app import fio_config as config
    from app import fio_runner
else:
    from . import fio_config as config
    from . import fio_runner


@lru_cache(maxsize=1)
def _get_model_thresholds() -> tuple[float, float, float]:
    """Load model-side thresholds (CFU/100mL).

    Falls back to sensible defaults if calibration file is missing/invalid
    so the app can start and display data with default bins.
    """
    default_thresholds = (1e2, 1e3, 1e4)
    p = config.OUTPUT_DATA_DIR / 'calibration_mapping.json'
    try:
        if not p.exists():
            st.info("Using default thresholds. Run calibration to enable model-calibrated bins.")
            return default_thresholds
        with open(p, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        node = data.get('category_thresholds_model_CFU_per_100mL')
        if not isinstance(node, dict):
            st.warning("Missing thresholds in calibration_mapping.json; using defaults.")
            return default_thresholds
        t1 = float(node.get('Low_Upper', default_thresholds[0]))
        t2 = float(node.get('Moderate_Upper', default_thresholds[1]))
        t3 = float(node.get('High_Upper', default_thresholds[2]))
        if not (t1 > 0 and t2 > t1 and t3 > t2):
            st.warning("Invalid thresholds in calibration; using defaults.")
            return default_thresholds
        return (t1, t2, t3)
    except Exception:
        st.warning("Failed to load thresholds; using defaults.")
        return default_thresholds

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


@st.cache_data(show_spinner=False)
def _load_outputs(nrows: Optional[int] = None) -> Dict[str, pd.DataFrame]:
    outputs = {}
    # Only load what is needed for the map - core columns that should exist in both files
    cols_core = [
        'borehole_id','borehole_type','lat','long',
        'concentration_CFU_per_100mL','Q_L_per_day'
    ]
    # Optional columns that may exist in some files
    cols_optional = [
        'lab_total_coliform_CFU_per_100mL',
        'lab_e_coli_CFU_per_100mL',
        'total_surviving_fio_load'
    ]
    dtype_map = {
        'borehole_id': 'object',
        'borehole_type': 'object',
        'lat': 'float64',
        'long': 'float64',
        'concentration_CFU_per_100mL': 'float64',
        'lab_total_coliform_CFU_per_100mL': 'float64',
        'lab_e_coli_CFU_per_100mL': 'float64',
        'Q_L_per_day': 'float64',
        'total_surviving_fio_load': 'float64',
    }
    if nrows is None:
        try:
            nrows_env = os.environ.get('FIO_READ_NROWS')
            nrows = int(nrows_env) if nrows_env else None
        except Exception:
            nrows = None
    for key, path in (
        ('priv_bh_dash', config.DASH_PRIVATE_BH_PATH),
        ('gov_bh_dash', config.DASH_GOVERNMENT_BH_PATH),
    ):
        if path.exists():
            try:
                # First, try loading with pyarrow - don't restrict columns upfront
                df = pd.read_csv(
                    path,
                    nrows=nrows,
                    engine='pyarrow',
                    dtype={k: v for k, v in dtype_map.items() if k in cols_core}
                )
                # Filter to available columns after loading
                available_cols = [c for c in cols_core + cols_optional if c in df.columns]
                outputs[key] = df[available_cols]
            except Exception:
                try:
                    # Fallback to pandas default
                    df = pd.read_csv(
                        path,
                        nrows=nrows,
                        low_memory=False,
                        dtype={k: v for k, v in dtype_map.items() if k in cols_core}
                    )
                    # Filter to available columns after loading
                    available_cols = [c for c in cols_core + cols_optional if c in df.columns]
                    outputs[key] = df[available_cols]
                except Exception:
                    # Final fallback: load everything, no dtype constraints
                    outputs[key] = pd.read_csv(path, nrows=nrows)
        else:
            # Create empty DataFrame with core columns if file doesn't exist
            outputs[key] = pd.DataFrame(columns=cols_core)
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

def _webgl_deck(priv_bh: pd.DataFrame, gov_bh: pd.DataFrame, *, show_private: bool = True, show_government: bool = True, show_ward_load: bool = False, show_ward_boundaries: bool = False, highlight_borehole_id: Optional[str] = None, zoom_to_highlight: bool = True):
    """High-performance WebGL renderer using pydeck. Avoids clustering and handles large point sets smoothly."""

    center = [-6.165, 39.202]
    # Use calibrated model-side thresholds if available
    T1, T2, T3 = _get_model_thresholds()

    def prepare_bh(df: pd.DataFrame, default_type: str) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=['borehole_id','borehole_type','lat','long','concentration_CFU_per_100mL'])
        d = df.dropna(subset=['lat','long']).copy()
        if 'borehole_type' not in d.columns:
            d['borehole_type'] = default_type
        # Ensure fields exist for tooltips
        for col in ['Q_L_per_day','lab_e_coli_CFU_per_100mL','lab_total_coliform_CFU_per_100mL','total_surviving_fio_load','borehole_id','borehole_type','concentration_CFU_per_100mL']:
            if col not in d.columns:
                d[col] = np.nan
        # Vectorized category + color
        conc100 = pd.to_numeric(d.get('concentration_CFU_per_100mL', np.nan), errors='coerce')
        valid = conc100.where(conc100 >= 0)
        cats = pd.cut(valid, bins=[0, T1, T2, T3, np.inf], right=False, labels=['low','moderate','high','very high'])
        d['conc_category'] = cats.astype('object').fillna('unknown')
        color_map = {
            'low': [46, 204, 113, 200],
            'moderate': [52, 152, 219, 200],
            'high': [243, 156, 18, 200],
            'very high': [231, 76, 60, 200],
            'unknown': [160, 160, 160, 200],
        }
        d['color_rgba'] = d['conc_category'].map(color_map)
        return d

    bh_priv = prepare_bh(priv_bh, 'private')
    bh_gov = prepare_bh(gov_bh, 'government')

    # Limit number of points to keep first render fast (override via env FIO_MAX_POINTS)
    try:
        max_points = int(os.environ.get('FIO_MAX_POINTS', '8000'))
    except Exception:
        max_points = 8000
    def limit_points(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        if len(df) <= max_points:
            return df
        col = 'concentration_CFU_per_100mL'
        if col in df.columns:
            try:
                return df.nlargest(max_points, col)
            except Exception:
                return df.head(max_points)
        return df.head(max_points)
    bh_priv = limit_points(bh_priv)
    bh_gov = limit_points(bh_gov)

    # Use fixed marker sizes (private: 5 px, government: 7 px) so only color varies by concentration
    if not bh_priv.empty:
        bh_priv['size_px'] = 5.0
    if not bh_gov.empty:
        bh_gov['size_px'] = 7.0
    # Government layer already uses a black stroke in the ScatterplotLayer config below

    layers = []
    # Always create layers with explicit visibility; toggles control 'visible'
    if not bh_priv.empty:
        layers.append(pdk.Layer(
            'ScatterplotLayer',
            data=bh_priv,
            get_position='[long, lat]',
            get_fill_color='color_rgba',
            get_radius='size_px',
            radius_units='pixels',
            pickable=True,
            auto_highlight=True,
            stroked=False,
            opacity=0.85,
            visible=bool(show_private),
            id='layer-priv-bh'
        ))
    if not bh_gov.empty:
        layers.append(pdk.Layer(
            'ScatterplotLayer',
            data=bh_gov,
            get_position='[long, lat]',
            get_fill_color='color_rgba',
            get_radius='size_px',
            radius_units='pixels',
            pickable=True,
            auto_highlight=True,
            stroked=True,
            get_line_color='[0,0,0,220]',
            line_width_min_pixels=1.5,
            opacity=0.95,
            visible=bool(show_government),
            id='layer-gov-bh'
        ))

    # Toilets heatmap removed per user request

    # Highlight selected borehole by ID
    view_state = pdk.ViewState(latitude=center[0], longitude=center[1], zoom=10, pitch=0)
    if highlight_borehole_id:
        try:
            key = str(highlight_borehole_id).strip().casefold()
            cand = pd.concat([bh_priv, bh_gov], ignore_index=True)
            if not cand.empty and 'borehole_id' in cand.columns:
                cand['__id_key'] = cand['borehole_id'].astype(str).str.strip().str.casefold()
                chosen = cand[cand['__id_key'] == key].copy()
                if not chosen.empty:
                    chosen['size_highlight'] = (chosen.get('size_px', 6.0).astype(float) * 2.0) + 4.0
                    layers.append(pdk.Layer(
                        'ScatterplotLayer',
                        data=chosen,
                        get_position='[long, lat]',
                        get_fill_color='[255, 235, 59, 255]',  # yellow
                        get_radius='size_highlight',
                        radius_units='pixels',
                        pickable=False,
                        stroked=True,
                        get_line_color='[0,0,0,200]',
                        line_width_min_pixels=2,
                        opacity=1.0,
                        id='layer-highlight'
                    ))
                    if zoom_to_highlight:
                        lat0 = float(chosen.iloc[0]['lat'])
                        lon0 = float(chosen.iloc[0]['long'])
                        view_state = pdk.ViewState(latitude=lat0, longitude=lon0, zoom=14, pitch=0)
        except Exception:
            pass

    # Ward boundaries and choropleth removed; we'll add a lightweight hover-only outline below

    # Map style handling with graceful fallback when MAPBOX token is missing
    mapbox_token = None
    try:
        mapbox_token = st.secrets.get('MAPBOX_API_KEY')  # type: ignore[attr-defined]
    except Exception:
        mapbox_token = None
    if not mapbox_token:
        mapbox_token = os.environ.get('MAPBOX_API_KEY') or os.environ.get('MAPBOX_TOKEN')
    
    if mapbox_token:
        map_provider = 'mapbox'
        map_style = 'mapbox://styles/mapbox/light-v9'
    else:
        map_provider = 'carto'
        map_style = 'light'
        # Only show fallback message once using session state
        if 'mapbox_fallback_shown' not in st.session_state:
            st.info('Using fallback basemap (Carto). Set MAPBOX_API_KEY to enable Mapbox.')
            st.session_state.mapbox_fallback_shown = True

    # LAZY LOAD: Only load ward boundaries when enabled (avoid heavy startup I/O)
    if bool(show_ward_boundaries):
        try:
            p = config.INPUT_DATA_DIR / 'wards.geojson'
            if p.exists():
                with open(p, 'r', encoding='utf-8') as fh:
                    wards_geo = json.load(fh)
                # Flatten fields for tooltip token replacement (avoid nested properties path)
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
                    visible=True,
                    id='layer-ward-outline'
                ))
        except Exception:
            # Graceful fallback: continue without ward boundaries if loading fails
            pass

    # Unified tooltip using token references to avoid per-row string builds
    tooltip = {
        'html': (
            '<div><b>{borehole_id}</b> <small>({borehole_type})</small><br>'
            'Concentration (model): <b>{concentration_CFU_per_100mL}</b> CFU/100mL<br>'
            'Lab Total Coliform: <b>{lab_total_coliform_CFU_per_100mL}</b> CFU/100mL'
            '</div>'
        ),
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
        map_provider=map_provider,
        tooltip=tooltip,
    )
    try:
        if mapbox_token and hasattr(deck, 'mapbox_key'):
            deck.mapbox_key = mapbox_token
    except Exception:
        pass
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
    # Provide only visualization defaults and highlight options from base; scenario edits happen in the form
    scenario = {
        'show_private': bool(base.get('show_private', True)),
        'show_government': bool(base.get('show_government', True)),
        'show_ward_boundaries': bool(base.get('show_ward_boundaries', False)),
        'highlight_borehole_id': base.get('highlight_borehole_id'),
        'zoom_to_highlight': bool(base.get('zoom_to_highlight', True)),
    }
    return scenario


def _legend_and_toggles(defaults: Dict[str, bool]) -> Dict[str, bool]:
        # Load calibrated thresholds for legend labels (model-side, CFU/100mL)
        t1, t2, t3 = _get_model_thresholds()
        t1s, t2s, t3s = _format_large(t1), _format_large(t2), _format_large(t3)
        # Legend bar
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
      <div class="title">Concentration (CFU/100mL):</div>
      <div class="entry"><span class="dot" style="background:#2ecc71"></span>Low </div>
      <div class="sep"></div>
      <div class="entry"><span class="dot" style="background:#3498db"></span>Moderate </div>
      <div class="sep"></div>
      <div class="entry"><span class="dot" style="background:#f39c12"></span>High </div>
      <div class="sep"></div>
      <div class="entry"><span class="dot" style="background:#e74c3c"></span>Very high </div>
    </div>
    """ % {'t1s': t1s, 't2s': t2s, 't3s': t3s}
        st.markdown(html, unsafe_allow_html=True)
        # Streamlit toggles just below legend
        col1, col2, col3 = st.columns([3, 3, 2])
        with col1:
            show_private = st.checkbox('Pathogens Concentration - Private Wells', value=bool(defaults.get('show_private', True)))
        with col2:
            show_government = st.checkbox('Pathogens Concentration - ZAWA Boreholes', value=bool(defaults.get('show_government', True)))
        with col3:
            show_ward_boundaries = st.checkbox('Ward boundaries', value=bool(defaults.get('show_ward_boundaries', False)))
        return {
            'show_private': bool(show_private),
            'show_government': bool(show_government),
            'show_ward_boundaries': bool(show_ward_boundaries),
        }


def main():
    st.set_page_config(page_title='FIO Scenarios', layout='wide')

    # FAST FIRST RENDER: Show sidebar and legend immediately
    sel = _scenario_selector()
    tuned = _tunable_controls(sel['params'])

    # Single-submit scenario form: edits are buffered until submitted
    with st.sidebar.form('scenario_form'):
        st.markdown('#### Edit scenario settings')
        pop_factor = st.number_input('Population factor', min_value=0.1, max_value=5.0, value=float(sel['params'].get('pop_factor', 1.0)), step=0.05)
        full_ct = st.checkbox('Centralized treatment (sewered)', value=bool(sel['params'].get('centralized_treatment_enabled', False)))
        od_red = st.slider('Convert OD to septic (%)', 0, 100, int(sel['params'].get('od_reduction_percent', 0)))
        upgrade = st.slider('Upgrade pit latrines to septic (%)', 0, 100, int(sel['params'].get('infrastructure_upgrade_percent', 0)))
        fecal_sludge = st.slider('Fecal sludge treatment (%)', 0, 100, int(sel['params'].get('fecal_sludge_treatment_percent', 0)))

        submitted = st.form_submit_button('Run scenario')
        if submitted:
            with st.spinner(f"Running scenario pipeline..."):
                scenario_payload = dict(sel['params'])
                scenario_payload.update({
                    'scenario_name': f"custom__{sel['name']}",
                    'pop_factor': float(pop_factor),
                    'centralized_treatment_enabled': bool(full_ct),
                    'od_reduction_percent': float(od_red),
                    'infrastructure_upgrade_percent': float(upgrade),
                    'fecal_sludge_treatment_percent': float(fecal_sludge),
                })
                fio_runner.run_scenario(scenario_payload)
        st.success('Scenario outputs updated.')

    # Show legend and toggles BEFORE loading data (for responsive UI)
    toggled = _legend_and_toggles({
        'show_private': bool(tuned.get('show_private', True)),
        'show_government': bool(tuned.get('show_government', True)),
        'show_ward_boundaries': bool(tuned.get('show_ward_boundaries', False)),
    })

    # Create placeholder for progressive loading
    map_placeholder = st.empty()

    # PROGRESSIVE LOADING: First paint with small subset (5000 rows)
    with st.spinner('Loading initial data...'):
        outs = _load_outputs(nrows=5000)
    
    with st.spinner('Rendering map...'):
        deck = _webgl_deck(
            outs['priv_bh_dash'],
            outs['gov_bh_dash'],
            show_private=bool(toggled.get('show_private', True)),
            show_government=bool(toggled.get('show_government', True)),
            show_ward_load=False,
            show_ward_boundaries=bool(toggled.get('show_ward_boundaries', False)),
            highlight_borehole_id=tuned.get('highlight_borehole_id'),
            zoom_to_highlight=bool(tuned.get('zoom_to_highlight', True))
        )
        # Use placeholder for initial render
        map_placeholder.pydeck_chart(deck, use_container_width=True)

    # BACKGROUND UPGRADE: Load full data and update in place (no rerun)
    try:
        with st.spinner('Loading full dataset...'):
            full_outs = _load_outputs(nrows=None)
        
        # Only update if we have more data
        if len(full_outs['priv_bh_dash']) > len(outs['priv_bh_dash']) or len(full_outs['gov_bh_dash']) > len(outs['gov_bh_dash']):
            deck_full = _webgl_deck(
                full_outs['priv_bh_dash'],
                full_outs['gov_bh_dash'],
                show_private=bool(toggled.get('show_private', True)),
                show_government=bool(toggled.get('show_government', True)),
                show_ward_load=False,
                show_ward_boundaries=bool(toggled.get('show_ward_boundaries', False)),
                highlight_borehole_id=tuned.get('highlight_borehole_id'),
                zoom_to_highlight=bool(tuned.get('zoom_to_highlight', True))
            )
            # Update the same placeholder (no page rerun)
            map_placeholder.pydeck_chart(deck_full, use_container_width=True)
    except Exception:
        # Graceful fallback: continue with subset if full load fails
        pass

    # Charts removed per request


if __name__ == '__main__':
    main()


