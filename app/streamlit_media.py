"""Helpers for moving large datasets to Streamlit's media endpoint.

These utilities let us hand a public URL to frontend components (like
pydeck) instead of streaming multi‑MB payloads through the websocket.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


def dataframe_to_media_url(df: pd.DataFrame, *, label: str) -> Optional[str]:
    """Return a Streamlit media URL for the given dataframe.

    When running inside a Streamlit session we register the dataframe as an
    ``application/json`` blob with the runtime media manager and return the
    fetchable URL. If we are outside of a Streamlit runtime (for example when
    unit tests import the module) ``None`` is returned so callers can fall back
    to the raw dataframe.
    """

    if df is None or df.empty:
        return None

    try:
        from streamlit.runtime import runtime
        from streamlit.runtime.scriptrunner import script_run_context
    except Exception:
        # Streamlit runtime modules are unavailable (e.g. non-Streamlit CLI).
        return None

    try:
        if not runtime.Runtime.exists():
            return None
        ctx = script_run_context.get_script_run_ctx(suppress_warning=True)
        if ctx is None:
            return None
        media_mgr = runtime.Runtime.instance().media_file_mgr
    except Exception:
        # Runtime not initialised yet – fall back to the original dataframe.
        return None

    try:
        json_bytes = df.to_json(orient="records").encode("utf-8")
    except Exception:
        return None

    coordinates = f"pydeck-data::{label}"
    try:
        return media_mgr.add(
            json_bytes,
            mimetype="application/json",
            coordinates=coordinates,
            file_name=f"{label}.json",
        )
    except Exception:
        return None

