"""Nitrogen dashboard using precomputed nitrogen load data."""

from pathlib import Path
from typing import Dict, Any, Optional
import os
import json

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

from app import tile_server

# Nitrogen dashboard configuration - CHANGE SCALE VALUES HERE ONLY
NITROGEN_SCALE_MIN = 20.0  # Fixed minimum scale value (kg N/year)
NITROGEN_SCALE_MAX = 45.0  # Fixed maximum scale value (kg N/year)


# Support both package and script execution
try:
    from app import fio_config as config  # when executed as a script by Streamlit
    from app import n_runner
except Exception:
    import sys
    from pathlib import Path
    # Add parent directory to path when running as script
    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    from app import fio_config as config
    from app import n_runner


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


def _webgl_deck_nitrogen(*, show_nitrogen_loads: bool = True, show_ward_boundaries: bool = False):
    """High-performance WebGL renderer backed by the local tile server."""

    center = [-6.165, 39.202]
    tile_server.start_tile_server()
    tile_url = tile_server.tile_url(limit=tile_server.MAX_FEATURES_PER_RESPONSE)

    layers = []
    view_state = pdk.ViewState(latitude=center[0], longitude=center[1], zoom=10, pitch=0)

    if show_nitrogen_loads:
        layers.append(
            pdk.Layer(
                'MVTLayer',
                data=tile_url,
                pickable=True,
                auto_highlight=True,
                filled=True,
                point_type='circle',
                get_fill_color='@=[properties.n_color_r, properties.n_color_g, properties.n_color_b, properties.n_color_a]',
                get_radius='properties.radius',
                point_radius_min_pixels=3,
                point_radius_max_pixels=15,
                visible=bool(show_nitrogen_loads),
                id='layer-nitrogen-mvt',
            )
        )

    # Ward boundaries
    try:
        p = config.INPUT_DATA_DIR / 'wards.geojson'
        if p.exists():
            with open(p, 'r', encoding='utf-8') as fh:
                wards_geo = json.load(fh)
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
            layers.append(
                pdk.Layer(
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
                )
            )
    except Exception:
        pass

    # Map style handling
    try:
        mapbox_token = st.secrets.get('MAPBOX_API_KEY')  # type: ignore[attr-defined]
    except Exception:
        mapbox_token = None
    if mapbox_token:
        map_style = 'mapbox://styles/mapbox/light-v9'
    else:
        map_style = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'

    tooltip = {
        'html': '{properties.tooltip_html}',
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
    # Continuous scale legend for nitrogen loads using colored blocks
    html = """
    <style>
    .legend-top {{ display: flex; align-items: center; gap: 16px; margin: 8px 0 6px 0; padding: 10px 12px; background: #ffffff;
                  border: 1px solid #e0e0e0; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); font-size: 13px; }}
    .legend-top .title {{ font-weight: 600; margin-right: 8px; color: #333; }}
    .legend-top .scale-container {{ display: flex; align-items: center; gap: 8px; }}
    .legend-top .scale-blocks {{ display: flex; width: 120px; height: 16px; border-radius: 4px; overflow: hidden; border: 1px solid #333; }}
    .legend-top .block {{ flex: 1; height: 100%; }}
    .legend-top .scale-labels {{ display: flex; justify-content: space-between; width: 120px; font-size: 11px; color: #666; margin-top: 2px; }}
    .legend-top .sep {{ width: 1px; height: 14px; background: #e0e0e0; margin: 0 8px; }}
    @media (max-width: 768px) {{ .legend-top {{ flex-wrap: wrap; gap: 10px; }} }}
    </style>
    <div class="legend-top">
      <div class="title">Nitrogen Load (kg N/year):</div>
      <div class="scale-container">
        <div style="display: flex; flex-direction: column; align-items: center;">
          <div class="scale-blocks">
            <div class="block" style="background-color: #2ecc71;"></div>
            <div class="block" style="background-color: #52ff52;"></div>
            <div class="block" style="background-color: #ffff00;"></div>
            <div class="block" style="background-color: #ff8000;"></div>
            <div class="block" style="background-color: #ff0000;"></div>
          </div>
          <div class="scale-labels">
            <span>{scale_min}</span>
            <span>{scale_max}</span>
          </div>
        </div>
      </div>
      <div class="sep"></div>
      <div style="font-size: 11px; color: #666;">Fixed scale for comparison</div>
    </div>
    """
    st.markdown(html.format(scale_min=int(NITROGEN_SCALE_MIN), scale_max=int(NITROGEN_SCALE_MAX)), unsafe_allow_html=True)
    
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
                st.cache_data.clear()
        st.success('Nitrogen scenario outputs updated.')

    outs = _load_nitrogen_outputs()

    # Display summary statistics and download
    if not outs['nitrogen_loads'].empty:
        nitrogen_data = outs['nitrogen_loads']
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Households", f"{len(nitrogen_data):,}")
        with col2:
            mean_load = nitrogen_data['nitrogen_load'].mean()
            st.metric("Average Load", f"{mean_load:.1f} kg N/year")
        with col3:
            max_load = nitrogen_data['nitrogen_load'].max()
            st.metric("Peak Load", f"{max_load:.1f} kg N/year")

        st.download_button(
            "Download full data (CSV)",
            data=nitrogen_data.to_csv(index=False),
            file_name="net_nitrogen_load_from_households.csv",
            mime="text/csv",
            help="Exports the full dataset without tiling limits",
        )
    
    toggled = _legend_and_toggles({
        'show_nitrogen_loads': bool(tuned.get('show_nitrogen_loads', True)),
        'show_ward_boundaries': bool(tuned.get('show_ward_boundaries', False)),
    })
    
    st.caption(f"Vector tiles served locally on port {tile_server.TILE_SERVER_PORT} (limit {tile_server.MAX_FEATURES_PER_RESPONSE} features per request)")

    deck = _webgl_deck_nitrogen(
        show_nitrogen_loads=bool(toggled.get('show_nitrogen_loads', True)),
        show_ward_boundaries=bool(toggled.get('show_ward_boundaries', False))
    )
    st.pydeck_chart(deck, use_container_width=True)


if __name__ == '__main__':
    main()
