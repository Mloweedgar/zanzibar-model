"""Lightweight helpers to precompute and serve vector tiles for large point datasets."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import threading
from collections import defaultdict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

import mapbox_vector_tile
import pandas as pd


def _tile_coords(lon: float, lat: float, z: int, *, extent: int = 4096) -> Optional[Tuple[int, int, int, int]]:
    """Convert lon/lat to tile coordinates (x, y, pixel offsets).

    Returns None for invalid coordinates.
    """

    try:
        lon = float(lon)
        lat = float(lat)
    except Exception:
        return None

    if not (-180.0 <= lon <= 180.0 and -85.05112878 <= lat <= 85.05112878):
        return None

    lat_rad = math.radians(lat)
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n

    xtile = int(math.floor(x))
    ytile = int(math.floor(y))
    x_pix = int((x - xtile) * extent)
    y_pix = int((y - ytile) * extent)
    return xtile, ytile, x_pix, y_pix


def _hash_dataframe(df: pd.DataFrame, *, columns: Iterable[str]) -> str:
    """Stable hash for a dataframe based on selected columns."""

    if df is None or df.empty:
        return "empty"
    cols = [c for c in columns if c in df.columns]
    if not cols:
        return "empty"
    subset = df[cols].copy()
    subset = subset.fillna(0)
    hashed = pd.util.hash_pandas_object(subset, index=False).values
    digest = hashlib.md5(hashed.tobytes()).hexdigest()
    return digest


def build_point_tile_pyramid(
    layer_frames: Mapping[str, Tuple[pd.DataFrame, List[str]]],
    *,
    tiles_dir: Path,
    lon_col: str = "long",
    lat_col: str = "lat",
    min_zoom: int = 8,
    max_zoom: int = 16,
    extent: int = 4096,
    manifest_payload: Optional[Mapping[str, object]] = None,
) -> Path:
    """Encode point features into a z/x/y vector tile pyramid.

    layer_frames maps a vector tile layer name to a tuple of (DataFrame, property columns).
    Only the provided columns are embedded in the tile to keep payloads small.
    Tiles are regenerated only when the manifest (hashes + metadata) changes.
    """

    tiles_dir = Path(tiles_dir)
    manifest_path = tiles_dir / "manifest.json"
    tiles_dir.mkdir(parents=True, exist_ok=True)

    # Compute manifest and short-circuit if unchanged
    manifest: Dict[str, object] = {
        "min_zoom": int(min_zoom),
        "max_zoom": int(max_zoom),
        "extent": int(extent),
        "layers": {},
    }
    if manifest_payload:
        manifest["metadata"] = dict(manifest_payload)

    for layer_name, (df, prop_cols) in layer_frames.items():
        manifest["layers"][layer_name] = {
            "hash": _hash_dataframe(df, columns=[lon_col, lat_col, *prop_cols]),
            "rows": 0 if df is None else int(len(df)),
        }

    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as fh:
                existing = json.load(fh)
            if existing == manifest:
                return tiles_dir
        except Exception:
            pass

    # Rebuild pyramid
    shutil.rmtree(tiles_dir, ignore_errors=True)
    tiles_dir.mkdir(parents=True, exist_ok=True)

    tile_layers: Dict[Tuple[int, int, int], Dict[str, List[dict]]] = defaultdict(lambda: defaultdict(list))

    for layer_name, (df, prop_cols) in layer_frames.items():
        if df is None or df.empty:
            continue
        present_cols = [c for c in prop_cols if c in df.columns]
        if lon_col not in df.columns or lat_col not in df.columns:
            continue
        for _, row in df.iterrows():
            # quick validation before iterating zooms
            if _tile_coords(row[lon_col], row[lat_col], min_zoom, extent=extent) is None:
                continue
            for z in range(min_zoom, max_zoom + 1):
                coord = _tile_coords(row[lon_col], row[lat_col], z, extent=extent)
                if coord is None:
                    continue
                xtile, ytile, x_pix, y_pix = coord
                props = {k: row[k] for k in present_cols}
                try:
                    props = {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in props.items()}
                except Exception:
                    pass
                tile_layers[(z, xtile, ytile)][layer_name].append({
                    "geometry": {"type": "Point", "coordinates": [x_pix, y_pix]},
                    "properties": props,
                })

    for (z, xtile, ytile), layers in tile_layers.items():
        path = tiles_dir / str(z) / str(xtile) / f"{ytile}.pbf"
        path.parent.mkdir(parents=True, exist_ok=True)
        tile = mapbox_vector_tile.encode(layers, extents=extent)
        with open(path, "wb") as fh:
            fh.write(tile)

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    return tiles_dir


_server_lock = threading.Lock()
_server_started = False
_server_port: Optional[int] = None


def ensure_tile_http_server(root: Path, *, port: int = 8081, host: str = "0.0.0.0") -> int:
    """Start a static HTTP server (once) rooted at ``root`` for tile delivery."""

    global _server_started, _server_port

    with _server_lock:
        if _server_started and _server_port:
            return _server_port

        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)

        class _Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(root), **kwargs)

            def log_message(self, fmt: str, *args) -> None:  # pragma: no cover - noisy in Streamlit
                return

            def guess_type(self, path: str) -> str:
                if path.endswith(".pbf"):
                    return "application/vnd.mapbox-vector-tile"
                if path.endswith(".geojson"):
                    return "application/geo+json"
                return super().guess_type(path)

        def _serve():
            with ThreadingHTTPServer((host, port), _Handler) as httpd:
                httpd.serve_forever()

        thread = threading.Thread(target=_serve, daemon=True)
        thread.start()
        _server_started = True
        _server_port = port
        return port


def tile_url(base: str, *, subdir: str) -> str:
    """Return a template URL for deck.gl data pointing at the tile server."""

    base = (base or "").rstrip("/")
    if base == "":
        return f"/tiles/{subdir}/{{z}}/{{x}}/{{y}}.pbf"
    return f"{base}/tiles/{subdir}/{{z}}/{{x}}/{{y}}.pbf"
