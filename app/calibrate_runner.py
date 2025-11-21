import copy
from itertools import product
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, kendalltau
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold
from sklearn.neighbors import BallTree

from app import config, engine, calibration_utils
from app.calibration_engine import CalibrationEngine

# Default search space for physical parameters
DEFAULT_GRID = {
    "efio": [1e6, 5e6, 1e7],
    "ks": [0.01, 0.05, 0.1],
    "radius_g": [50.0, 100.0, 250.0, 500.0, 1000.0],
    "flow_mult": [1.0, 10.0, 100.0, 1000.0],
}

# Radii used for data-driven feature engineering (counts/decay)
FEATURE_RADII = (50, 100, 200, 500, 1000)


def _prepare_inputs() -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """Load common inputs once to avoid repeated I/O in calibration."""
    base_scenario = copy.deepcopy(config.SCENARIOS["crisis_2025_current"])
    sanitation = engine.apply_interventions(
        engine.load_and_standardize_sanitation(), base_scenario
    )
    gov_boreholes = pd.read_csv(config.GOVERNMENT_BOREHOLES_ENRICHED_PATH)
    return sanitation, gov_boreholes, base_scenario


def _run_model_once(
    sanitation: pd.DataFrame,
    gov_boreholes: pd.DataFrame,
    scenario_base: Dict,
    efio: float,
    ks: float,
    radius_g: float,
    flow_mult: float,
) -> pd.DataFrame:
    """Run the physical transport pipeline for government wells only."""
    scenario = copy.deepcopy(scenario_base)
    scenario["EFIO_override"] = efio
    scenario["ks_per_m"] = ks
    scenario["radius_by_type"]["government"] = radius_g
    scenario["flow_multiplier_by_type"]["government"] = flow_mult

    pcfg = engine._get_pollutant_config("fio", scenario)  # type: ignore
    loads = engine.compute_load(sanitation, pcfg, save_output=False)
    linked = engine.run_transport(loads, gov_boreholes, pcfg, radius_g)
    conc = engine.compute_concentration(linked, flow_multiplier=flow_mult)
    conc["borehole_type"] = "government"
    return conc


def run_grid_search(grid: Dict = None) -> pd.DataFrame:
    """Evaluate a coarse grid of physical parameters and persist results."""
    grid = grid or DEFAULT_GRID
    sanitation, gov_boreholes, scenario_base = _prepare_inputs()
    calib = CalibrationEngine()

    records: List[Dict] = []
    for efio, ks, radius_g, flow_mult in product(
        grid["efio"], grid["ks"], grid["radius_g"], grid["flow_mult"]
    ):
        pred_df = _run_model_once(
            sanitation, gov_boreholes, scenario_base, efio, ks, radius_g, flow_mult
        )
        calib.model_df = pred_df
        matched = calib.match_points()
        metrics = calib.calculate_metrics(matched)
        metrics.update(
            {
                "efio": efio,
                "ks": ks,
                "radius_g": radius_g,
                "flow_multiplier": flow_mult,
            }
        )
        records.append(metrics)

    results = pd.DataFrame(records).sort_values(
        ["spearman_rho", "kendall_rho", "rmse_log"], ascending=[False, False, True]
    )
    out_path = config.OUTPUT_DATA_DIR / "calibration_grid_results.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(out_path, index=False)
    return results


def _build_neighbor_features(
    toilets: pd.DataFrame, boreholes: pd.DataFrame, radii: Iterable[int]
) -> pd.DataFrame:
    """Pre-compute neighbor-based features for data-driven calibration."""
    leak_load = toilets["household_population"] * (
        1.0 - toilets["pathogen_containment_efficiency"]
    )
    tree = BallTree(np.radians(toilets[["lat", "long"]].values), metric="haversine")
    bore_rad = np.radians(boreholes[["lat", "long"]].values)

    feats = {}
    for r in radii:
        inds, dists = tree.query_radius(
            bore_rad, r=r / config.EARTH_RADIUS_M, return_distance=True
        )
        count_list = []
        sum_list = []
        invd_list = []
        decay_list = []
        for idx, dist in zip(inds, dists):
            if len(idx) == 0:
                count_list.append(0.0)
                sum_list.append(0.0)
                invd_list.append(0.0)
                decay_list.append(0.0)
                continue
            ld = leak_load.iloc[idx].values
            dist_m = dist * config.EARTH_RADIUS_M
            count_list.append(float(len(idx)))
            sum_list.append(ld.sum())
            invd_list.append(np.sum(ld / (dist_m + 1.0)))
            decay_list.append(np.sum(ld * np.exp(-0.01 * dist_m)))

        feats[f"count_{r}m"] = count_list
        feats[f"load_{r}m"] = sum_list
        feats[f"invd_{r}m"] = invd_list
        feats[f"decay_{r}m"] = decay_list

    return pd.DataFrame(feats)


def run_random_forest_cv(
    toilets: pd.DataFrame, obs_df: pd.DataFrame, radii: Tuple[int, ...] = FEATURE_RADII
) -> Dict:
    """Cross-validated data-driven calibration to expose ceiling performance."""
    obs_df = obs_df.dropna(subset=["fio_obs"]).reset_index(drop=True)
    features = _build_neighbor_features(toilets, obs_df, radii=radii)
    X = np.log1p(features.fillna(0))
    y = obs_df["fio_obs"].values

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    rmses: List[float] = []
    spears: List[float] = []
    kendalls: List[float] = []
    for train_idx, test_idx in kf.split(X):
        model = RandomForestRegressor(
            n_estimators=400, random_state=42, max_depth=None
        )
        model.fit(X.iloc[train_idx], y[train_idx])
        pred = model.predict(X.iloc[test_idx])
        rmses.append(
            float(
                np.sqrt(
                    np.mean((np.log1p(pred) - np.log1p(y[test_idx])) ** 2)
                )
            )
        )
        spear = spearmanr(pred, y[test_idx]).correlation
        kend = kendalltau(pred, y[test_idx], nan_policy="omit").correlation
        spears.append(float(spear if not np.isnan(spear) else 0.0))
        kendalls.append(float(kend if not np.isnan(kend) else 0.0))

    return {
        "n_samples": len(y),
        "rmse_log_mean": float(np.nanmean(rmses)),
        "spearman_mean": float(np.nanmean(spears)),
        "kendall_mean": float(np.nanmean(kendalls)),
        "radii": list(radii),
    }


def main():
    sanitation, gov_boreholes, scenario_base = _prepare_inputs()
    print("Running parameter grid search...")
    grid_results = run_grid_search()
    best = grid_results.iloc[0]
    print("Top grid result:", best.to_dict())

    print("Running data-driven RF CV (upper bound on trend signal)...")
    rf_metrics = run_random_forest_cv(sanitation, calibration_utils.load_government_data())
    rf_path = config.OUTPUT_DATA_DIR / "calibration_rf_cv.json"
    rf_path.write_text(pd.Series(rf_metrics).to_json(indent=2))
    print("RF CV metrics saved to", rf_path)


if __name__ == "__main__":
    main()
