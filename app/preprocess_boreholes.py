"""Utilities to preprocess borehole inputs (e.g., derive Q_L_per_day, inspect unique values)."""

from __future__ import annotations

import pandas as pd
from pathlib import Path
from typing import Tuple

from . import fio_config as config


def _normalize_header(s: str) -> str:
    # Lowercase, collapse whitespace; safe for matching headers with newlines
    return " ".join(s.lower().split())


def _find_column(columns: list[str], include_substrings: Tuple[str, ...]) -> str | None:
    norm_map = {_normalize_header(c): c for c in columns}
    for norm, original in norm_map.items():
        if all(sub in norm for sub in include_substrings):
            return original
    return None


def extract_private_q_uniques() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Read private boreholes CSV and write distinct values for volume/refill columns to output dir.

    Returns two DataFrames (volume_uniques, refill_uniques) with counts, and writes them to disk.
    """
    path_in = config.PRIVATE_BOREHOLES_PATH
    if not path_in.exists():
        raise FileNotFoundError(f"Private boreholes file not found: {path_in}")

    df = pd.read_csv(path_in)
    vol_col = _find_column(list(df.columns), ("volume", "liter"))
    ref_col = _find_column(list(df.columns), ("refill",))
    if not vol_col or not ref_col:
        raise ValueError(
            "Could not locate expected columns for volume/refill in private boreholes file. "
            f"Available: {list(df.columns)}"
        )

    vol_uniques = (
        df[vol_col]
        .astype(str)
        .fillna("")
        .value_counts(dropna=False)
        .rename_axis("value")
        .reset_index(name="count")
    )
    ref_uniques = (
        df[ref_col]
        .astype(str)
        .fillna("")
        .value_counts(dropna=False)
        .rename_axis("value")
        .reset_index(name="count")
    )

    out_vol = config.OUTPUT_DATA_DIR / "private_unique_volume_values.csv"
    out_ref = config.OUTPUT_DATA_DIR / "private_unique_refill_values.csv"
    vol_uniques.to_csv(out_vol, index=False)
    ref_uniques.to_csv(out_ref, index=False)
    return vol_uniques, ref_uniques


def derive_private_Q_L_per_day() -> Path:
    """Derive Q_L_per_day for private boreholes and save an enriched CSV in derived dir.

    Rules:
    - Volume parsing: numbers like "1,000 liters" → 1000 L; unparseable → median of parsed volumes.
    - Refill parsing: map phrases to refills/week:
        - 'every day' or 'automatic filling' → 7
        - 'once a week' → 1; 'two times a week' → 2; ... up to 'six times a week' → 6
        - 'don't know'/'other'/missing → median of parsed refills/week
    - Q_L_per_day = volume_L × (refills_per_week / 7)
    Ensures no missing Q by imputing medians for volume/refill where needed.
    """
    path_in = config.PRIVATE_BOREHOLES_PATH
    if not path_in.exists():
        raise FileNotFoundError(f"Private boreholes file not found: {path_in}")
    df = pd.read_csv(path_in)

    # Locate candidate columns by header tokens
    vol_col = _find_column(list(df.columns), ("volume", "liter"))
    ref_col = _find_column(list(df.columns), ("refill",))
    if not vol_col or not ref_col:
        raise ValueError("Expected volume/refill columns not found in private boreholes CSV.")

    # Parse and impute volume (L) and refills/week using compact vectorized ops
    import re
    vols = (
        df[vol_col].astype(str).str.lower().where(df[vol_col].notna(), '')
        .str.extract(r'([\d,.]+)', expand=False).str.replace(',', '', regex=False)
    )
    vol_L = pd.to_numeric(vols, errors='coerce')
    vol_median = vol_L.dropna().median() if not vol_L.dropna().empty else 3000.0
    vol_L = vol_L.fillna(vol_median)

    # Map common phrases; fallback to first integer in text; then median
    phrase_map = {
        'every day': 7.0,
        'automatic filling': 7.0,
        'once a week': 1.0,
        'two times a week': 2.0,
        'three times a week': 3.0,
        'four times a week': 4.0,
        'five times a week': 5.0,
        'six times a week': 6.0,
    }
    ref_raw = df[ref_col].astype(str).str.lower().where(df[ref_col].notna(), '')
    ref_map = ref_raw.map(phrase_map)
    ref_num = ref_map.copy()
    needs_num = ref_num.isna() & ref_raw.notna()
    ref_num.loc[needs_num] = pd.to_numeric(ref_raw.str.extract(r'(\d+)', expand=False), errors='coerce')
    ref_median = ref_num.dropna().median() if not ref_num.dropna().empty else 3.0
    ref_wk = ref_num.fillna(ref_median)

    # Compute Q and write enriched file
    q_l_per_day = vol_L * (ref_wk / 7.0)
    df['Q_L_per_day'] = q_l_per_day

    out_path = config.PRIVATE_BOREHOLES_ENRICHED_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return out_path


def derive_government_Q_L_per_day() -> Path:
    """Add constant Q_L_per_day to government boreholes and save enriched CSV.

    Uses config.GOVERNMENT_Q_L_PER_DAY_DEFAULT (liters/day) for all rows.
    """
    path_in = config.GOVERNMENT_BOREHOLES_PATH
    if not path_in.exists():
        raise FileNotFoundError(f"Government boreholes file not found: {path_in}")
    df = pd.read_csv(path_in)
    df['Q_L_per_day'] = float(config.GOVERNMENT_Q_L_PER_DAY_DEFAULT)
    out_path = config.GOVERNMENT_BOREHOLES_ENRICHED_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return out_path



