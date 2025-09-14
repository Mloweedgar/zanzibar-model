"""Streamlit dashboard (app) using precomputed small CSVs."""

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
    from app import fio_runner
except Exception:
    from . import fio_config as config  # when imported as a package
    from . import fio_runner


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


def _load_outputs() -> Dict[str, pd.DataFrame]:
    outputs = {}
    paths = {
        'hh_loads_markers': config.DASH_TOILETS_MARKERS_PATH,
        'hh_loads_heat': config.DASH_TOILETS_HEATMAP_PATH,
        'priv_bh_dash': config.DASH_PRIVATE_BH_PATH,
        'gov_bh_dash': config.DASH_GOVERNMENT_BH_PATH,
        'bh_conc': config.FIO_CONCENTRATION_AT_BOREHOLES_PATH,
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

def _webgl_deck(priv_bh: pd.DataFrame, gov_bh: pd.DataFrame, toilets: pd.DataFrame, *, show_private: bool = True, show_government: bool = True, show_ward_load: bool = False, show_ward_boundaries: bool = False, highlight_borehole_id: Optional[str] = None, zoom_to_highlight: bool = True):
    """High-performance WebGL renderer using pydeck. Avoids clustering and handles large point sets smoothly."""

    center = [-6.165, 39.202]

    def prepare_bh(df: pd.DataFrame, default_type: str) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=['borehole_id','borehole_type','lat','long','concentration_CFU_per_100mL'])
        d = df.dropna(subset=['lat','long']).copy()
        if 'borehole_type' not in d.columns:
            d['borehole_type'] = default_type
        conc100 = pd.to_numeric(d.get('concentration_CFU_per_100mL', np.nan), errors='coerce')
        d['logC'] = np.log10(conc100.replace(0, np.nan))
        def cat(v: float) -> str:
                try:
                    x = float(v)
                except Exception:
                    return 'unknown'
                if pd.isna(x) or x < 0:
                    return 'unknown'
                if x < 10:
                    return 'low'
                if x < 100:
                    return 'moderate'
                if x < 1000:
                    return 'high'
                return 'very high'
        d['conc_category'] = conc100.apply(cat)
        # Ensure fields exist for tooltips
        for col in ['Q_L_per_day','lab_e_coli_CFU_per_100mL','lab_total_coliform_CFU_per_100mL','total_surviving_fio_load','borehole_id','borehole_type','concentration_CFU_per_100mL']:
            if col not in d.columns:
                d[col] = np.nan
        # Build per-row tooltip HTML for boreholes
        try:
            def _fmt(v):
                return _format_large(v)
            def _row_html(row: pd.Series) -> str:
                bid = str(row.get('borehole_id') or '-')
                btype = str(row.get('borehole_type') or '-')
                conc = _fmt(row.get('concentration_CFU_per_100mL'))
                lab = _fmt(row.get('lab_total_coliform_CFU_per_100mL'))
                return (
                    f"<div><b>{bid}</b> <small>({btype})</small><br>"
                    f"Calculated Concentration(By Model): <b>{conc} </b> CFU/100mL<br>"
                    f"Lab Total Coliform(E. coli): <b>{lab} </b> CFU/100mL<br>"
                )
            d['tooltip_html'] = d.apply(_row_html, axis=1)
        except Exception:
            d['tooltip_html'] = ''
        return d

    bh_priv = prepare_bh(priv_bh, 'private')
    bh_gov = prepare_bh(gov_bh, 'government')

    # Derive lab-based categories and colors for comparison (outline)
    def lab_color_from_value(v: float):
        try:
            x = float(v)
        except Exception:
            return [160, 160, 160, 180]
        if pd.isna(x) or x < 0:
            return [160, 160, 160, 180]
        if x < 10: return [46, 204, 113, 220]
        if x < 100: return [52, 152, 219, 220]
        if x < 1000: return [243, 156, 18, 220]
        return [231, 76, 60, 220]
    for d in (bh_priv, bh_gov):
        if not d.empty:
            lab_vals = pd.to_numeric(d.get('lab_total_coliform_CFU_per_100mL', np.nan), errors='coerce')
            d['lab_color_rgba'] = lab_vals.apply(lab_color_from_value)

    # Combined range for consistent size scaling
    logs = pd.concat([bh_priv['logC'].dropna(), bh_gov['logC'].dropna()], ignore_index=True)
    if len(logs) >= 2:
        vmin, vmax = float(np.nanpercentile(logs, 5)), float(np.nanpercentile(logs, 95))
        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
            vmin, vmax = float(logs.min()), float(logs.max())
    else:
        vmin, vmax = -1.0, 1.0

    def size_from_log(v: float) -> float:
        if pd.isna(v):
            return 3.0
        t = 0.0 if vmax == vmin else (float(v) - vmin) / (vmax - vmin)
        return 3.0 + 7.0 * max(0.0, min(1.0, t))

    def color_from_cat(c: str):
        c = (c or '').lower()
        if c == 'low': return [46, 204, 113, 200]      # green
        if c == 'moderate': return [52, 152, 219, 200] # blue
        if c == 'high': return [243, 156, 18, 200]     # orange
        if c == 'very high': return [231, 76, 60, 200] # red
        return [160, 160, 160, 200]                    # gray

    for d in (bh_priv, bh_gov):
        if not d.empty:
            d['size_px'] = d['logC'].apply(size_from_log).astype(float)
            d['color_rgba'] = d['conc_category'].apply(color_from_cat)

    # Enlarge government points slightly for clear distinction
    if not bh_gov.empty:
        try:
            bh_gov['size_px'] = (bh_gov['size_px'].astype(float) * 1.35 + 0.5).clip(lower=3.0)
        except Exception:
            pass

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

    # Map style handling: prefer Mapbox token if provided
    map_style = None
    mapbox_token = None
    try:
        mapbox_token = st.secrets.get('MAPBOX_API_KEY')  # type: ignore[attr-defined]
    except Exception:
        mapbox_token = None
    if mapbox_token:
        map_style = 'mapbox://styles/mapbox/light-v9'
    else:
        # Public CARTO GL style (no token required)
        map_style = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'

    # Add lightweight ward outline with hover-tooltips (ward name)
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
                visible=bool(show_ward_boundaries),
                id='layer-ward-outline'
            ))
    except Exception:
        pass

    # Unified tooltip content for all pickable layers
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
    od_red = st.sidebar.slider('Convert OD to septic (%)', 0, 100, int(st.session_state.get('od_reduction_percent', base.get('od_reduction_percent', 0))))
    upgrade = st.sidebar.slider('Upgrade pit latrines to septic (%)', 0, 100, int(st.session_state.get('infrastructure_upgrade_percent', base.get('infrastructure_upgrade_percent', 0))))
    fecal_sludge = st.sidebar.slider('Fecal sludge treatment (%)', 0, 100, int(st.session_state.get('fecal_sludge_treatment_percent', base.get('fecal_sludge_treatment_percent', 0))))
    full_ct = st.sidebar.checkbox('Centralized treatment (sewered)', value=bool(st.session_state.get('centralized_treatment_enabled', base.get('centralized_treatment_enabled', False))))
    
    # Inline advanced parameters
    pop_factor = st.sidebar.number_input('Population factor', min_value=0.1, max_value=5.0, value=float(st.session_state.get('pop_factor', base.get('pop_factor', 1.0))), step=0.05)
    # Removed map display sidebar to keep UI simple
    show_private = bool(base.get('show_private', True))
    show_government = bool(base.get('show_government', True))
    show_ward_load = bool(base.get('show_ward_load', False))
    show_ward_boundaries = bool(base.get('show_ward_boundaries', False))
    highlight_id = str(base.get('highlight_borehole_id') or '')
    zoom_to_highlight = bool(base.get('zoom_to_highlight', True))
    scenario = dict(base)
    scenario.update({
        'pop_factor': float(pop_factor),
        'centralized_treatment_enabled': bool(full_ct),
        'od_reduction_percent': float(od_red),
        'infrastructure_upgrade_percent': float(upgrade),
        'fecal_sludge_treatment_percent': float(fecal_sludge),
        'show_private': bool(show_private),
        'show_government': bool(show_government),
        'show_ward_load': bool(show_ward_load),
        'show_ward_boundaries': bool(show_ward_boundaries),
        'highlight_borehole_id': str(highlight_id).strip() if str(highlight_id).strip() else None,
        'zoom_to_highlight': bool(zoom_to_highlight)
    })
    return scenario


def _legend_and_toggles(defaults: Dict[str, bool]) -> Dict[str, bool]:
    # Legend bar
    html = """
<style>
.legend-top { display: flex; align-items: center; gap: 16px; margin: 8px 0 6px 0; padding: 10px 12px; background: #ffffff;
              border: 1px solid #e0e0e0; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); font-size: 13px; }
.legend-top .title { font-weight: 600; margin-right: 6px; color: #333; }
.legend-top .entry { display: inline-flex; align-items: center; gap: 6px; color: #333; }
.legend-top .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.legend-top .sep { width: 1px; height: 14px; background: #e0e0e0; margin: 0 2px; }
@media (max-width: 768px) { .legend-top { flex-wrap: wrap; gap: 10px; } }
</style>
<div class=\"legend-top\">
  <div class=\"title\">Concentration (CFU/100mL):</div>
  <div class=\"entry\"><span class=\"dot\" style=\"background:#2ecc71\"></span>Low</div>
  <div class=\"sep\"></div>
  <div class=\"entry\"><span class=\"dot\" style=\"background:#3498db\"></span>Moderate</div>
  <div class=\"sep\"></div>
  <div class=\"entry\"><span class=\"dot\" style=\"background:#f39c12\"></span>High</div>
  <div class=\"sep\"></div>
  <div class=\"entry\"><span class=\"dot\" style=\"background:#e74c3c\"></span>Very high</div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)
    # Streamlit toggles just below legend
    col1, col2, col3 = st.columns([3,3,2])
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

    sel = _scenario_selector()
    tuned = _tunable_controls(sel['params'])
    run_clicked = st.sidebar.button('Run scenario')
    if run_clicked:
        with st.spinner(f"Running pipeline for {sel['name']} (customized)..."):
            scenario_payload = dict(tuned)
            scenario_payload['scenario_name'] = f"custom__{sel['name']}"
            fio_runner.run_scenario(scenario_payload)
        st.success('Scenario outputs updated.')

    outs = _load_outputs()
    # Heatmap radius removed
    toggled = _legend_and_toggles({
        'show_private': bool(tuned.get('show_private', True)),
        'show_government': bool(tuned.get('show_government', True)),
        'show_ward_boundaries': bool(tuned.get('show_ward_boundaries', False)),
    })
    deck = _webgl_deck(
        outs['priv_bh_dash'],
        outs['gov_bh_dash'],
        outs['hh_loads_markers'],
        show_private=bool(toggled.get('show_private', True)),
        show_government=bool(toggled.get('show_government', True)),
        
        show_ward_load=False,
        show_ward_boundaries=bool(toggled.get('show_ward_boundaries', False)),
        highlight_borehole_id=tuned.get('highlight_borehole_id'),
        zoom_to_highlight=bool(tuned.get('zoom_to_highlight', True))
    )
    st.pydeck_chart(deck, use_container_width=True)

    # Charts removed per request


if __name__ == '__main__':
    main()


