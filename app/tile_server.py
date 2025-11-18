"""Lightweight data tile service for Streamlit dashboards.

Runs a FastAPI app in a background thread so Streamlit can fetch
viewport-filtered GeoJSON or Mapbox Vector Tiles (PBF). The service
keeps responses small (capped per request) to keep the map responsive
while a separate download button exposes the full dataset.
"""

from __future__ import annotations

import math
import os
import threading
from functools import lru_cache
from typing import Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, Response
import uvicorn
import mapbox_vector_tile

from . import fio_config as config

TILE_SERVER_PORT = int(os.getenv("TILE_SERVER_PORT", "8001"))
MAX_FEATURES_PER_RESPONSE = 20_000

_server_started = False
_server_lock = threading.Lock()


def _nitrogen_intensity(load: float) -> float:
    # Fixed scale used in nitrogen dashboard
    NITROGEN_SCALE_MIN = 20.0
    NITROGEN_SCALE_MAX = 45.0
    try:
        x = float(load)
        if np.isnan(x) or x < 0:
            return 0.0
    except Exception:
        return 0.0
    intensity = (x - NITROGEN_SCALE_MIN) / (NITROGEN_SCALE_MAX - NITROGEN_SCALE_MIN)
    return float(max(0.0, min(1.0, intensity)))


def _nitrogen_color(intensity: float) -> Tuple[int, int, int, int]:
    try:
        intensity = float(intensity)
    except Exception:
        intensity = 0.0
    intensity = max(0.0, min(1.0, intensity))
    if intensity < 0.33:
        ratio = intensity / 0.33
        r = int(46 + (255 - 46) * ratio)
        g = 255
        b = int(113 - 113 * ratio)
    elif intensity < 0.66:
        ratio = (intensity - 0.33) / 0.33
        r = 255
        g = int(255 - 99 * ratio)
        b = 0
    else:
        ratio = (intensity - 0.66) / 0.34
        r = 255
        g = int(156 - 80 * ratio)
        b = int(18 - 18 * ratio)
    return (r, g, b, 200)


def _nitrogen_radius(load: float) -> float:
    try:
        x = float(load)
        if np.isnan(x) or x < 0:
            return 3.0
    except Exception:
        return 3.0
    intensity = _nitrogen_intensity(x)
    return 3.0 + (intensity * 9.0)


def _toilet_type_color(cat_id: int) -> Tuple[int, int, int, int]:
    try:
        m = {
            1: (46, 204, 113, 200),
            2: (243, 156, 18, 200),
            3: (52, 152, 219, 200),
            4: (231, 76, 60, 200),
        }
        return m.get(int(cat_id), (160, 160, 160, 200))
    except Exception:
        return (160, 160, 160, 200)


def _toilet_type_label(cat_id: int) -> str:
    return {1: "Sewered", 2: "Pit Latrine", 3: "Septic", 4: "Open Defecation"}.get(int(cat_id), "Unknown")


@lru_cache(maxsize=1)
def _load_points() -> pd.DataFrame:
    p = config.NET_NITROGEN_LOAD_PATH
    if not p.exists():
        return pd.DataFrame(columns=["id", "lat", "long", "toilet_category_id", "nitrogen_load"])
    df = pd.read_csv(p)
    cols = [c for c in ["id", "lat", "long", "toilet_category_id", "nitrogen_load"] if c in df.columns]
    df = df[cols].dropna(subset=["lat", "long"]).copy()
    try:
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce").astype("float32")
        df["long"] = pd.to_numeric(df["long"], errors="coerce").astype("float32")
        if "nitrogen_load" in df.columns:
            df["nitrogen_load"] = pd.to_numeric(df["nitrogen_load"], errors="coerce").astype("float32")
        df["toilet_category_id"] = pd.to_numeric(df.get("toilet_category_id", 0), errors="coerce").fillna(0).astype("int8")
    except Exception:
        pass
    df["nitrogen_intensity"] = df.get("nitrogen_load", 0).apply(_nitrogen_intensity)
    colors = df["nitrogen_intensity"].apply(_nitrogen_color)
    df[["n_color_r", "n_color_g", "n_color_b", "n_color_a"]] = pd.DataFrame(colors.tolist(), index=df.index)
    type_colors = df["toilet_category_id"].apply(_toilet_type_color)
    df[["t_color_r", "t_color_g", "t_color_b", "t_color_a"]] = pd.DataFrame(type_colors.tolist(), index=df.index)
    df["radius"] = df.get("nitrogen_load", 0).apply(_nitrogen_radius)
    df["toilet_type_label"] = df["toilet_category_id"].apply(_toilet_type_label)
    df["nitrogen_label"] = df.get("nitrogen_load", 0).apply(lambda x: f"{float(x):.1f}" if pd.notna(x) else "-")
    df["tooltip_html"] = (
        "<div><b>Toilet ID: "
        + df.get("id", "-").astype(str)
        + "</b><br>Type: <b>"
        + df["toilet_type_label"].astype(str)
        + "</b><br>Nitrogen Load: <b>"
        + df["nitrogen_label"]
        + " kg N/year</b></div>"
    )
    return df


def _filter_categories(df: pd.DataFrame, categories: Sequence[int] | None) -> pd.DataFrame:
    if not categories:
        return df
    return df[df["toilet_category_id"].isin([int(c) for c in categories])]


def _filter_bbox(df: pd.DataFrame, bbox: Tuple[float, float, float, float]) -> pd.DataFrame:
    minx, miny, maxx, maxy = bbox
    return df[(df["long"] >= minx) & (df["long"] <= maxx) & (df["lat"] >= miny) & (df["lat"] <= maxy)]


def _tile_to_bounds(x: int, y: int, z: int) -> Tuple[float, float, float, float]:
    # Web mercator tile to lon/lat bounds
    def _tile2lon(x: int, z: int) -> float:
        return x / (2 ** z) * 360.0 - 180.0

    def _tile2lat(y: int, z: int) -> float:
        n = math.pi - (2.0 * math.pi * y) / (2 ** z)
        return math.degrees(math.atan(math.sinh(n)))

    return (_tile2lon(x, z), _tile2lat(y + 1, z), _tile2lon(x + 1, z), _tile2lat(y, z))


def _rows_to_geojson(rows: pd.DataFrame) -> dict:
    features: List[dict] = []
    for row in rows.itertuples(index=False):
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row.long, row.lat]},
                "properties": {
                    "id": getattr(row, "id", None),
                    "nitrogen_load": getattr(row, "nitrogen_load", None),
                    "nitrogen_intensity": getattr(row, "nitrogen_intensity", None),
                    "radius": getattr(row, "radius", None),
                    "toilet_category_id": getattr(row, "toilet_category_id", None),
                    "toilet_type_label": getattr(row, "toilet_type_label", None),
                    "n_color_r": getattr(row, "n_color_r", None),
                    "n_color_g": getattr(row, "n_color_g", None),
                    "n_color_b": getattr(row, "n_color_b", None),
                    "n_color_a": getattr(row, "n_color_a", None),
                    "t_color_r": getattr(row, "t_color_r", None),
                    "t_color_g": getattr(row, "t_color_g", None),
                    "t_color_b": getattr(row, "t_color_b", None),
                    "t_color_a": getattr(row, "t_color_a", None),
                    "tooltip_html": getattr(row, "tooltip_html", ""),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _rows_to_mvt(rows: pd.DataFrame, bounds: Tuple[float, float, float, float]) -> bytes:
    features = []
    for row in rows.itertuples(index=False):
        features.append(
            {
                "geometry": {"type": "Point", "coordinates": [row.long, row.lat]},
                "properties": {
                    "id": getattr(row, "id", None),
                    "nitrogen_load": getattr(row, "nitrogen_load", None),
                    "nitrogen_intensity": getattr(row, "nitrogen_intensity", None),
                    "radius": getattr(row, "radius", None),
                    "toilet_category_id": getattr(row, "toilet_category_id", None),
                    "toilet_type_label": getattr(row, "toilet_type_label", None),
                    "n_color_r": getattr(row, "n_color_r", None),
                    "n_color_g": getattr(row, "n_color_g", None),
                    "n_color_b": getattr(row, "n_color_b", None),
                    "n_color_a": getattr(row, "n_color_a", None),
                    "t_color_r": getattr(row, "t_color_r", None),
                    "t_color_g": getattr(row, "t_color_g", None),
                    "t_color_b": getattr(row, "t_color_b", None),
                    "t_color_a": getattr(row, "t_color_a", None),
                    "tooltip_html": getattr(row, "tooltip_html", ""),
                },
            }
        )
    return mapbox_vector_tile.encode({"nitrogen": features}, quantize_bounds=bounds, extents=4096)


def _create_app() -> FastAPI:
    app = FastAPI(title="Nitrogen tiles")

    @app.get("/health")
    def health():  # pragma: no cover - trivial
        return {"status": "ok"}

    @app.get("/geojson")
    def geojson(
        bbox: str = Query(..., description="minx,miny,maxx,maxy in lon/lat"),
        limit: int = Query(MAX_FEATURES_PER_RESPONSE, le=MAX_FEATURES_PER_RESPONSE * 2, gt=0),
        categories: str | None = Query(None, description="Comma-separated toilet_category_id values"),
    ):
        df = _load_points()
        try:
            coords = [float(x) for x in bbox.split(",")]
            if len(coords) != 4:
                raise ValueError
        except Exception:
            raise HTTPException(status_code=400, detail="bbox must be 'minx,miny,maxx,maxy'")
        cats = [int(x) for x in categories.split(",")] if categories else None
        filtered = _filter_bbox(_filter_categories(df, cats), tuple(coords))
        subset = filtered.head(limit)
        return JSONResponse(_rows_to_geojson(subset))

    @app.get("/tiles/{z}/{x}/{y}.pbf")
    def tile(
        z: int,
        x: int,
        y: int,
        limit: int = Query(MAX_FEATURES_PER_RESPONSE, le=MAX_FEATURES_PER_RESPONSE * 2, gt=0),
        categories: str | None = Query(None, description="Comma-separated toilet_category_id values"),
    ):
        df = _load_points()
        bounds = _tile_to_bounds(x, y, z)
        cats = [int(c) for c in categories.split(",")] if categories else None
        filtered = _filter_bbox(_filter_categories(df, cats), bounds)
        subset = filtered.head(limit)
        tile_bytes = _rows_to_mvt(subset, bounds)
        return Response(content=tile_bytes, media_type="application/x-protobuf")

    return app


def start_tile_server() -> str:
    """Start the FastAPI tile server in a background thread (idempotent)."""

    global _server_started
    with _server_lock:
        if _server_started:
            return f"http://localhost:{TILE_SERVER_PORT}"

        app = _create_app()
        config_obj = uvicorn.Config(app, host="0.0.0.0", port=TILE_SERVER_PORT, log_level="warning")
        server = uvicorn.Server(config_obj)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        _server_started = True
    return f"http://localhost:{TILE_SERVER_PORT}"


def tile_url(categories: Iterable[int] | None = None, limit: int = MAX_FEATURES_PER_RESPONSE) -> str:
    base = f"http://localhost:{TILE_SERVER_PORT}"
    cat_param = ""
    if categories:
        cat_param = "&categories=" + ",".join(str(int(c)) for c in sorted(set(categories)))
    return f"{base}/tiles/{{z}}/{{x}}/{{y}}.pbf?limit={int(limit)}{cat_param}"


def geojson_url(bbox_placeholder: str = "{bbox}", categories: Iterable[int] | None = None, limit: int = MAX_FEATURES_PER_RESPONSE) -> str:
    base = f"http://localhost:{TILE_SERVER_PORT}"
    cat_param = ""
    if categories:
        cat_param = "&categories=" + ",".join(str(int(c)) for c in sorted(set(categories)))
    return f"{base}/geojson?bbox={bbox_placeholder}&limit={int(limit)}{cat_param}"

