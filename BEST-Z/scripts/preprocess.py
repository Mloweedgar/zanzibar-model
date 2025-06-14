"""Cleaning and joining routines."""

import logging
from pathlib import Path
import pandas as pd
import geopandas as gpd
from . import ingest, config


def clean_households() -> pd.DataFrame:
    """Return household records with toilet info."""
    path = config.DATA_RAW / 'Zanzibar_Census_Data2022.csv'
    df = ingest.read_csv(path)
    df = df[df['H_INSTITUTION_TYPE'] == ' ']
    df = df[df['TOILET'].notnull() & (df['TOILET'].astype(str).str.strip() != '')]
    logging.info('Loaded %s household records', len(df))
    return df


def group_population(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate population per ward and toilet type."""
    cols = [
        'reg_name', 'H_DISTRICT_NAME', 'H_COUNCIL_NAME',
        'H_CONSTITUENCY_NAME', 'H_DIVISION_NAME', 'ward_name', 'TOILET'
    ]
    grouped = (
        df.groupby(cols)
        .size()
        .reset_index(name='population')
    )
    return grouped


def add_removal_efficiency(pop_df: pd.DataFrame) -> pd.DataFrame:
    """Join with removal efficiency table."""
    eff = ingest.read_csv(config.DATA_RAW / 'sanitation_removal_efficiencies_Zanzibar.csv')
    eff = eff[['toilet_type_id', 'nitrogen_removal_efficiency']]
    pop_df = pop_df.rename(columns={'TOILET': 'toilet_type_id'})
    eff['toilet_type_id'] = eff['toilet_type_id'].astype(str).str.strip()
    pop_df['toilet_type_id'] = pop_df['toilet_type_id'].astype(str).str.strip()
    merged = pop_df.merge(eff, on='toilet_type_id', how='left')
    return merged


def attach_geometry(n_load_df: pd.DataFrame) -> gpd.GeoDataFrame:
    """Attach ward polygons."""
    wards = ingest.read_geojson(config.DATA_RAW / 'unguja_wards.geojson')
    geo_cols = [
        'reg_name', 'dist_name', 'counc_name',
        'const_name', 'div_name', 'ward_name'
    ]
    wards[geo_cols] = wards[geo_cols].apply(lambda c: c.astype(str).str.lower().str.strip())
    key_cols = [
        'reg_name', 'H_DISTRICT_NAME', 'H_COUNCIL_NAME',
        'H_CONSTITUENCY_NAME', 'H_DIVISION_NAME', 'ward_name'
    ]
    n_load_df[key_cols] = n_load_df[key_cols].apply(lambda c: c.astype(str).str.lower().str.strip())
    gdf = wards.merge(n_load_df, left_on=geo_cols, right_on=key_cols, how='left')
    return gdf
