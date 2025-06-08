"""Data ingestion helpers."""

from pathlib import Path
import pandas as pd
import geopandas as gpd


def read_csv(path: Path) -> pd.DataFrame:
    """Read CSV file."""
    return pd.read_csv(path)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write DataFrame to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def read_geojson(path: Path) -> gpd.GeoDataFrame:
    """Read GeoJSON file."""
    return gpd.read_file(path)


def write_geojson(gdf: gpd.GeoDataFrame, path: Path) -> None:
    """Write GeoDataFrame to GeoJSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver='GeoJSON')
