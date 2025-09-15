"""Calibration utilities for FIO model (grid search over ks_per_m, EFIO scale).

Keeps linking radii fixed (no radius calibration).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Dict, Any, Tuple

import numpy as np
import pandas as pd

from . import fio_config as config
from . import fio_runner


@dataclass
class CalibParams:
    ks_per_m: float
    efio_scale: float


def _rmse_log(model: np.ndarray, lab: np.ndarray, eps: float = 1.0) -> float:
    m = np.log10(np.clip(model, 0, None) + eps)
    l = np.log10(np.clip(lab, 0, None) + eps)
    return float(np.sqrt(np.mean((m - l) ** 2)))


def _run_once(params: CalibParams, base_scenario: Dict[str, Any]) -> Tuple[float, int]:
    # Build scenario with updated ks and EFIO override; keep radii unchanged
    scenario = dict(base_scenario)
    scenario['ks_per_m'] = float(params.ks_per_m)
    scenario['EFIO_override'] = float(scenario.get('EFIO_override') or config.EFIO_DEFAULT) * float(params.efio_scale)

    fio_runner.run_scenario(scenario)

    # Load dashboard government table (has model concentrations and lab fields if present)
    gov = pd.read_csv(config.DASH_GOVERNMENT_BH_PATH) if config.DASH_GOVERNMENT_BH_PATH.exists() else pd.DataFrame()
    if gov.empty:
        return np.inf, 0

    # Expect modeled concentration in CFU/100mL and lab CFU/100mL if present
    if 'concentration_CFU_per_100mL' not in gov.columns:
        return np.inf, 0

    model = pd.to_numeric(gov['concentration_CFU_per_100mL'], errors='coerce')
    # Prefer Total Coliform for calibration if available; fallback to E. coli
    lab_col = 'lab_total_coliform_CFU_per_100mL' if 'lab_total_coliform_CFU_per_100mL' in gov.columns else 'lab_e_coli_CFU_per_100mL'
    lab = pd.to_numeric(gov.get(lab_col, np.nan), errors='coerce')
    mask = model.notna() & lab.notna()
    if mask.sum() == 0:
        return np.inf, 0

    score = _rmse_log(model[mask].to_numpy(), lab[mask].to_numpy())
    return score, int(mask.sum())


def run_calibration(ks_grid: Iterable[float] | None = None, efio_scale_grid: Iterable[float] | None = None) -> Dict[str, Any]:
    ks_grid = ks_grid or [0.0003, 0.0005, 0.001, 0.0015, 0.002, 0.003]
    efio_scale_grid = efio_scale_grid or [0.7, 0.85, 1.0, 1.15, 1.3]

    base = config.SCENARIOS['crisis_2025_current']

    results = []
    best = {'score': np.inf, 'params': None, 'n': 0}

    for ks in ks_grid:
        for ef in efio_scale_grid:
            params = CalibParams(ks_per_m=float(ks), efio_scale=float(ef))
            score, n = _run_once(params, base)
            row = {'ks_per_m': ks, 'efio_scale': ef, 'rmse_log': score, 'n_matched_boreholes': n}
            results.append(row)
            if score < best['score'] and n > 0:
                best = {'score': score, 'params': {'ks_per_m': ks, 'efio_scale': ef}, 'n': n}

    report = {
        'grid': {'ks_per_m': list(ks_grid), 'efio_scale': list(efio_scale_grid)},
        'results': results,
        'best': best,
    }

    (config.OUTPUT_DATA_DIR / 'calibration_report.json').write_text(json.dumps(report, indent=2))
    pd.DataFrame(results).to_csv(config.OUTPUT_DATA_DIR / 'calibration_results.csv', index=False)
    if best['params']:
        (config.OUTPUT_DATA_DIR / 'calibrated_scenario.json').write_text(json.dumps({
            'name': 'calibrated_best',
            'params': {
                **base,
                'ks_per_m': float(best['params']['ks_per_m']),
                'EFIO_override': float(config.EFIO_DEFAULT) * float(best['params']['efio_scale']),
            }
        }, indent=2))
    return report


def run_efficiency_calibration(
    ks_per_m: float = 0.003,
    efio_scale: float = 0.7,
    eff1_grid: Iterable[float] | None = None,
    eff2_grid: Iterable[float] | None = None,
    eff3_grid: Iterable[float] | None = None,
) -> Dict[str, Any]:
    """Calibrate containment efficiencies (cats 1..3) with fixed radius, ks, EFIO.

    eff4 (OD) is assumed 0.
    """
    eff1_grid = eff1_grid or [0.55, 0.60, 0.65]
    eff2_grid = eff2_grid or [0.15, 0.20, 0.25]
    eff3_grid = eff3_grid or [0.55, 0.60, 0.65]

    base = dict(config.SCENARIOS['crisis_2025_current'])
    base['ks_per_m'] = float(ks_per_m)
    base['EFIO_override'] = float(config.EFIO_DEFAULT) * float(efio_scale)

    results = []
    best = {'score': np.inf, 'params': None, 'n': 0}

    for e1 in eff1_grid:
        for e2 in eff2_grid:
            for e3 in eff3_grid:
                scenario = dict(base)
                scenario['efficiency_override'] = {1: float(e1), 2: float(e2), 3: float(e3), 4: 0.0}
                fio_runner.run_scenario(scenario)

                gov = pd.read_csv(config.DASH_GOVERNMENT_BH_PATH) if config.DASH_GOVERNMENT_BH_PATH.exists() else pd.DataFrame()
                if gov.empty or 'concentration_CFU_per_100mL' not in gov.columns:
                    score, n = np.inf, 0
                else:
                    model = pd.to_numeric(gov['concentration_CFU_per_100mL'], errors='coerce')
                    lab_col = 'lab_total_coliform_CFU_per_100mL' if 'lab_total_coliform_CFU_per_100mL' in gov.columns else 'lab_e_coli_CFU_per_100mL'
                    lab = pd.to_numeric(gov.get(lab_col, np.nan), errors='coerce')
                    mask = model.notna() & lab.notna()
                    if mask.sum() == 0:
                        score, n = np.inf, 0
                    else:
                        score = _rmse_log(model[mask].to_numpy(), lab[mask].to_numpy())
                        n = int(mask.sum())

                row = {'eff_cat1': e1, 'eff_cat2': e2, 'eff_cat3': e3, 'rmse_log': score, 'n_matched_boreholes': n}
                results.append(row)
                if score < best['score'] and n > 0:
                    best = {'score': score, 'params': {'eff_cat1': e1, 'eff_cat2': e2, 'eff_cat3': e3}, 'n': n}

    report = {
        'fixed': {'ks_per_m': ks_per_m, 'efio_scale': efio_scale},
        'grids': {'eff_cat1': list(eff1_grid), 'eff_cat2': list(eff2_grid), 'eff_cat3': list(eff3_grid)},
        'results': results,
        'best': best,
    }

    (config.OUTPUT_DATA_DIR / 'calibration_eff_report.json').write_text(json.dumps(report, indent=2))
    pd.DataFrame(results).to_csv(config.OUTPUT_DATA_DIR / 'calibration_eff_results.csv', index=False)
    if best['params']:
        (config.OUTPUT_DATA_DIR / 'calibrated_eff_scenario.json').write_text(json.dumps({
            'name': 'calibrated_eff_best',
            'params': {
                **base,
                'efficiency_override': {
                    1: float(best['params']['eff_cat1']),
                    2: float(best['params']['eff_cat2']),
                    3: float(best['params']['eff_cat3']),
                    4: 0.0,
                }
            }
        }, indent=2))
    return report




def _safe_corr(a: pd.Series, b: pd.Series, method: str) -> float:
    # Require at least two distinct values in each series to avoid NaN correlations
    if a.nunique(dropna=True) < 2 or b.nunique(dropna=True) < 2:
        return float('nan')
    try:
        return float(a.corr(b, method=method))
    except Exception:
        return float('nan')


def run_trend_search(
    ks_grid: Iterable[float] | None = None,
    efio_override_grid: Iterable[float] | None = None,
    eff1_grid: Iterable[float] | None = None,
    eff2_grid: Iterable[float] | None = None,
    eff3_grid: Iterable[float] | None = None,
    lab_threshold_cfu_per_100ml: float = 10.0,
) -> Dict[str, Any]:
    """Search parameter combos and measure trend similarity vs. lab data.

    Metrics:
      - Spearman rho(model, lab)
      - Kendall tau(model, lab)
      - Pearson r on log10(x+1)
      - RMSE in log10-space
    """
    # Defaults focus around the empirically promising region and low containment context
    ks_grid = list(ks_grid or [0.05, 0.08, 0.10, 0.12])
    # Fix EFIO to a plausible low value to emphasize trend matching
    efio_override_grid = list(efio_override_grid or [1.0e7])
    # Explore limited efficiency ranges to keep runs fast
    eff1_grid = list(eff1_grid or [0.50])
    eff2_grid = list(eff2_grid or [0.10, 0.20])
    eff3_grid = list(eff3_grid or [0.30, 0.50])

    base = dict(config.SCENARIOS['crisis_2025_current'])

    results: list[dict[str, Any]] = []
    # Best by primary criterion (highest Spearman), fallback to Kendall, then lowest RMSE
    best = {'score_spearman': -np.inf, 'score_kendall': -np.inf, 'rmse_log': np.inf, 'params': None, 'n': 0}

    for ks in ks_grid:
        for efio in efio_override_grid:
            for e1 in eff1_grid:
                for e2 in eff2_grid:
                    for e3 in eff3_grid:
                        scenario = dict(base)
                        scenario['ks_per_m'] = float(ks)
                        scenario['EFIO_override'] = float(efio)
                        scenario['efficiency_override'] = {1: float(e1), 2: float(e2), 3: float(e3), 4: 0.0}

                        fio_runner.run_scenario(scenario)

                        gov = pd.read_csv(config.DASH_GOVERNMENT_BH_PATH) if config.DASH_GOVERNMENT_BH_PATH.exists() else pd.DataFrame()
                        if gov.empty or 'concentration_CFU_per_100mL' not in gov.columns:
                            n = 0
                            rho = float('nan')
                            tau = float('nan')
                            r_log = float('nan')
                            rmse = float('inf')
                        else:
                            model = pd.to_numeric(gov['concentration_CFU_per_100mL'], errors='coerce')
                            lab_col = 'lab_total_coliform_CFU_per_100mL' if 'lab_total_coliform_CFU_per_100mL' in gov.columns else 'lab_e_coli_CFU_per_100mL'
                            lab = pd.to_numeric(gov.get(lab_col, np.nan), errors='coerce')
                            mask = model.notna() & lab.notna()
                            m = model[mask]
                            l = lab[mask].clip(lower=1.0)
                            if lab_threshold_cfu_per_100ml is not None and lab_threshold_cfu_per_100ml > 0:
                                keep = l >= float(lab_threshold_cfu_per_100ml)
                                m = m[keep]
                                l = l[keep]
                            n = int(len(m))
                            if n == 0:
                                rho = float('nan')
                                tau = float('nan')
                                r_log = float('nan')
                                rmse = float('inf')
                            else:
                                rho = _safe_corr(m, l, method='spearman')
                                tau = _safe_corr(m, l, method='kendall')
                                mlog = np.log10(m.to_numpy() + 1.0)
                                llog = np.log10(l.to_numpy() + 1.0)
                                if np.std(mlog) == 0.0 or np.std(llog) == 0.0:
                                    r_log = float('nan')
                                else:
                                    r_log = float(pd.Series(mlog).corr(pd.Series(llog), method='pearson'))
                                rmse = _rmse_log(m.to_numpy(), l.to_numpy())

                        row = {
                            'ks_per_m': float(ks),
                            'EFIO_override': float(efio),
                            'eff_cat1': float(e1),
                            'eff_cat2': float(e2),
                            'eff_cat3': float(e3),
                            'n_matched_boreholes': n,
                            'spearman_rho': rho,
                            'kendall_tau': tau,
                            'pearson_r_log': r_log,
                            'rmse_log': rmse,
                        }
                        results.append(row)

                        # Determine best by (spearman desc, kendall desc, rmse asc)
                        better = False
                        if not np.isnan(rho):
                            if rho > best['score_spearman']:
                                better = True
                            elif rho == best['score_spearman']:
                                if not np.isnan(tau) and (tau > best['score_kendall']):
                                    better = True
                                elif (tau == best['score_kendall']) and (rmse < best['rmse_log']):
                                    better = True
                        if better and n > 0:
                            best = {
                                'score_spearman': float(rho) if not np.isnan(rho) else -np.inf,
                                'score_kendall': float(tau) if not np.isnan(tau) else -np.inf,
                                'rmse_log': float(rmse),
                                'params': {
                                    'ks_per_m': float(ks),
                                    'EFIO_override': float(efio),
                                    'eff_cat1': float(e1),
                                    'eff_cat2': float(e2),
                                    'eff_cat3': float(e3),
                                },
                                'n': int(n),
                            }

    # Persist outputs
    report = {
        'grids': {
            'ks_per_m': ks_grid,
            'EFIO_override': efio_override_grid,
            'eff_cat1': eff1_grid,
            'eff_cat2': eff2_grid,
            'eff_cat3': eff3_grid,
        },
        'results': results,
        'best_by_spearman': best,
    }

    (config.OUTPUT_DATA_DIR / 'trend_search_report.json').write_text(json.dumps(report, indent=2))
    pd.DataFrame(results).to_csv(config.OUTPUT_DATA_DIR / 'trend_search_results.csv', index=False)

    if best['params']:
        (config.OUTPUT_DATA_DIR / 'calibrated_trend_scenario.json').write_text(json.dumps({
            'name': 'calibrated_trend_best',
            'params': {
                **base,
                'ks_per_m': float(best['params']['ks_per_m']),
                'EFIO_override': float(best['params']['EFIO_override']),
                'efficiency_override': {
                    1: float(best['params']['eff_cat1']),
                    2: float(best['params']['eff_cat2']),
                    3: float(best['params']['eff_cat3']),
                    4: 0.0,
                }
            }
        }, indent=2))

    return report

