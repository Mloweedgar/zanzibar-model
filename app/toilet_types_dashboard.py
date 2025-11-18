"""Toilet Types dashboard showing only toilet category markers and legend."""

from typing import Dict, Any
import json

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

try:
    from app import fio_config as config
    from app.streamlit_media import dataframe_to_media_url
except Exception:
    from . import fio_config as config
    from .streamlit_media import dataframe_to_media_url


def _load_nitrogen_points() -> pd.DataFrame:
    p = config.NET_NITROGEN_LOAD_PATH
    if p.exists():
        df = pd.read_csv(p)
        cols = [c for c in ['id','lat','long','toilet_category_id','nitrogen_load'] if c in df.columns]
        df = df[cols].dropna(subset=['lat','long']).copy()
        # Downcast
        try:
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce').astype('float32')
            df['long'] = pd.to_numeric(df['long'], errors='coerce').astype('float32')
            if 'nitrogen_load' in df.columns:
                df['nitrogen_load'] = pd.to_numeric(df['nitrogen_load'], errors='coerce').astype('float32')
            df['toilet_category_id'] = pd.to_numeric(df['toilet_category_id'], errors='coerce').fillna(0).astype('int8')
        except Exception:
            pass
        return df
    return pd.DataFrame(columns=['id','lat','long','toilet_category_id','nitrogen_load'])


def _legend() -> None:
    html = """
    <style>
    .legend-top { display: flex; align-items: center; gap: 16px; margin: 8px 0 6px 0; padding: 10px 12px; background: #ffffff;
                  border: 1px solid #e0e0e0; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); font-size: 13px; }
    .legend-top .title { font-weight: 600; margin-right: 6px; color: #333; }
    .legend-top .entry { display: inline-flex; align-items: center; gap: 6px; color: #333; }
    .legend-top .dot { width: 10px; height: 10px; border-radius: 50%%; display: inline-block; }
    .legend-top .sep { width: 1px; height: 14px; background: #e0e0e0; margin: 0 2px; }
    </style>
    <div class="legend-top">
      <div class="title">Toilet Types:</div>
      <div class="entry"><span class="dot" style="background:#2ecc71"></span>Sewered </div>
      <div class="sep"></div>
      <div class="entry"><span class="dot" style="background:#f39c12"></span>Pit Latrine </div>
      <div class="sep"></div>
      <div class="entry"><span class="dot" style="background:#3498db"></span>Septic </div>
      <div class="sep"></div>
      <div class="entry"><span class="dot" style="background:#e74c3c"></span>Open Defecation </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def _color_from_toilet_type(cat_id: int) -> list[int]:
    try:
        m = {
            1: [46, 204, 113, 200],
            2: [243, 156, 18, 200],
            3: [52, 152, 219, 200],
            4: [231, 76, 60, 200],
        }
        return m.get(int(cat_id), [160,160,160,200])
    except Exception:
        return [160,160,160,200]


def main():
    # page config set by parent dashboard
    st.subheader('Toilet Types Map')

    df = _load_nitrogen_points()
    if df.empty:
        st.info('No nitrogen points available. Run nitrogen pipeline first.')
        return

    # Display summary statistics - distribution counts
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Households", f"{len(df):,}")
    
    with col2:
        sewered_count = len(df[df['toilet_category_id'] == 1])
        st.metric("Sewered", f"{sewered_count:,}")
    
    with col3:
        pit_count = len(df[df['toilet_category_id'] == 2])
        st.metric("Pit Latrine", f"{pit_count:,}")
    
    with col4:
        septic_count = len(df[df['toilet_category_id'] == 3])
        st.metric("Septic", f"{septic_count:,}")
    
    with col5:
        od_count = len(df[df['toilet_category_id'] == 4])
        st.metric("Open Defecation", f"{od_count:,}")

    # derive colors
    df['toilet_color'] = df['toilet_category_id'].apply(_color_from_toilet_type)

    # optional sampling to keep payload small
    MAX_POINTS = 150_000
    if len(df) > MAX_POINTS:
        try:
            df = df.groupby('toilet_category_id', group_keys=False, observed=True).apply(
                lambda g: g.sample(n=max(1, int(len(g) * (MAX_POINTS / len(df)))), random_state=42)
            )
        except Exception:
            df = df.sample(n=MAX_POINTS, random_state=42)

    _legend()

    # Individual layer toggle controls
    st.markdown("**Toggle Layers:** *Use checkboxes below to show/hide specific toilet types*")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        show_sewered = st.checkbox('Sewered', value=True, key='sewered_toggle')
    with col2:
        show_pit_latrine = st.checkbox('Pit Latrine', value=True, key='pit_toggle')
    with col3:
        show_septic = st.checkbox('Septic', value=True, key='septic_toggle')
    with col4:
        show_open_defecation = st.checkbox('Open Defecation', value=True, key='od_toggle')
    
    # Ward boundaries toggle
    show_ward_boundaries = st.checkbox('Ward boundaries', value=False)

    # Filter data based on checkbox selections
    filtered_data = df.copy()
    
    # Create a list to track which categories to show
    categories_to_show = []
    if show_sewered:
        categories_to_show.append(1)
    if show_pit_latrine:
        categories_to_show.append(2)
    if show_septic:
        categories_to_show.append(3)
    if show_open_defecation:
        categories_to_show.append(4)
    
    # Filter the dataframe
    if categories_to_show:
        filtered_data = filtered_data[filtered_data['toilet_category_id'].isin(categories_to_show)]
    else:
        # If no categories are selected, show empty dataframe
        filtered_data = filtered_data[filtered_data['toilet_category_id'] == -1]

    view_state = pdk.ViewState(latitude=-6.165, longitude=39.202, zoom=10, pitch=0)
    layers = []
    
    # Only create the layer if there's data to show
    if not filtered_data.empty:
        layer_data = dataframe_to_media_url(filtered_data, label="toilet-types") or filtered_data
        layer = pdk.Layer(
            'ScatterplotLayer',
            data=layer_data,
            get_position='[long, lat]',
            get_fill_color='toilet_color',
            radius_min_pixels=4,
            radius_max_pixels=4,
            pickable=False,
            stroked=True,
            get_line_color='[0,0,0,100]',
            line_width_min_pixels=1,
            opacity=0.85,
            id='layer-toilet-types-only'
        )
        layers.append(layer)

    # Ward boundaries layer (optional)
    if show_ward_boundaries:
        try:
            import json as _json
            p = config.INPUT_DATA_DIR / 'wards.geojson'
            if p.exists():
                with open(p, 'r', encoding='utf-8') as fh:
                    wards_geo = _json.load(fh)
                layers.append(pdk.Layer(
                    'GeoJsonLayer',
                    data=wards_geo,
                    stroked=True,
                    filled=True,
                    get_fill_color='[0,0,0,0]',
                    get_line_color='[40,40,40,160]',
                    line_width_min_pixels=1,
                    pickable=False,
                    id='layer-ward-outline'
                ))
        except Exception:
            pass

    deck = pdk.Deck(layers=layers, initial_view_state=view_state, map_style='https://basemaps.cartocdn.com/gl/positron-gl-style/style.json')
    st.pydeck_chart(deck, use_container_width=True)


if __name__ == '__main__':
    main()

