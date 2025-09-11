"""FIO transport and dilution calculations (app, Layers 2-3)."""

import pandas as pd
import numpy as np
import logging
from typing import Tuple, List, Dict

from . import fio_config as config


def require_columns(df: pd.DataFrame, df_name: str, required: List[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{df_name} missing columns: {missing}. Available: {list(df.columns)}")


def haversine_m(lat1: float, lon1: float, lat2_arr: np.ndarray, lon2_arr: np.ndarray) -> np.ndarray:
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2_arr)
    lon2_rad = np.radians(lon2_arr)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = (np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2)
    c = 2 * np.arcsin(np.sqrt(a))
    R = 6371000
    return R * c


def load_boreholes_with_ids(path_in: str, path_out: str, prefix: str) -> pd.DataFrame:
    logging.info(f"Loading borehole data from {path_in}")
    df = pd.read_csv(path_in)
    coord_mapping = {}
    for col in df.columns:
        cl = col.lower().strip()
        if cl in ['lat', 'latitude']:
            coord_mapping[col] = 'lat'
        elif cl in ['long', 'lon', 'longitude']:
            coord_mapping[col] = 'long'
    if coord_mapping:
        df = df.rename(columns=coord_mapping)
    if 'lat' not in df.columns or 'long' not in df.columns:
        raise ValueError(f"Could not find lat/long columns in {path_in}. Available: {list(df.columns)}")
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['long'] = pd.to_numeric(df['long'], errors='coerce')
    before_clean = len(df)
    df = df.dropna(subset=['lat', 'long'])
    after_clean = len(df)
    if before_clean != after_clean:
        logging.warning(f"Dropped {before_clean - after_clean} boreholes with missing coordinates")
    if 'id' not in df.columns:
        df['id'] = [f"{prefix}_{i:03d}" for i in range(len(df))]
    df['id'] = df['id'].astype(str)
    df.to_csv(path_out, index=False)
    logging.info(f"Saved boreholes with IDs to {path_out} ({len(df)} records)")
    return df


def link_sources_to_boreholes(toilets_df: pd.DataFrame, bores_df: pd.DataFrame, borehole_type: str, ks_per_m: float, radius_m: float, batch_size: int = 1000) -> pd.DataFrame:
    logging.info(f"Linking {len(toilets_df)} toilets to {len(bores_df)} {borehole_type} boreholes (radius: {radius_m}m)")
    require_columns(toilets_df, 'toilets_df', ['id','lat','long','fio_load'])
    if not bores_df.empty:
        require_columns(bores_df, 'bores_df', ['id','lat','long'])
    if bores_df.empty:
        return pd.DataFrame(columns=['toilet_id','toilet_lat','toilet_long','borehole_id','borehole_type','distance_m','surviving_fio_load'])
    valid_toilets = toilets_df[(toilets_df['fio_load'].notna()) & (toilets_df['fio_load'] > 0)].copy()
    if valid_toilets.empty:
        return pd.DataFrame(columns=['toilet_id','toilet_lat','toilet_long','borehole_id','borehole_type','distance_m','surviving_fio_load'])
    links = []
    batch_size = int(batch_size) if batch_size and batch_size > 0 else 1000
    for i in range(0, len(valid_toilets), batch_size):
        batch_toilets = valid_toilets.iloc[i:i+batch_size]
        for _, toilet in batch_toilets.iterrows():
            distances = haversine_m(toilet['lat'], toilet['long'], bores_df['lat'].values, bores_df['long'].values)
            within = distances <= radius_m
            if np.any(within):
                idxs = np.where(within)[0]
                ds = distances[within]
                for idx, d in zip(idxs, ds):
                    borehole = bores_df.iloc[idx]
                    links.append({
                        'toilet_id': toilet['id'],
                        'toilet_lat': toilet['lat'],
                        'toilet_long': toilet['long'],
                        'borehole_id': borehole['id'],
                        'borehole_type': borehole_type,
                        'distance_m': d,
                        'surviving_fio_load': toilet['fio_load'] * np.exp(-ks_per_m * d),
                    })
    return pd.DataFrame(links)


def pick_Q_L_per_day(df: pd.DataFrame, flow_prefs: List[str]) -> pd.Series:
    Q_series = pd.Series(index=df.index, dtype=float)
    for col_name in flow_prefs:
        if col_name in df.columns:
            valid_mask = df[col_name].notna() & Q_series.isna()
            valid_values = pd.to_numeric(df[col_name], errors='coerce')
            if valid_mask.any():
                if 'Lps' in col_name or 'L/s' in col_name:
                    Q_series.loc[valid_mask] = valid_values.loc[valid_mask] * 86400
                elif 'm3' in col_name or 'M3' in col_name:
                    Q_series.loc[valid_mask] = valid_values.loc[valid_mask] * 1000
                else:
                    Q_series.loc[valid_mask] = valid_values.loc[valid_mask]
    nonpos_mask = Q_series.notna() & (Q_series <= 0)
    if nonpos_mask.any():
        Q_series.loc[nonpos_mask] = np.nan
    return Q_series


def build_borehole_Q_map(df: pd.DataFrame, borehole_type: str, defaults_by_type: Dict[str, float], flow_prefs: 'List[str] | None' = None) -> pd.DataFrame:
    prefs = flow_prefs if flow_prefs else config.FLOW_PREFERENCE_ORDER
    Q_series = pick_Q_L_per_day(df, prefs)
    default_Q = defaults_by_type.get(borehole_type, 2000.0)
    Q_series = Q_series.fillna(default_Q)
    return pd.DataFrame({'id': df['id'], 'borehole_type': borehole_type, 'Q_L_per_day': Q_series})


def compute_borehole_concentrations(links_df: pd.DataFrame, bh_q_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if links_df.empty:
        empty_links = pd.DataFrame(columns=['toilet_id','toilet_lat','toilet_long','borehole_id','borehole_type','distance_m','surviving_fio_load','Q_L_per_day','concentration_CFU_per_L'])
        empty_boreholes = pd.DataFrame(columns=['borehole_id','borehole_type','total_surviving_fio_load','Q_L_per_day','concentration_CFU_per_L'])
        empty_links.to_csv(config.NET_SURVIVING_PATHOGEN_CONCENTRATION_LINKS_PATH, index=False)
        empty_boreholes.to_csv(config.FIO_CONCENTRATION_AT_BOREHOLES_PATH, index=False)
        return empty_links, empty_boreholes
    links_with_Q = links_df.merge(bh_q_df, left_on='borehole_id', right_on='id', how='left', suffixes=('', '_q'))
    if 'borehole_type_q' in links_with_Q.columns:
        links_with_Q = links_with_Q.drop('borehole_type_q', axis=1)
    if links_with_Q['Q_L_per_day'].isna().any():
        missing = links_with_Q[links_with_Q['Q_L_per_day'].isna()][['borehole_id','borehole_type']].drop_duplicates()
        raise ValueError(f"Missing Q for some boreholes; cannot compute concentrations. Examples:\n{missing.head(10).to_string(index=False)}")
    links_with_Q['concentration_CFU_per_L'] = links_with_Q['surviving_fio_load'] / links_with_Q['Q_L_per_day']
    links_with_Q['concentration_CFU_per_100mL'] = links_with_Q['concentration_CFU_per_L'] / 10.0
    borehole_agg = links_with_Q.groupby('borehole_id').agg({'borehole_type':'first','surviving_fio_load':'sum','Q_L_per_day':'first'}).reset_index()
    borehole_agg['concentration_CFU_per_L'] = borehole_agg['surviving_fio_load'] / borehole_agg['Q_L_per_day']
    borehole_agg['concentration_CFU_per_100mL'] = borehole_agg['concentration_CFU_per_L'] / 10.0
    borehole_agg = borehole_agg.rename(columns={'surviving_fio_load':'total_surviving_fio_load'})
    link_cols = ['toilet_id','toilet_lat','toilet_long','borehole_id','borehole_type','distance_m','surviving_fio_load','Q_L_per_day','concentration_CFU_per_L','concentration_CFU_per_100mL']
    links_output = links_with_Q[link_cols].copy()
    links_output.to_csv(config.NET_SURVIVING_PATHOGEN_CONCENTRATION_LINKS_PATH, index=False)
    borehole_agg.to_csv(config.FIO_CONCENTRATION_AT_BOREHOLES_PATH, index=False)
    return links_output, borehole_agg
