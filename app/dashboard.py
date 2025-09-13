"""Streamlit dashboard (app) using precomputed small CSVs."""

from pathlib import Path
from typing import Dict, Any, Optional
import os
import json

import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import Fullscreen, HeatMap
try:
    # Fast clustered rendering for large point sets
    from folium.plugins import FastMarkerCluster
except Exception:
    FastMarkerCluster = None
import pydeck as pdk
try:
    from folium.features import RegularPolygonMarker
except Exception:
    RegularPolygonMarker = None
 

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


def _webgl_deck(priv_bh: pd.DataFrame, gov_bh: pd.DataFrame, toilets: pd.DataFrame, *, heat_radius: int = 18, show_private: bool = True, show_government: bool = True, show_ward_load: bool = False, show_ward_boundaries: bool = False, highlight_borehole_id: Optional[str] = None, zoom_to_highlight: bool = True):
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
            if x < 10: return 'low'
            if x < 100: return 'moderate'
            if x < 1000: return 'high'
            return 'very high'
        d['conc_category'] = conc100.apply(cat)
        # Ensure fields exist for tooltips
        for col in ['Q_L_per_day','lab_e_coli_CFU_per_100mL','lab_total_coliform_CFU_per_100mL','total_surviving_fio_load','borehole_id','borehole_type','concentration_CFU_per_100mL']:
            if col not in d.columns:
                d[col] = np.nan
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
            lab_vals = pd.to_numeric(d.get('lab_e_coli_CFU_per_100mL', np.nan), errors='coerce')
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
            pickable=False,
            auto_highlight=False,
            stroked=False,
            opacity=0.85,
            visible=bool(show_private),
            id='layer-priv-bh'
        ))
    if not bh_gov.empty:
        layers.append(pdk.Layer(
            'TextLayer',
            data=bh_gov,
            get_position='[long, lat]',
            get_text='"■"',
            get_color='color_rgba',
            get_size='size_px',
            size_scale=2.0,
            get_text_anchor='"middle"',
            get_alignment_baseline='"center"',
            pickable=False,
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
            # Try common ward name keys
            ward_name_keys = ['WARD_NAME','ward_name','Ward_Name','ward','name']
            def ward_name_accessor():
                # Build a JS accessor string to pick whichever property exists
                checks = []
                for k in ward_name_keys:
                    checks.append(f"f.properties && f.properties['{k}']")
                expr = ' || '.join(checks)
                return f"function(f){{ return ({expr}) || '' }}"
            layers.append(pdk.Layer(
                'GeoJsonLayer',
                data=wards_geo,
                stroked=True,
                filled=False,
                get_line_color='[40,40,40,160]',
                line_width_min_pixels=1,
                pickable=True,
                getTooltip={ 'text': ward_name_accessor() },
                visible=bool(show_ward_boundaries),
                id='layer-ward-outline'
            ))
    except Exception:
        pass

    # Disable default tooltip; we'll only show context on click via deck's default info panel
    tooltip = None

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=map_style,
        tooltip=tooltip,
    )
    if mapbox_token:
        deck.mapbox_key = mapbox_token
    return deck


def _single_map(borehole_conc: pd.DataFrame, priv_bh: pd.DataFrame, gov_bh: pd.DataFrame, toilets: pd.DataFrame, *, heat_radius: int = 18, cluster_markers: bool = True) -> folium.Map:
    center = [-6.165, 39.202]
    m = folium.Map(location=center, zoom_start=10, control_scale=True, prefer_canvas=True)
    Fullscreen().add_to(m)

    bh_priv = priv_bh.dropna(subset=['lat','long']).copy() if not priv_bh.empty else pd.DataFrame(columns=['borehole_id','borehole_type','lat','long','Q_L_per_day','concentration_CFU_per_100mL','total_surviving_fio_load'])
    bh_gov = gov_bh.dropna(subset=['lat','long']).copy() if not gov_bh.empty else pd.DataFrame(columns=['borehole_id','borehole_type','lat','long','Q_L_per_day','concentration_CFU_per_100mL','total_surviving_fio_load'])
    if 'borehole_type' not in bh_priv.columns and not bh_priv.empty:
        bh_priv['borehole_type'] = 'private'
    if 'borehole_type' not in bh_gov.columns and not bh_gov.empty:
        bh_gov['borehole_type'] = 'government'

    for df in (bh_priv, bh_gov):
        if not df.empty:
            conc100 = pd.to_numeric(df.get('concentration_CFU_per_100mL', np.nan), errors='coerce')
            df['logC'] = np.log10(conc100.replace(0, np.nan))
            # Ensure lab columns are numeric if present
            for lab_col in ['lab_e_coli_CFU_per_100mL', 'lab_total_coliform_CFU_per_100mL']:
                if lab_col in df.columns:
                    df[lab_col] = pd.to_numeric(df[lab_col], errors='coerce')
            # Concentration categories for popups
            def _cat(v: float) -> str:
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
            df['conc_category'] = conc100.apply(_cat)

    def color_for(val: float, vmin: float, vmax: float) -> str:
        if pd.isna(val):
            return '#cccccc'
        t = 0.0 if vmax == vmin else (val - vmin) / (vmax - vmin)
        def lerp(a,b,t): return int(a + (b - a) * t)
        return f"#{lerp(255,189,t):02x}{lerp(255,0,t):02x}{lerp(178,38,t):02x}"

    # Category color mapping for marker pins (folium.Icon color names)
    def color_name_for_category(cat: str) -> str:
        c = (cat or '').lower()
        if c == 'low':
            return 'green'
        if c == 'moderate':
            return 'blue'
        if c == 'high':
            return 'orange'
        if c == 'very high':
            return 'red'
        return 'gray'

    # Hex colors for faster, canvas-rendered circle markers
    def hex_color_for_category(cat: str) -> str:
        c = (cat or '').lower()
        if c == 'low':
            return '#2ecc71'
        if c == 'moderate':
            return '#3498db'
        if c == 'high':
            return '#f39c12'
        if c == 'very high':
            return '#e74c3c'
        return '#7f8c8d'

    def add_legend(m: folium.Map) -> None:
        legend_html = (
            '<div style="position: fixed; bottom: 18px; left: 18px; z-index: 9999; background: white;'
            ' padding: 10px 12px; border: 1px solid #999; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.3); font-size: 12px;">'
            '<b>Legend</b><br>'
            '<div style="margin-top: 6px;">'
            '<span style="display:inline-block;width:10px;height:10px;background:#2c3e50;border-radius:50%;margin-right:6px;"></span> Private borehole (pin icon)<br>'
            '<span style="display:inline-block;width:10px;height:10px;background:#2c3e50;margin-right:6px;border:1px solid #2c3e50;"></span> Government borehole (square pin)<br>'
            '<div style="margin-top:6px;"><b>Concentration</b></div>'
            '<span style="display:inline-block;width:10px;height:10px;background:#2ecc71;margin-right:6px;"></span> Low (&lt;10)<br>'
            '<span style="display:inline-block;width:10px;height:10px;background:#3498db;margin-right:6px;"></span> Moderate (10–99)<br>'
            '<span style="display:inline-block;width:10px;height:10px;background:#f39c12;margin-right:6px;"></span> High (100–999)<br>'
            '<span style="display:inline-block;width:10px;height:10px;background:#e74c3c;margin-right:6px;"></span> Very high (≥1000)'
            '</div></div>'
        )
        m.get_root().html.add_child(folium.Element(legend_html))

    # Private markers + heat (prefer canvas circles; off by default for faster initial render)
    priv_markers = folium.FeatureGroup(name='Private boreholes (markers)', show=False)
    if not bh_priv.empty:
        use_cluster = bool(cluster_markers) and FastMarkerCluster is not None
        if use_cluster and len(bh_priv) > 500:
            dfn = bh_priv.copy()
            # Cap extremely large datasets to keep DOM light and interactions smooth
            if 'logC' in dfn.columns and len(dfn) > 15000:
                dfn = dfn.nlargest(15000, 'logC')
            data = []
            for _, row in dfn.iterrows():
                cat = row.get('conc_category', 'unknown')
                popup_html = (
                f"<b>{row.get('borehole_id')}</b><br>"
                f"Type: {row.get('borehole_type','-')}<br>"
                f"Conc (CFU/100mL): {_format_large(row.get('concentration_CFU_per_100mL', np.nan))}<br>"
                f"Category: {row.get('conc_category','-')}<br>"
            )
                data.append([
                    float(row['lat']),
                    float(row['long']),
                    popup_html,
                    str(cat)
                ])
            cb = (
                "function (row) {\n"
                "  var color = 'gray';\n"
                "  var c = String(row[3] || '').toLowerCase();\n"
                "  if (c === 'low') color = 'green';\n"
                "  else if (c === 'moderate') color = 'blue';\n"
                "  else if (c === 'high') color = 'orange';\n"
                "  else if (c === 'very high') color = 'red';\n"
                "  var marker = L.marker(new L.LatLng(row[0], row[1]), {\n"
                "    icon: L.AwesomeMarkers.icon({ icon: 'tint', prefix: 'fa', markerColor: color })\n"
                "  });\n"
                "  if (row[2]) { marker.bindPopup(row[2], {maxWidth: 300}); }\n"
                "  return marker;\n"
                "}"
            )
            FastMarkerCluster(data=data, callback=cb, options={'chunkedLoading': True}).add_to(priv_markers)
        else:
            dfn = bh_priv.copy()
            # For non-clustered rendering, also cap to avoid too many DOM nodes
            if 'logC' in dfn.columns and len(dfn) > 8000:
                dfn = dfn.nlargest(8000, 'logC')
            for _, row in dfn.iterrows():
                cat = row.get('conc_category', 'unknown')
                color_hex = hex_color_for_category(cat)
                # Keep popup lightweight to improve performance
                popup = (
                    f"<b>{row.get('borehole_id')}</b><br>"
                    f"Type: {row.get('borehole_type','-')}<br>"
                    f"Conc: {_format_large(row.get('concentration_CFU_per_100mL', np.nan))} CFU/100mL"
                )
                folium.CircleMarker(
                    [row['lat'], row['long']],
                    radius=4.5,
                    color=color_hex,
                    fill=True,
                    fill_color=color_hex,
                    fill_opacity=0.85,
                    weight=1,
                    popup=folium.Popup(popup, max_width=260),
                    tooltip=f"{row.get('borehole_id')}"
                ).add_to(priv_markers)
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

    # Government markers + heat (prefer canvas circles; off by default for faster initial render)
    gov_markers = folium.FeatureGroup(name='Government boreholes (markers)', show=False)
    if not bh_gov.empty:
        for _, row in bh_gov.iterrows():
            cat = row.get('conc_category', 'unknown')
            color_hex = hex_color_for_category(cat)
            popup = (
                f"<b>{row.get('borehole_id')}</b><br>"
                f"Type: {row.get('borehole_type','-')}<br>"
                f"Conc: {_format_large(row.get('concentration_CFU_per_100mL', np.nan))} CFU/100mL"
            )
            folium.CircleMarker(
                [row['lat'], row['long']],
                radius=5.0,
                color=color_hex,
                fill=True,
                fill_color=color_hex,
                fill_opacity=0.9,
                weight=1.5,
                popup=folium.Popup(popup, max_width=260),
                tooltip=f"{row.get('borehole_id')}"
            ).add_to(gov_markers)
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

    # Zoom gating: only draw marker layers when zoomed in to reduce load
    min_zoom_for_markers = 12
    script = f"""
    <script>
    var mapObj = {m.get_name()};
    var priv = {priv_markers.get_name()};
    var gov = {gov_markers.get_name()};
    function syncMarkerLayers() {{
      var z = mapObj.getZoom();
      if (z >= {min_zoom_for_markers}) {{
        if (!mapObj.hasLayer(priv)) mapObj.addLayer(priv);
        if (!mapObj.hasLayer(gov)) mapObj.addLayer(gov);
      }} else {{
        if (mapObj.hasLayer(priv)) mapObj.removeLayer(priv);
        if (mapObj.hasLayer(gov)) mapObj.removeLayer(gov);
      }}
    }}
    mapObj.on('zoomend', syncMarkerLayers);
    setTimeout(syncMarkerLayers, 0);
    </script>
    """
    m.get_root().html.add_child(folium.Element(script))

    folium.LayerControl(collapsed=False).add_to(m)
    add_legend(m)
    return m


def _scenario_selector() -> Dict[str, Any]:
    names = list(config.SCENARIOS.keys())
    idx = names.index('crisis_2025_current') if 'crisis_2025_current' in names else 0
    selected = st.sidebar.selectbox('Scenario template', options=names, index=idx)
    return {"name": selected, "params": dict(config.SCENARIOS[selected])}


def _tunable_controls(base: Dict[str, Any]) -> Dict[str, Any]:
    st.sidebar.markdown('---')
    st.sidebar.subheader('Decision-maker settings')
    od_red = st.sidebar.slider('Convert OD to septic (%)', 0, 100, int(base.get('od_reduction_percent', 0)))
    upgrade = st.sidebar.slider('Upgrade pit latrines to septic (%)', 0, 100, int(base.get('infrastructure_upgrade_percent', 0)))
    fecal_sludge = st.sidebar.slider('Fecal sludge treatment (%)', 0, 100, int(base.get('fecal_sludge_treatment_percent', 0)))
    full_ct = st.sidebar.checkbox('Centralized treatment (sewered)', value=bool(base.get('centralized_treatment_enabled', False)))
    heat_radius_sidebar = st.sidebar.slider('Heatmap radius', min_value=8, max_value=32, value=int(base.get('heatmap_radius', 18)), step=2)
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
        hh_default = config.HOUSEHOLD_POPULATION_DEFAULT
        # Q is now provided by enriched CSVs; keep UI minimal and avoid Q overrides
        batch_size = st.number_input('Linking batch size', min_value=100, max_value=20000, value=int(base.get('link_batch_size', 1000)), step=100)
        rebuild = st.checkbox('Rebuild standardized sanitation table from raw this run', value=bool(base.get('rebuild_standardized', False)))
        eff = config.CONTAINMENT_EFFICIENCY_DEFAULT
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
        'ks_per_m': float(ks_per_m),
        'centralized_treatment_enabled': bool(full_ct),
        'od_reduction_percent': float(od_red),
        'infrastructure_upgrade_percent': float(upgrade),
        'fecal_sludge_treatment_percent': float(fecal_sludge),
        'heatmap_radius': int(heat_radius_sidebar),
        'radius_by_type': {'private': int(r_priv), 'government': int(r_gov)},
        'link_batch_size': int(batch_size),
        'rebuild_standardized': bool(rebuild),
        'show_private': bool(show_private),
        'show_government': bool(show_government),
        'show_ward_load': bool(show_ward_load),
        'show_ward_boundaries': bool(show_ward_boundaries),
        'highlight_borehole_id': str(highlight_id).strip() if str(highlight_id).strip() else None,
        'zoom_to_highlight': bool(zoom_to_highlight)
    })
    try:
        scenario['EFIO_override'] = float(efio) if efio.strip() else None
    except Exception:
        scenario['EFIO_override'] = None
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
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        show_private = st.checkbox('Private', value=bool(defaults.get('show_private', True)))
    with col2:
        show_government = st.checkbox('Government', value=bool(defaults.get('show_government', True)))
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
            fio_runner.run_scenario(tuned)
        st.success('Scenario outputs updated.')

    outs = _load_outputs()
    heat_radius = int(tuned.get('heatmap_radius', 18))
    toggled = _legend_and_toggles({
        'show_private': bool(tuned.get('show_private', True)),
        'show_government': bool(tuned.get('show_government', True)),
        'show_ward_boundaries': bool(tuned.get('show_ward_boundaries', False)),
    })
    deck = _webgl_deck(
        outs['priv_bh_dash'],
        outs['gov_bh_dash'],
        outs['hh_loads_markers'],
        heat_radius=heat_radius,
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


