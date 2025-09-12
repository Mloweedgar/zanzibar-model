"""FIO transport and dilution calculations (app, Layers 2-3)."""

import pandas as pd
import numpy as np
import logging
from typing import List
try:
    from sklearn.neighbors import BallTree
except Exception:  # Optional dependency; clearer error later if missing
    BallTree = None  # type: ignore

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
    # Assume consistent column names in inputs: require 'lat' and 'long'
    if 'lat' not in df.columns or 'long' not in df.columns:
        raise ValueError(f"Missing required columns 'lat'/'long' in {path_in}. Available: {list(df.columns)}")
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['long'] = pd.to_numeric(df['long'], errors='coerce')
    before_clean = len(df)
    df = df.dropna(subset=['lat', 'long'])
    after_clean = len(df)
    if before_clean != after_clean:
        logging.warning(f"Dropped {before_clean - after_clean} boreholes with missing coordinates")
    # Ensure a stable ID column exists
    if 'id' not in df.columns:
        df['id'] = [f"{prefix}_{i:03d}" for i in range(len(df))]
    df['id'] = df['id'].astype(str)
    df.to_csv(path_out, index=False)
    logging.info(f"Saved boreholes with IDs to {path_out} ({len(df)} records)")
    return df


def link_sources_to_boreholes(toilets_df: pd.DataFrame, bores_df: pd.DataFrame, borehole_type: str, ks_per_m: float, radius_m: float, batch_size: int = 1000, scenario_name: 'str | None' = None, use_cache: bool = True) -> pd.DataFrame:
    """
    Link household sources (toilets) to nearby boreholes and compute distance-decayed surviving loads.

    What this does (high-level):
    - For each toilet with positive fio_load, find all boreholes within `radius_m` meters
    - For each toilet→borehole pair, compute surviving_fio_load = fio_load × exp(−ks_per_m × distance_m)
    - Return one row per pair with the distance and surviving_fio_load

    Parameters
    - toilets_df: DataFrame with columns ['id','lat','long','fio_load'] (fio_load in CFU/day)
    - bores_df:   DataFrame with columns ['id','lat','long'] for boreholes
    - borehole_type: string label (e.g., 'private' or 'government') added to output rows
    - ks_per_m:     exponential decay rate per meter (1/m). Higher → stronger distance decay
    - radius_m:     maximum distance to link (meters)
    - batch_size:   process toilets in batches to limit memory
    - scenario_name/use_cache: optional adjacency cache for faster re-runs

    Returns
    - DataFrame with columns: ['toilet_id','toilet_lat','toilet_long','borehole_id','borehole_type','distance_m','surviving_fio_load']

    Raises
    - ValueError if required inputs/columns are missing or empty
    - ImportError if scikit-learn (BallTree) is not available
    """

    logging.info(f"Linking {len(toilets_df)} toilets to {len(bores_df)} {borehole_type} boreholes (radius: {radius_m}m)")
    # 1) Validate inputs and preconditions
    require_columns(toilets_df, 'toilets_df', ['id','lat','long','fio_load'])
    if toilets_df.empty:
        raise ValueError("No toilets available for linking (empty toilets_df).")
    if bores_df.empty:
        raise ValueError(f"No {borehole_type} boreholes available for linking (empty input after validation).")
    require_columns(bores_df, 'bores_df', ['id','lat','long'])
    # Keep only toilets with positive fio_load; others cannot contribute to links
    valid_toilets = toilets_df[(toilets_df['fio_load'].notna()) & (toilets_df['fio_load'] > 0)].copy()
    if valid_toilets.empty:
        raise ValueError("No toilets with positive fio_load available for linking.")

    # Try cache of adjacency pairs (toilet_id, borehole_id, distance_m) in derived dir
    adjacency_df: pd.DataFrame | None = None
    cache_path = None
    if use_cache and scenario_name:
        try:
            fname = config.SPATIAL_ADJ_CACHE_PREFIX.format(scenario=scenario_name, bh_type=borehole_type, radius_m=int(radius_m))
            cache_path = config.DERIVED_DATA_DIR / fname
            if cache_path.exists():
                adjacency_df = pd.read_csv(cache_path)
                logging.info(f"Loaded cached adjacency pairs from {cache_path} ({len(adjacency_df)} rows)")
        except Exception as e:
            logging.warning(f"Failed to load spatial adjacency cache: {e}")

    # If we have a cached adjacency (toilet_id, borehole_id, distance), reuse it to skip neighbor search
    if adjacency_df is not None and not adjacency_df.empty:
        base = valid_toilets[['id','lat','long','fio_load']].rename(columns={'id':'toilet_id','lat':'toilet_lat','long':'toilet_long'})
        links_df = adjacency_df.merge(base, on='toilet_id', how='inner')
        links_df['borehole_type'] = borehole_type
        links_df['surviving_fio_load'] = links_df['fio_load'] * np.exp(-ks_per_m * links_df['distance_m'])
        return links_df[['toilet_id','toilet_lat','toilet_long','borehole_id','borehole_type','distance_m','surviving_fio_load']]

    if BallTree is None:
        raise ImportError("scikit-learn is required for fast spatial linking. Please add 'scikit-learn' to requirements and install.")

    # 3) Build a spatial index on boreholes in radians (BallTree with Haversine great-circle distance)
    bores_rad = np.radians(bores_df[['lat','long']].to_numpy(dtype=float))
    tree = BallTree(bores_rad, metric='haversine')

    # Convert the search radius from meters to radians, and choose a safe batch size
    earth_radius_m = 6371000.0
    radius_rad = float(radius_m) / earth_radius_m
    batch_size = int(batch_size) if batch_size and batch_size > 0 else 20000

    # Prepare numpy arrays for fast math inside the loop
    links_records = []                 # output rows (to build a DataFrame at the end)
    adjacency_records = []             # optional adjacency cache rows
    toilet_ids = valid_toilets['id'].to_numpy()
    toilet_lat = valid_toilets['lat'].to_numpy(dtype=float)
    toilet_lon = valid_toilets['long'].to_numpy(dtype=float)
    toilet_load = valid_toilets['fio_load'].to_numpy(dtype=float)

    # 4) Process toilets in batches to keep memory bounded
    for start in range(0, len(valid_toilets), batch_size):
        end = start + batch_size
        # Convert this batch of toilets to radians and find nearby boreholes
        pts_rad = np.radians(np.column_stack((toilet_lat[start:end], toilet_lon[start:end])))
        # ind_array and dist_array are ragged: one array of neighbor indices and distances per toilet
        ind_array, dist_array = tree.query_radius(pts_rad, r=radius_rad, return_distance=True, sort_results=False)

        # Expand ragged results: for each toilet in the batch, create rows for each nearby borehole
        for local_idx, (bh_indices, bh_dists_rad) in enumerate(zip(ind_array, dist_array)):
            if len(bh_indices) == 0:
                continue
            t_idx = start + local_idx
            # Convert neighbor distances to meters and compute surviving load via exponential decay
            dists_m = bh_dists_rad * earth_radius_m
            surv = toilet_load[t_idx] * np.exp(-ks_per_m * dists_m)
            for bore_idx, d_m, s_load in zip(bh_indices, dists_m, surv):
                links_records.append((
                    toilet_ids[t_idx],
                    toilet_lat[t_idx],
                    toilet_lon[t_idx],
                    bores_df.iloc[bore_idx]['id'],
                    borehole_type,
                    float(d_m),
                    float(s_load),
                ))
                adjacency_records.append((
                    toilet_ids[t_idx],
                    bores_df.iloc[bore_idx]['id'],
                    float(d_m),
                ))

    if not links_records:
        # No links at all (e.g., radius too small) → return an empty, well-typed table
        return pd.DataFrame(columns=['toilet_id','toilet_lat','toilet_long','borehole_id','borehole_type','distance_m','surviving_fio_load'])

    links_df = pd.DataFrame.from_records(
        links_records,
        columns=['toilet_id','toilet_lat','toilet_long','borehole_id','borehole_type','distance_m','surviving_fio_load']
    )
    # 5) Optionally save the adjacency cache for faster neighbor lookups next time
    if use_cache and scenario_name and cache_path is not None:
        try:
            adj_df = pd.DataFrame.from_records(adjacency_records, columns=['toilet_id','borehole_id','distance_m'])
            adj_df.to_csv(cache_path, index=False)
            logging.info(f"Saved adjacency cache to {cache_path} ({len(adj_df)} rows)")
        except Exception as e:
            logging.warning(f"Failed to save spatial adjacency cache: {e}")
    return links_df


def compute_borehole_concentrations(links_df: pd.DataFrame, bh_q_df: pd.DataFrame) -> pd.DataFrame:
    if links_df.empty:
        raise ValueError("No toilet→borehole links available to compute concentrations. Increase radius or check inputs.")
    # Assume bh_q_df provides ['id','Q_L_per_day']; inner-join to keep matched rows only
    links_with_Q = links_df.merge(bh_q_df[['id','Q_L_per_day']], left_on='borehole_id', right_on='id', how='inner')
    if links_with_Q.empty:
        raise ValueError("No borehole flows matched to links; check borehole IDs.")

    borehole_agg = (
        links_with_Q
        .groupby('borehole_id', as_index=False)
        .agg({'borehole_type':'first','surviving_fio_load':'sum','Q_L_per_day':'first'})
        .rename(columns={'surviving_fio_load':'total_surviving_fio_load'})
    )
    borehole_agg['concentration_CFU_per_100mL'] = (
        (borehole_agg['total_surviving_fio_load'] / borehole_agg['Q_L_per_day']) / 10.0
    )
    borehole_agg[['borehole_id','borehole_type','Q_L_per_day','total_surviving_fio_load','concentration_CFU_per_100mL']].to_csv(
        config.FIO_CONCENTRATION_AT_BOREHOLES_PATH, index=False
    )
    return borehole_agg[['borehole_id','borehole_type','Q_L_per_day','total_surviving_fio_load','concentration_CFU_per_100mL']]
