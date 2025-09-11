"""Streamlit dashboard (app) using precomputed small CSVs."""

from pathlib import Path
from typing import Dict, Any
import json

import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import Fullscreen, HeatMap

# Support both package and script execution
try:
    from app import fio_config as config  # when executed as a script by Streamlit
    from app import fio_runner
except Exception:
    from . import fio_config as config  # when imported as a package
    from . import fio_runner


def _format_large(x: float) -> str:
    if pd.isna(x):
        return "-"
    a = abs(x)
    if a >= 1e12: return f"{x/1e12:.1f}T"
    if a >= 1e9: return f"{x/1e9:.1f}B"
    if a >= 1e6: return f"{x/1e6:.1f}M"
    if a >= 1e3: return f"{x/1e3:.1f}K"
    return f"{x:.0f}"


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


def _single_map(borehole_conc: pd.DataFrame, priv_bh: pd.DataFrame, gov_bh: pd.DataFrame, toilets: pd.DataFrame, *, heat_radius: int = 18) -> folium.Map:
    center = [-6.165, 39.202]
    m = folium.Map(location=center, zoom_start=10, control_scale=True)
    Fullscreen().add_to(m)

    bh_priv = priv_bh.dropna(subset=['lat','long']).copy() if not priv_bh.empty else pd.DataFrame(columns=['borehole_id','borehole_type','lat','long','Q_L_per_day','concentration_CFU_per_L','total_surviving_fio_load'])
    bh_gov = gov_bh.dropna(subset=['lat','long']).copy() if not gov_bh.empty else pd.DataFrame(columns=['borehole_id','borehole_type','lat','long','Q_L_per_day','concentration_CFU_per_L','total_surviving_fio_load'])
    if 'borehole_type' not in bh_priv.columns and not bh_priv.empty:
        bh_priv['borehole_type'] = 'private'
    if 'borehole_type' not in bh_gov.columns and not bh_gov.empty:
        bh_gov['borehole_type'] = 'government'

    for df in (bh_priv, bh_gov):
        if not df.empty:
            df['logC'] = np.log10(pd.to_numeric(df['concentration_CFU_per_L'], errors='coerce').replace(0, np.nan))

    def color_for(val: float, vmin: float, vmax: float) -> str:
        if pd.isna(val):
            return '#cccccc'
        t = 0.0 if vmax == vmin else (val - vmin) / (vmax - vmin)
        def lerp(a,b,t): return int(a + (b - a) * t)
        return f"#{lerp(255,189,t):02x}{lerp(255,0,t):02x}{lerp(178,38,t):02x}"

    # Private markers + heat
    priv_markers = folium.FeatureGroup(name='Private boreholes (markers)', show=True)
    if not bh_priv.empty:
        vmin_p, vmax_p = float(bh_priv['logC'].min(skipna=True)), float(bh_priv['logC'].max(skipna=True))
        for _, row in bh_priv.iterrows():
            logc = row.get('logC', np.nan)
            size = 4 if pd.isna(logc) else 4 + 6 * (0.0 if vmax_p == vmin_p else (logc - vmin_p) / (vmax_p - vmin_p))
            popup = (
                f"<b>{row.get('borehole_id')}</b><br>"
                f"Type: {row.get('borehole_type','-')}<br>"
                f"Q (L/day): {row.get('Q_L_per_day', '-'):,}<br>"
                f"Conc (CFU/L): {_format_large(row.get('concentration_CFU_per_L', np.nan))}<br>"
                f"Total load: {_format_large(row.get('total_surviving_fio_load', np.nan))}"
            )
            folium.CircleMarker([row['lat'], row['long']], radius=float(size), color=color_for(logc, vmin_p, vmax_p), fill=True, fill_opacity=0.7, popup=folium.Popup(popup, max_width=300), tooltip=f"{row.get('borehole_id')}").add_to(priv_markers)
    priv_markers.add_to(m)

    priv_heat = folium.FeatureGroup(name='Private boreholes (heatmap)', show=False)
    if not bh_priv.empty and bh_priv['logC'].notna().any():
        dfn = bh_priv.dropna(subset=['logC']).copy()
        if len(dfn) > 12000: dfn = dfn.nlargest(12000, 'logC')
        vmin, vmax = float(dfn['logC'].min()), float(dfn['logC'].max())
        denom = (vmax - vmin) if vmax != vmin else 1.0
        dfn['w'] = (dfn['logC'] - vmin) / denom
        HeatMap(dfn[['lat','long','w']].values.tolist(), radius=int(heat_radius), blur=int(max(10, heat_radius-4)), min_opacity=0.3, max_zoom=18).add_to(priv_heat)
    priv_heat.add_to(m)

    # Government markers + heat
    gov_markers = folium.FeatureGroup(name='Government boreholes (markers)', show=True)
    if not bh_gov.empty:
        vmin_g, vmax_g = float(bh_gov['logC'].min(skipna=True)), float(bh_gov['logC'].max(skipna=True))
        for _, row in bh_gov.iterrows():
            logc = row.get('logC', np.nan)
            size = 4 if pd.isna(logc) else 4 + 6 * (0.0 if vmax_g == vmin_g else (logc - vmin_g) / (vmax_g - vmin_g))
            popup = (
                f"<b>{row.get('borehole_id')}</b><br>"
                f"Type: {row.get('borehole_type','-')}<br>"
                f"Q (L/day): {row.get('Q_L_per_day', '-'):,}<br>"
                f"Conc (CFU/L): {_format_large(row.get('concentration_CFU_per_L', np.nan))}<br>"
                f"Total load: {_format_large(row.get('total_surviving_fio_load', np.nan))}"
            )
            folium.CircleMarker([row['lat'], row['long']], radius=float(size), color=color_for(logc, vmin_g, vmax_g), fill=True, fill_opacity=0.7, popup=folium.Popup(popup, max_width=300), tooltip=f"{row.get('borehole_id')}").add_to(gov_markers)
    gov_markers.add_to(m)

    gov_heat = folium.FeatureGroup(name='Government boreholes (heatmap)', show=False)
    if not bh_gov.empty and bh_gov['logC'].notna().any():
        dfn = bh_gov.dropna(subset=['logC']).copy()
        if len(dfn) > 12000: dfn = dfn.nlargest(12000, 'logC')
        vmin, vmax = float(dfn['logC'].min()), float(dfn['logC'].max())
        denom = (vmax - vmin) if vmax != vmin else 1.0
        dfn['w'] = (dfn['logC'] - vmin) / denom
        HeatMap(dfn[['lat','long','w']].values.tolist(), radius=int(heat_radius), blur=int(max(10, heat_radius-4)), min_opacity=0.3, max_zoom=18).add_to(gov_heat)
    gov_heat.add_to(m)

    # Toilets markers + heat
    toilets_markers = folium.FeatureGroup(name='Toilets net pathogen load (markers)', show=False)
    toilets_heat = folium.FeatureGroup(name='Toilets net pathogen load (heatmap)', show=False)
    th = toilets.dropna(subset=['lat','long']).copy()
    if not th.empty:
        th['logL'] = np.log10(pd.to_numeric(th['fio_load'], errors='coerce').replace(0, np.nan))
        if th['logL'].notna().any():
            vmin_t, vmax_t = float(th['logL'].min()), float(th['logL'].max())
            for _, row in th.iterrows():
                logl = row.get('logL', np.nan)
                size = 2 if pd.isna(logl) else 2 + 6 * (0.0 if vmax_t == vmin_t else (logl - vmin_t) / (vmax_t - vmin_t))
                popup = f"<b>{row.get('id')}</b><br>Net load (CFU/day): {_format_large(row.get('fio_load', np.nan))}"
                folium.CircleMarker([row['lat'], row['long']], radius=float(size), color=color_for(logl, vmin_t, vmax_t), fill=True, fill_opacity=0.6, popup=folium.Popup(popup, max_width=240), tooltip=f"{row.get('id')}").add_to(toilets_markers)
            dfn = th.dropna(subset=['logL']).copy()
            if len(dfn) > 20000: dfn = dfn.nlargest(20000, 'logL')
            denom = (vmax_t - vmin_t) if vmax_t != vmin_t else 1.0
            dfn['w'] = (dfn['logL'] - vmin_t) / denom
            HeatMap(dfn[['lat','long','w']].values.tolist(), radius=int(heat_radius), blur=int(max(10, heat_radius-4)), min_opacity=0.3, max_zoom=18).add_to(toilets_heat)
    toilets_markers.add_to(m)
    toilets_heat.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def _scenario_selector() -> Dict[str, Any]:
    names = list(config.SCENARIOS.keys())
    idx = names.index('crisis_2025_current') if 'crisis_2025_current' in names else 0
    selected = st.sidebar.selectbox('Scenario template', options=names, index=idx)
    return {"name": selected, "params": dict(config.SCENARIOS[selected])}


def _tunable_controls(base: Dict[str, Any]) -> Dict[str, Any]:
    st.sidebar.markdown('---')
    st.sidebar.subheader('Decision-maker settings')
    od_red = st.slider('Convert OD to septic (%)', 0, 100, int(base.get('od_reduction_percent', 0)))
    upgrade = st.slider('Upgrade pit latrines to septic (%)', 0, 100, int(base.get('infrastructure_upgrade_percent', 0)))
    st.sidebar.caption('Other settings are available under Advanced.')
    with st.sidebar.expander('Advanced system settings'):
        pop_factor = st.number_input('Population factor', min_value=0.1, max_value=5.0, value=float(base.get('pop_factor', 1.0)), step=0.05)
        ks_per_m = st.number_input('Spatial decay ks (1/m)', min_value=0.0, max_value=0.01, value=float(base.get('ks_per_m', config.KS_PER_M_DEFAULT)), step=0.0005, format='%0.4f')
        rbt = base.get('radius_by_type', config.RADIUS_BY_TYPE_DEFAULT)
        colr1, colr2 = st.columns(2)
        with colr1:
            r_priv = st.number_input('Private radius (m)', min_value=10, max_value=1000, value=int(rbt.get('private', 30)), step=5)
        with colr2:
            r_gov = st.number_input('Government radius (m)', min_value=10, max_value=2000, value=int(rbt.get('government', 100)), step=10)
        efio = st.text_input('EFIO override (CFU/person/day, blank = default)', value=str(base.get('EFIO_override') or ''))
        hh_default = st.number_input('Household pop default', min_value=1, max_value=30, value=int(base.get('household_population_default_override') or config.HOUSEHOLD_POPULATION_DEFAULT))
        flow_prefs_str = ','.join(config.FLOW_PREFERENCE_ORDER)
        qdefs = base.get('Q_defaults_by_type', config.Q_DEFAULTS_BY_TYPE)
        q_priv = st.number_input('Default Q private (L/day)', min_value=100.0, max_value=100000.0, value=float(qdefs.get('private', config.Q_DEFAULTS_BY_TYPE['private'])), step=100.0)
        q_gov = st.number_input('Default Q government (L/day)', min_value=100.0, max_value=1000000.0, value=float(qdefs.get('government', config.Q_DEFAULTS_BY_TYPE['government'])), step=500.0)
        batch_size = st.number_input('Linking batch size', min_value=100, max_value=20000, value=int(base.get('link_batch_size', 1000)), step=100)
        rebuild = st.checkbox('Rebuild standardized sanitation table from raw this run', value=bool(base.get('rebuild_standardized', False)))
        eff = base.get('containment_efficiency_override') or config.CONTAINMENT_EFFICIENCY_DEFAULT
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            eff1 = st.number_input('Cat 1 efficiency', min_value=0.0, max_value=1.0, value=float(eff.get(1, 0.8)), step=0.05)
            eff2 = st.number_input('Cat 2 efficiency', min_value=0.0, max_value=1.0, value=float(eff.get(2, 0.2)), step=0.05)
        with col_e2:
            eff3 = st.number_input('Cat 3 efficiency', min_value=0.0, max_value=1.0, value=float(eff.get(3, 0.9)), step=0.05)
            eff4 = st.number_input('Cat 4 efficiency', min_value=0.0, max_value=1.0, value=float(eff.get(4, 0.0)), step=0.05)
    scenario = dict(base)
    scenario.update({
        'pop_factor': float(pop_factor),
        'ks_per_m': float(ks_per_m),
        'od_reduction_percent': float(od_red),
        'infrastructure_upgrade_percent': float(upgrade),
        'radius_by_type': {'private': int(r_priv), 'government': int(r_gov)},
        'household_population_default_override': int(hh_default),
        'flow_preference_order': [s.strip() for s in flow_prefs_str.split(',') if s.strip()],
        'Q_defaults_by_type': {'private': float(q_priv), 'government': float(q_gov)},
        'containment_efficiency_override': {1: float(eff1), 2: float(eff2), 3: float(eff3), 4: float(eff4)},
        'link_batch_size': int(batch_size),
        'rebuild_standardized': bool(rebuild)
    })
    try:
        scenario['EFIO_override'] = float(efio) if efio.strip() else None
    except Exception:
        scenario['EFIO_override'] = None
    return scenario


def main():
    st.set_page_config(page_title='FIO Scenarios', layout='wide')
    st.title('FIO Scenarios')
    st.caption('Single map with layer controls; adjust OD→septic and pit→septic, then run')

    sel = _scenario_selector()
    tuned = _tunable_controls(sel['params'])
    run_clicked = st.sidebar.button('Run scenario')
    if run_clicked:
        with st.spinner(f"Running pipeline for {sel['name']} (customized)..."):
            fio_runner.run_scenario(tuned)
        st.success('Scenario outputs updated.')

    outs = _load_outputs()
    st.subheader('Map')
    if outs['bh_conc'].empty:
        st.info('No outputs available yet. Click "Run scenario" to generate outputs.')
    else:
        heat_radius = st.slider('Heatmap radius', min_value=8, max_value=32, value=18, step=2)
        m = _single_map(outs['bh_conc'], outs['priv_bh_dash'], outs['gov_bh_dash'], outs['hh_loads_markers'], heat_radius=heat_radius)
        st.components.v1.html(m._repr_html_(), height=720)


if __name__ == '__main__':
    main()
