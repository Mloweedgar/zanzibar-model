"""Nitrogen calculations."""

import pandas as pd
import logging
from . import config


def apply_scenario(pop_df: pd.DataFrame, scenario: dict) -> pd.DataFrame:
    """Return DataFrame with nitrogen load columns for a scenario."""
    df = pop_df.copy()
    df['population'] = df['population'] * scenario['pop_factor']
    df['nre'] = df['nitrogen_removal_efficiency']
    for ttype, val in scenario['nre_override'].items():
        mask = df['toilet_type_id'].str.lower() == ttype
        df.loc[mask, 'nre'] = val
    df['n_load_kg_y'] = (
        df['population'] * config.P_C * 365 * config.PTN * (1 - df['nre'])
    ) / 1000
    logging.info('Calculated nitrogen load for %s rows', len(df))
    return df


def aggregate_ward(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate nitrogen load to ward level."""
    group_cols = [
        'reg_name', 'H_DISTRICT_NAME', 'H_COUNCIL_NAME',
        'H_CONSTITUENCY_NAME', 'H_DIVISION_NAME', 'ward_name'
    ]
    ward = df.groupby(group_cols)['n_load_kg_y'].sum().reset_index()
    ward = ward.rename(columns={'n_load_kg_y': 'ward_total_n_load_kg'})
    return ward
