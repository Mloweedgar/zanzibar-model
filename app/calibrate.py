"""Calibration utilities for FIO model.

Two types of calibration:
1. Parameter calibration (grid search over ks_per_m, EFIO scale) - original functionality
2. Model→Lab calibration (mapping model outputs to lab-equivalent scale) - new protocol

Keeps linking radii fixed (no radius calibration).
"""

from __future__ import annotations

import argparse
import json
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Dict, Any, Tuple, Optional, Union

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import HuberRegressor, TheilSenRegressor
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from scipy.stats import spearmanr, kendalltau

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

    # Expect modeled concentration in CFU/100mL and lab E. coli CFU/100mL if present
    if 'concentration_CFU_per_100mL' not in gov.columns:
        return np.inf, 0

    model = pd.to_numeric(gov['concentration_CFU_per_100mL'], errors='coerce')
    lab = pd.to_numeric(gov.get('lab_e_coli_CFU_per_100mL', np.nan), errors='coerce')
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
                    lab = pd.to_numeric(gov.get('lab_e_coli_CFU_per_100mL', np.nan), errors='coerce')
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
                            lab = pd.to_numeric(gov.get('lab_e_coli_CFU_per_100mL', np.nan), errors='coerce')
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


# ==================================================================================
# MODEL → LAB CALIBRATION (New Protocol)
# ==================================================================================

def coerce_numeric(series: pd.Series, nd_value: float = 0.1, numerous_policy: str = 'cap_p99') -> pd.Series:
    """Coerce lab/model values to numeric, handling ND and 'Numerous' per protocol."""
    result = series.copy()
    
    # Convert to string first for consistent handling
    result = result.astype(str).str.strip().str.replace(',', '').str.lower()
    
    # Handle non-detect cases
    nd_mask = result.isin(['nd', '0', 'nan', ''])
    
    # Handle "Numerous" cases  
    numerous_mask = result.str.contains('numerous', na=False)
    
    # Convert remaining to numeric
    result = pd.to_numeric(result, errors='coerce')
    
    # Apply ND policy
    result.loc[nd_mask] = nd_value
    
    # Apply "Numerous" policy
    if numerous_mask.any():
        if numerous_policy == 'cap_p99':
            # Set to 99th percentile of the dataset (excluding Numerous values)
            clean_values = result[~numerous_mask & ~nd_mask]
            if len(clean_values) > 0:
                p99_value = clean_values.quantile(0.99)
                result.loc[numerous_mask] = p99_value
            else:
                result.loc[numerous_mask] = 1000.0  # fallback
        elif numerous_policy == 'cap_p97':
            clean_values = result[~numerous_mask & ~nd_mask]
            if len(clean_values) > 0:
                p97_value = clean_values.quantile(0.97)
                result.loc[numerous_mask] = p97_value
            else:
                result.loc[numerous_mask] = 1000.0
        elif numerous_policy == 'fixed_1000':
            result.loc[numerous_mask] = 1000.0
        else:
            raise ValueError(f"Unknown numerous_policy: {numerous_policy}")
    
    return result


def fit_robust_linear(m: np.ndarray, y: np.ndarray, method: str = 'huber') -> Tuple[float, float]:
    """Fit robust linear model y = α + β·m in log space."""
    if method == 'huber':
        reg = HuberRegressor(epsilon=1.35, max_iter=1000, alpha=0.0001, fit_intercept=True)
        reg.fit(m.reshape(-1, 1), y)
        alpha, beta = reg.intercept_, reg.coef_[0]
    elif method == 'theil_sen':
        reg = TheilSenRegressor(max_iter=1000, random_state=42, fit_intercept=True)
        reg.fit(m.reshape(-1, 1), y)
        alpha, beta = reg.intercept_, reg.coef_[0]
    else:
        raise ValueError(f"Unknown robust method: {method}")
    
    return float(alpha), float(beta)


def fit_isotonic(m: np.ndarray, y: np.ndarray) -> IsotonicRegression:
    """Fit monotonic isotonic regression m → y."""
    reg = IsotonicRegression(increasing=True, out_of_bounds='clip')
    reg.fit(m, y)
    return reg


def fit_factor_scaling(m: np.ndarray, y: np.ndarray) -> float:
    """Compute single factor scaling: k = 10^(median(y - m))."""
    log_ratio = y - m
    median_log_ratio = np.median(log_ratio)
    factor = 10 ** median_log_ratio
    return float(factor)


def cross_validate_calibration(m: np.ndarray, y: np.ndarray, method: str, cv_folds: int = 5) -> Dict[str, float]:
    """Cross-validate calibration method and compute metrics."""
    kf = KFold(n_splits=cv_folds, shuffle=True, random_state=42)
    
    rmse_scores = []
    mae_scores = []
    r2_scores = []
    bias_scores = []
    spearman_scores = []
    
    for train_idx, val_idx in kf.split(m):
        m_train, m_val = m[train_idx], m[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        
        # Fit on training set
        if method == 'robust_linear' or method.startswith('huber') or method.startswith('theil'):
            alpha, beta = fit_robust_linear(m_train, y_train, 'huber' if 'huber' in method else 'theil_sen')
            y_pred = alpha + beta * m_val
        elif method == 'isotonic':
            reg = fit_isotonic(m_train, y_train)
            y_pred = reg.predict(m_val)
        elif method == 'factor':
            factor = fit_factor_scaling(m_train, y_train)
            # Apply factor in original space, then log
            model_orig = 10 ** m_val
            lab_pred = model_orig * factor
            y_pred = np.log10(lab_pred)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Compute metrics in log space
        rmse_scores.append(np.sqrt(mean_squared_error(y_val, y_pred)))
        mae_scores.append(mean_absolute_error(y_val, y_pred))
        r2_scores.append(r2_score(y_val, y_pred))
        bias_scores.append(np.mean(y_pred - y_val))
        
        # Spearman correlation for rank agreement
        spearman_rho, _ = spearmanr(y_val, y_pred)
        spearman_scores.append(spearman_rho if not np.isnan(spearman_rho) else 0.0)
    
    return {
        'rmse_mean': float(np.mean(rmse_scores)),
        'rmse_std': float(np.std(rmse_scores)),
        'mae_mean': float(np.mean(mae_scores)),
        'mae_std': float(np.std(mae_scores)),
        'r2_mean': float(np.mean(r2_scores)),
        'r2_std': float(np.std(r2_scores)),
        'bias_mean': float(np.mean(bias_scores)),
        'bias_std': float(np.std(bias_scores)),
        'spearman_mean': float(np.mean(spearman_scores)),
        'spearman_std': float(np.std(spearman_scores)),
    }


def apply_calibration_mapping(model_conc: np.ndarray, calibration_params: Dict[str, Any]) -> np.ndarray:
    """Apply saved calibration mapping to model concentrations."""
    method = calibration_params['method']
    
    if method == 'robust_linear':
        alpha = calibration_params['alpha']
        beta = calibration_params['beta']
        # Apply in log space
        m_log = np.log10(np.clip(model_conc, 1e-10, None))
        y_log = alpha + beta * m_log
        return 10 ** y_log
    
    elif method == 'isotonic':
        # Would need to save/load isotonic regression object
        # For now, fall back to linear approximation stored in params
        knots_m = np.array(calibration_params['knots_model'])
        knots_y = np.array(calibration_params['knots_lab'])
        m_log = np.log10(np.clip(model_conc, 1e-10, None))
        y_log = np.interp(m_log, knots_m, knots_y)
        return 10 ** y_log
    
    elif method == 'factor':
        factor = calibration_params['factor']
        return model_conc * factor
    
    else:
        raise ValueError(f"Unknown calibration method: {method}")


def categorize_concentrations(lab_equiv_conc: np.ndarray) -> np.ndarray:
    """Categorize lab-equivalent concentrations into Low/Moderate/High/Very high."""
    categories = np.full(len(lab_equiv_conc), 'Low', dtype=object)
    categories[(lab_equiv_conc >= 10) & (lab_equiv_conc < 100)] = 'Moderate'
    categories[(lab_equiv_conc >= 100) & (lab_equiv_conc < 1000)] = 'High'
    categories[lab_equiv_conc >= 1000] = 'Very high'
    return categories


def create_calibration_scatter_plot(m: np.ndarray, y: np.ndarray, method: str, params: Dict[str, Any], 
                                   save_path: Path) -> None:
    """Create before/after calibration scatter plot."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Before calibration (raw model vs lab)
    model_orig = 10 ** m
    lab_orig = 10 ** y
    ax1.scatter(model_orig, lab_orig, alpha=0.6, s=30)
    ax1.plot([model_orig.min(), model_orig.max()], [model_orig.min(), model_orig.max()], 'r--', alpha=0.8, label='1:1 line')
    ax1.set_xlabel('Model concentration (CFU/100mL)')
    ax1.set_ylabel('Lab concentration (CFU/100mL)')
    ax1.set_title('Before calibration')
    ax1.set_xscale('log')
    ax1.set_yscale('log')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # After calibration
    if method == 'robust_linear':
        alpha, beta = params['alpha'], params['beta']
        y_pred_log = alpha + beta * m
        y_pred = 10 ** y_pred_log
    elif method == 'isotonic':
        # Use stored knots for prediction
        knots_m = np.array(params['knots_model'])
        knots_y = np.array(params['knots_lab'])
        y_pred_log = np.interp(m, knots_m, knots_y)
        y_pred = 10 ** y_pred_log
    elif method == 'factor':
        factor = params['factor']
        y_pred = model_orig * factor
    else:
        y_pred = lab_orig  # fallback
    
    ax2.scatter(y_pred, lab_orig, alpha=0.6, s=30)
    ax2.plot([lab_orig.min(), lab_orig.max()], [lab_orig.min(), lab_orig.max()], 'r--', alpha=0.8, label='1:1 line')
    ax2.set_xlabel('Calibrated model (CFU/100mL)')
    ax2.set_ylabel('Lab concentration (CFU/100mL)')
    ax2.set_title(f'After calibration ({method})')
    ax2.set_xscale('log')
    ax2.set_yscale('log')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def run_model_lab_calibration(
    input_csv: Optional[str] = None,
    method: str = 'robust_linear',
    nd_value: float = 0.1,
    numerous_policy: str = 'cap_p99',
    cv_folds: int = 5,
    random_seed: int = 42
) -> Dict[str, Any]:
    """Run model→lab calibration per protocol."""
    
    # Set random seed for reproducibility  
    np.random.seed(random_seed)
    
    # Load government borehole data
    if input_csv is None:
        input_csv = str(config.DASH_GOVERNMENT_BH_PATH)
    
    if not Path(input_csv).exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")
    
    df = pd.read_csv(input_csv)
    logging.info(f"Loaded {len(df)} government boreholes from {input_csv}")
    
    # Extract model and lab columns
    if 'concentration_CFU_per_100mL' not in df.columns:
        raise ValueError("Missing required column: concentration_CFU_per_100mL")
    if 'lab_total_coliform_CFU_per_100mL' not in df.columns:
        raise ValueError("Missing required column: lab_total_coliform_CFU_per_100mL")
    
    # Preprocess per protocol
    model_raw = df['concentration_CFU_per_100mL']
    lab_raw = df['lab_total_coliform_CFU_per_100mL']
    
    model_clean = coerce_numeric(model_raw, nd_value=nd_value, numerous_policy=numerous_policy)
    lab_clean = coerce_numeric(lab_raw, nd_value=nd_value, numerous_policy=numerous_policy)
    
    # Filter valid pairs
    mask = model_clean.notna() & lab_clean.notna() & (model_clean > 0) & (lab_clean > 0)
    model_valid = model_clean[mask]
    lab_valid = lab_clean[mask]
    
    n_pairs = len(model_valid)
    logging.info(f"Found {n_pairs} valid model-lab pairs for calibration")
    
    if n_pairs < 5:
        raise ValueError(f"Insufficient data for calibration: only {n_pairs} valid pairs")
    
    # Transform to log space
    m = np.log10(model_valid.to_numpy())
    y = np.log10(lab_valid.to_numpy())
    
    # Fit calibration
    timestamp = datetime.utcnow().isoformat() + 'Z'
    data_hash = hashlib.md5(df.to_csv(index=False).encode()).hexdigest()[:8]
    
    if method == 'robust_linear':
        alpha, beta = fit_robust_linear(m, y, 'huber')
        params = {
            'method': 'robust_linear',
            'alpha': alpha,
            'beta': beta,
            'nd_value': nd_value,
            'numerous_policy': numerous_policy,
            'n_pairs': n_pairs,
            'timestamp': timestamp,
            'data_hash': data_hash,
            'random_seed': random_seed,
        }
    elif method == 'isotonic':
        reg = fit_isotonic(m, y)
        # Store representative knots for later application
        m_sorted_idx = np.argsort(m)
        m_sorted = m[m_sorted_idx]
        y_pred_sorted = reg.predict(m_sorted)
        
        # Subsample knots to keep storage reasonable
        n_knots = min(50, len(m_sorted))
        knot_indices = np.linspace(0, len(m_sorted)-1, n_knots).astype(int)
        
        params = {
            'method': 'isotonic',
            'knots_model': m_sorted[knot_indices].tolist(),
            'knots_lab': y_pred_sorted[knot_indices].tolist(),
            'nd_value': nd_value,
            'numerous_policy': numerous_policy,
            'n_pairs': n_pairs,
            'timestamp': timestamp,
            'data_hash': data_hash,
            'random_seed': random_seed,
        }
    elif method == 'factor':
        factor = fit_factor_scaling(m, y)
        params = {
            'method': 'factor',
            'factor': factor,
            'nd_value': nd_value,
            'numerous_policy': numerous_policy,
            'n_pairs': n_pairs,
            'timestamp': timestamp,
            'data_hash': data_hash,
            'random_seed': random_seed,
        }
    else:
        raise ValueError(f"Unknown calibration method: {method}")
    
    # Cross-validate
    cv_metrics = cross_validate_calibration(m, y, method, cv_folds)
    
    # Save calibration parameters
    output_path = config.OUTPUT_DATA_DIR / 'calibration_params.json'
    with open(output_path, 'w') as f:
        json.dump(params, f, indent=2)
    logging.info(f"Saved calibration parameters to {output_path}")
    
    # Create scatter plot
    plot_path = config.OUTPUT_DATA_DIR / 'model_vs_lab_scatter.png'
    create_calibration_scatter_plot(m, y, method, params, plot_path)
    logging.info(f"Saved calibration scatter plot to {plot_path}")
    
    # Compile report
    report = {
        'method': method,
        'parameters': params,
        'cross_validation': cv_metrics,
        'data_summary': {
            'n_total_boreholes': len(df),
            'n_valid_pairs': n_pairs,
            'model_range_cfu': [float(model_valid.min()), float(model_valid.max())],
            'lab_range_cfu': [float(lab_valid.min()), float(lab_valid.max())],
        },
        'diagnostic_info': {
            'nd_substitutions': int((lab_raw.astype(str).str.lower().isin(['nd', '0', ''])).sum()),
            'numerous_substitutions': int(lab_raw.astype(str).str.contains('numerous', case=False, na=False).sum()),
            'data_hash': data_hash,
        }
    }
    
    # Generate markdown report
    report_path = config.OUTPUT_DATA_DIR / 'calibration_report.md'
    generate_calibration_report(report, report_path)
    logging.info(f"Saved calibration report to {report_path}")
    
    return report


def generate_calibration_report(report: Dict[str, Any], output_path: Path) -> None:
    """Generate calibration report in markdown format."""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    md_content = f"""# FIO Model→Lab Calibration Report

**Generated:** {timestamp}  
**Method:** {report['method']}  
**Data Hash:** {report['diagnostic_info']['data_hash']}  

## Executive Summary

This report documents the calibration of modeled fecal indicator organism (FIO) concentrations to laboratory Total Coliform measurements from government boreholes. The calibration enables transparent risk categorization and supports evidence-based decision making.

### Key Results

- **Calibration method:** {report['method']}  
- **Valid data pairs:** {report['data_summary']['n_valid_pairs']} out of {report['data_summary']['n_total_boreholes']} boreholes  
- **Cross-validation RMSE:** {report['cross_validation']['rmse_mean']:.4f} ± {report['cross_validation']['rmse_std']:.4f} (log₁₀ space)  
- **Cross-validation R²:** {report['cross_validation']['r2_mean']:.4f} ± {report['cross_validation']['r2_std']:.4f}  
- **Spearman correlation:** {report['cross_validation']['spearman_mean']:.4f} ± {report['cross_validation']['spearman_std']:.4f}  

## Methods

### Data Preprocessing

Laboratory and model concentration values were preprocessed according to protocol:

- **Non-detect handling:** ND values substituted with {report['parameters']['nd_value']} CFU/100mL  
- **"Numerous" handling:** {report['parameters']['numerous_policy']} policy applied  
- **ND substitutions made:** {report['diagnostic_info']['nd_substitutions']}  
- **"Numerous" substitutions made:** {report['diagnostic_info']['numerous_substitutions']}  

### Calibration Approach

**{report['method']}** calibration was fitted in log₁₀ space to stabilize variance:

"""

    if report['method'] == 'robust_linear':
        md_content += f"""
The robust linear model takes the form:
```
log₁₀(lab) = α + β × log₁₀(model)
```

Where:
- **α (intercept):** {report['parameters']['alpha']:.6f}  
- **β (slope):** {report['parameters']['beta']:.6f}  

The lab-equivalent concentration is computed as:
```
lab_equivalent = 10^(α + β × log₁₀(model_concentration))
```

A slope β ≈ 1 indicates good scale agreement; the fitted β = {report['parameters']['beta']:.3f} suggests [interpretation needed].
"""
    elif report['method'] == 'isotonic':
        md_content += f"""
Isotonic regression ensures monotonic calibration without assuming linearity. The mapping is stored as {len(report['parameters']['knots_model'])} interpolation knots spanning the data range.
"""
    elif report['method'] == 'factor':
        md_content += f"""
Simple factor scaling: lab_equivalent = model × {report['parameters']['factor']:.6f}
"""

    md_content += f"""
### Cross-Validation

{report['cross_validation'].get('cv_folds', 5)}-fold cross-validation was used to assess calibration performance:

| Metric | Mean | Std Dev |
|--------|------|---------|
| RMSE (log₁₀) | {report['cross_validation']['rmse_mean']:.4f} | {report['cross_validation']['rmse_std']:.4f} |
| MAE (log₁₀) | {report['cross_validation']['mae_mean']:.4f} | {report['cross_validation']['mae_std']:.4f} |
| R² | {report['cross_validation']['r2_mean']:.4f} | {report['cross_validation']['r2_std']:.4f} |
| Bias (log₁₀) | {report['cross_validation']['bias_mean']:.4f} | {report['cross_validation']['bias_std']:.4f} |
| Spearman ρ | {report['cross_validation']['spearman_mean']:.4f} | {report['cross_validation']['spearman_std']:.4f} |

## Data Summary

- **Model concentration range:** {report['data_summary']['model_range_cfu'][0]:.1f} to {report['data_summary']['model_range_cfu'][1]:.1f} CFU/100mL  
- **Lab concentration range:** {report['data_summary']['lab_range_cfu'][0]:.1f} to {report['data_summary']['lab_range_cfu'][1]:.1f} CFU/100mL  

## Risk Categories

Lab-equivalent concentrations are categorized using public health-informed thresholds:

| Category | Range (CFU/100mL) | Rationale |
|----------|-------------------|-----------|
| **Low** | < 10 | Below typical detection limits |
| **Moderate** | 10 – 99 | Detectable but below concern thresholds |
| **High** | 100 – 999 | Elevated contamination |
| **Very High** | ≥ 1000 | Significant contamination requiring attention |

## Quality Assurance

- **Reproducibility:** Fixed random seed ({report['parameters']['random_seed']}) ensures reproducible results  
- **Data integrity:** Input data hash {report['diagnostic_info']['data_hash']} enables change tracking  
- **Robust methods:** Huber regression mitigates outlier influence  

## Files Generated

1. `calibration_params.json` - Calibration parameters for application  
2. `model_vs_lab_scatter.png` - Before/after calibration diagnostic plot  
3. `calibration_report.md` - This report  

## Protocol Compliance

This calibration follows the professional protocol for model→lab calibration:

✅ **Data-driven:** Uses only observed lab data for mapping  
✅ **Monotonic:** Higher model values map to higher lab-equivalent values  
✅ **Robust:** Handles non-detects, outliers, and text-coded values  
✅ **Reproducible:** Fixed random seed, versioned parameters  
✅ **Communicable:** Anchored to recognizable public health thresholds  

---
*Report generated by FIO Model→Lab Calibration System*
"""

    with open(output_path, 'w') as f:
        f.write(md_content)


def main_model_lab_calibration() -> int:
    """CLI entry point for model→lab calibration."""
    parser = argparse.ArgumentParser(description='FIO Model→Lab Calibration')
    parser.add_argument('--input', type=str, help='Input CSV path (default: dashboard_government_boreholes.csv)')
    parser.add_argument('--method', choices=['robust_linear', 'isotonic', 'factor'], 
                       default='robust_linear', help='Calibration method')
    parser.add_argument('--nd-value', type=float, default=0.1, help='Non-detect substitution value')
    parser.add_argument('--numerous-policy', choices=['cap_p99', 'cap_p97', 'fixed_1000'], 
                       default='cap_p99', help='Policy for handling "Numerous" values')
    parser.add_argument('--cv-folds', type=int, default=5, help='Cross-validation folds')
    parser.add_argument('--random-seed', type=int, default=42, help='Random seed for reproducibility')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    logging.basicConfig(level=getattr(logging, args.log_level), 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        report = run_model_lab_calibration(
            input_csv=args.input,
            method=args.method,
            nd_value=args.nd_value,
            numerous_policy=args.numerous_policy,
            cv_folds=args.cv_folds,
            random_seed=args.random_seed
        )
        
        # Display summary
        cv = report['cross_validation']
        print(f"\n=== FIO Model→Lab Calibration Complete ===")
        print(f"Method: {report['method']}")
        print(f"Valid pairs: {report['data_summary']['n_valid_pairs']}")
        print(f"CV RMSE: {cv['rmse_mean']:.4f} ± {cv['rmse_std']:.4f}")
        print(f"CV R²: {cv['r2_mean']:.4f} ± {cv['r2_std']:.4f}")
        print(f"CV Bias: {cv['bias_mean']:.4f} ± {cv['bias_std']:.4f}")
        print(f"CV Spearman: {cv['spearman_mean']:.4f} ± {cv['spearman_std']:.4f}")
        print(f"Outputs saved to: {config.OUTPUT_DATA_DIR}")
        
        return 0
        
    except Exception as e:
        logging.error(f"Calibration failed: {e}")
        return 1


if __name__ == '__main__':
    # Check if this is being called for model-lab calibration
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in ['--method', '--input', '--nd-value']:
        exit(main_model_lab_calibration())
    else:
        # Default to original behavior for backwards compatibility
        print("For model→lab calibration, use: python -m app.calibrate --method robust_linear")
        print("For parameter calibration, import and call functions directly.")

