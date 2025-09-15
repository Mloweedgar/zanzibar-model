"""Core FIO model functions for data standardization and Layer 1 calculations (app).

- Standardize sanitation table
- Apply interventions (OD→septic, pit→septic)
- Compute Layer 1 fio_load = Pop × EFIO × (1 − η)
"""

import pandas as pd
import numpy as np
import logging
from typing import Tuple, Dict, Any

from . import fio_config as config


def standardize_sanitation_table(
    raw_path: str,
    out_path: str,
    category_eff_map: Dict[int, float],
    household_population_default: int
) -> pd.DataFrame:
    logging.info(f"Loading raw sanitation data from {raw_path}")
    df = pd.read_csv(raw_path)

    available_cols = set(df.columns)
    mapping_to_use = {k: v for k, v in config.SANITATION_COLUMN_MAPPING.items() if k in available_cols}
    if not mapping_to_use:
        raise ValueError(f"No expected columns found in {raw_path}. Available: {list(df.columns)}")

    df_mapped = df[list(mapping_to_use.keys())].rename(columns=mapping_to_use)

    required_cols = ['id', 'lat', 'long', 'toilet_category_id']
    missing_cols = [col for col in required_cols if col not in df_mapped.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns after mapping: {missing_cols}")

    df_mapped['lat'] = pd.to_numeric(df_mapped['lat'], errors='coerce')
    df_mapped['long'] = pd.to_numeric(df_mapped['long'], errors='coerce')
    df_mapped['toilet_category_id'] = pd.to_numeric(df_mapped['toilet_category_id'], errors='coerce')

    df_mapped['pathogen_containment_efficiency'] = df_mapped['toilet_category_id'].map(category_eff_map).fillna(0.0)
    df_mapped['household_population'] = household_population_default

    before_clean = len(df_mapped)
    df_mapped = df_mapped.dropna(subset=['lat', 'long'])
    after_clean = len(df_mapped)
    if before_clean != after_clean:
        logging.warning(f"Dropped {before_clean - after_clean} rows with missing coordinates")

    df_mapped.to_csv(out_path, index=False)
    logging.info(f"Saved standardized sanitation data to {out_path} ({len(df_mapped)} rows)")
    return df_mapped


def apply_interventions(df: pd.DataFrame, scenario: Dict[str, Any]) -> pd.DataFrame:
    df = df.copy()
    # Start from default containment efficiencies, allow scenario override per category id
    eff_map: Dict[int, float] = dict(config.CONTAINMENT_EFFICIENCY_DEFAULT)
    if 'efficiency_override' in scenario and isinstance(scenario['efficiency_override'], dict):
        for k, v in scenario['efficiency_override'].items():
            try:
                eff_map[int(k)] = float(v)
            except Exception:
                continue
    # Ensure the dataframe has the correct efficiency column consistent with categories
    if 'pathogen_containment_efficiency' not in df.columns:
        df['pathogen_containment_efficiency'] = df['toilet_category_id'].map(eff_map).fillna(0.0)

    pop_factor = scenario.get('pop_factor', 1.0)
    df['household_population'] = df['household_population'] * pop_factor

    od_reduction = scenario.get('od_reduction_percent', 0.0) / 100.0
    if od_reduction > 0:
        od_mask = df['toilet_category_id'] == 4
        if od_mask.any():
            converted_rows = df[od_mask].copy()
            converted_rows['household_population'] = converted_rows['household_population'] * od_reduction
            converted_rows['toilet_category_id'] = 3
            converted_rows['pathogen_containment_efficiency'] = float(eff_map.get(3, 0.80))
            df.loc[od_mask, 'household_population'] = df.loc[od_mask, 'household_population'] * (1 - od_reduction)
            df = pd.concat([df, converted_rows], ignore_index=True)

    upgrade_percent = scenario.get('infrastructure_upgrade_percent', 0.0) / 100.0
    if upgrade_percent > 0:
        pit_mask = df['toilet_category_id'] == 2
        if pit_mask.any():
            upgraded_rows = df[pit_mask].copy()
            upgraded_rows['household_population'] = upgraded_rows['household_population'] * upgrade_percent
            upgraded_rows['toilet_category_id'] = 3
            upgraded_rows['pathogen_containment_efficiency'] = float(eff_map.get(3, 0.90))
            df.loc[pit_mask, 'household_population'] = df.loc[pit_mask, 'household_population'] * (1 - upgrade_percent)
            df = pd.concat([df, upgraded_rows], ignore_index=True)

    centralized_treatment = 1.0 if bool(scenario.get('centralized_treatment_enabled', False)) else 0.0
    if centralized_treatment > 0:
        sewer_mask = df['toilet_category_id'] == 1
        if sewer_mask.any():
            # Set sewered efficiency to exactly 0.90
            df.loc[sewer_mask, 'pathogen_containment_efficiency'] = float(eff_map.get(1, 0.90))

    fecal_sludge_treatment = float(scenario.get('fecal_sludge_treatment_percent', 0.0)) / 100.0
    if fecal_sludge_treatment > 0:
        septic_mask = df['toilet_category_id'] == 3
        if septic_mask.any():
            # Convert the chosen fraction of septic rows below 0.80 to exactly 0.80,
            # preserving population mass via row splitting (like OD/pit conversions)
            eligible_mask = septic_mask & (df['pathogen_containment_efficiency'] < 0.80)
            if eligible_mask.any():
                converted_rows = df[eligible_mask].copy()
                converted_rows['household_population'] = converted_rows['household_population'] * fecal_sludge_treatment
                converted_rows['pathogen_containment_efficiency'] = 0.80
                df.loc[eligible_mask, 'household_population'] = df.loc[eligible_mask, 'household_population'] * (1 - fecal_sludge_treatment)
                df = pd.concat([df, converted_rows], ignore_index=True)

    df = df[df['household_population'] > 0].reset_index(drop=True)
    logging.info(f"Applied interventions: {len(df)} household records")
    return df


def compute_layer1_loads(df: pd.DataFrame, EFIO: float) -> pd.DataFrame:
    df = df.copy()
    df['fio_load'] = (
        df['household_population'] * EFIO * (1 - df['pathogen_containment_efficiency'])
    )
    df[['id', 'lat', 'long', 'fio_load']].to_csv(config.NET_PATHOGEN_LOAD_PATH, index=False)
    logging.info(f"Saved net pathogen load to {config.NET_PATHOGEN_LOAD_PATH} ({len(df)} records)")
    return df


def build_or_load_household_tables(scenario: Dict[str, Any]) -> pd.DataFrame:
    rebuild = bool(scenario.get('rebuild_standardized', False))

    eff_map = config.CONTAINMENT_EFFICIENCY_DEFAULT
    hh_default = config.HOUSEHOLD_POPULATION_DEFAULT

    need_build = rebuild or (not config.SANITATION_STANDARDIZED_PATH.exists())
    if not need_build:
        logging.info(f"Loading existing standardized data from {config.SANITATION_STANDARDIZED_PATH}")
        df = pd.read_csv(config.SANITATION_STANDARDIZED_PATH)
        missing_cols = [col for col in ['household_population', 'pathogen_containment_efficiency'] if col not in df.columns]
        if missing_cols:
            logging.info(f"Existing file missing required columns {missing_cols} - rebuilding from raw data")
            need_build = True

    if need_build:
        logging.info("Building standardized sanitation table from raw data")
        df = standardize_sanitation_table(
            raw_path=str(config.SANITATION_RAW_PATH),
            out_path=str(config.SANITATION_STANDARDIZED_PATH),
            category_eff_map=eff_map,
            household_population_default=hh_default,
        )

    df_with_interventions = apply_interventions(df, scenario)
    EFIO = scenario.get('EFIO_override') or config.EFIO_DEFAULT
    df_with_loads = compute_layer1_loads(df_with_interventions, EFIO)
    return df_with_loads
