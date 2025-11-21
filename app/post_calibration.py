"""Post-calibration utilities for log-space rescaling and validation.

Provides empirical correction to align model magnitudes with observations
without requiring new data or physical model changes.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Risk Tier Thresholds (CFU/100mL)
# Based on WHO drinking water guidelines and local context
RISK_TIERS_OBSERVED = {
    'Low': (0, 10),        # Safe for consumption
    'Medium': (10, 50),    # Treatment recommended
    'High': (50, np.inf)   # Unsafe, immediate action required
}

# Calibrated thresholds for MODEL PREDICTIONS
# Account for systematic 3.3× overestimation (median pred: 81 vs obs: 24.5)
# These higher thresholds map model predictions to equivalent observed risk levels
CALIBRATION_FACTOR = 3.3  # Model overestimation factor (after unit fix)
RISK_TIERS_PREDICTED = {
    'Low': (0, 10 * CALIBRATION_FACTOR),        # <33 CFU/100mL
    'Medium': (10 * CALIBRATION_FACTOR, 50 * CALIBRATION_FACTOR),  # 33-165 CFU/100mL
    'High': (50 * CALIBRATION_FACTOR, np.inf)   # >165 CFU/100mL
}


def apply_log_correction(predicted: np.ndarray, 
                         obs_log_mean: float, 
                         pred_log_mean: float) -> np.ndarray:
    """
    Shift predicted concentrations in log-space to match observed mean.
    
    This accounts for unknown systematic biases (flow rate errors, EFIO uncertainty, etc.)
    without changing relative rankings between predictions.
    
    Args:
        predicted: Array of predicted concentrations (linear scale)
        obs_log_mean: Mean of log(observed + 1) from calibration data
        pred_log_mean: Mean of log(predicted + 1) from current predictions
        
    Returns:
        Array of corrected predictions (linear scale)
    """
    # Convert to log-space
    log_pred = np.log1p(predicted)
    
    # Shift to match observed mean
    shift = obs_log_mean - pred_log_mean
    corrected_log = log_pred + shift
    
    # Back to linear scale
    return np.expm1(corrected_log)


def cross_validate_correction(obs: pd.Series, 
                               pred: pd.Series, 
                               n_folds: int = 5) -> Dict[str, float]:
    """
    Perform k-fold cross-validation of log-space correction.
    
    Tests whether empirical correction generalizes or just overfits to training data.
    
    Args:
        obs: Observed concentrations
        pred: Predicted concentrations (before correction)
        n_folds: Number of CV folds
        
    Returns:
        Dictionary with CV performance metrics
    """
    from sklearn.model_selection import KFold
    from scipy.stats import spearmanr
    
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)
    
    cv_scores = {
        'rmse_log': [],
        'spearman_rho': [],
        'pearson_r': []
    }
    
    for train_idx, test_idx in kf.split(obs):
        # Split data
        obs_train, obs_test = obs.iloc[train_idx], obs.iloc[test_idx]
        pred_train, pred_test = pred.iloc[train_idx], pred.iloc[test_idx]
        
        # Fit correction on training set
        obs_log_mean = np.log1p(obs_train).mean()
        pred_log_mean = np.log1p(pred_train).mean()
        
        # Apply to test set
        pred_test_corrected = apply_log_correction(pred_test.values, obs_log_mean, pred_log_mean)
        
        # Evaluate
        log_obs = np.log1p(obs_test)
        log_pred_corr = np.log1p(pred_test_corrected)
        
        rmse = np.sqrt(((log_obs - log_pred_corr) ** 2).mean())
        spearman_rho, _ = spearmanr(obs_test, pred_test_corrected)
        pearson_r = obs_test.corr(pd.Series(pred_test_corrected))
        
        cv_scores['rmse_log'].append(rmse)
        cv_scores['spearman_rho'].append(spearman_rho)
        cv_scores['pearson_r'].append(pearson_r)
    
    return {
        'mean_rmse_log_cv': np.mean(cv_scores['rmse_log']),
        'std_rmse_log_cv': np.std(cv_scores['rmse_log']),
        'mean_spearman_cv': np.mean(cv_scores['spearman_rho']),
        'std_spearman_cv': np.std(cv_scores['spearman_rho']),
        'mean_pearson_cv': np.mean(cv_scores['pearson_r']),
        'std_pearson_cv': np.std(cv_scores['pearson_r'])
    }


def validate_rankings(obs: pd.Series, pred: pd.Series) -> Dict[str, float]:
    """
    Validate model performance based on risk tier classification and rankings.
    
    Better suited for policy use-case (identifying high-risk areas) than
    absolute concentration accuracy.
    
    Args:
        obs: Observed concentrations
        pred: Predicted concentrations
        
    Returns:
        Dictionary with ranking validation metrics
    """
    from scipy.stats import spearmanr
    
    # Define risk tiers based on WHO guidelines / local standards
    # For OBSERVED values (ground truth):
    # Low: <10 CFU/100mL, Medium: 10-50, High: >50
    obs_bins = [0, 10, 50, np.inf]
    
    # For PREDICTED values: adjust thresholds by ~3.3× overestimation factor
    # Model median: 81 vs Observed median: 24.5 → ratio = 3.3
    # So predicted thresholds should be 3.3× higher to align with observed tiers
    calibration_factor = 3.3
    pred_bins = [0, 10 * calibration_factor, 50 * calibration_factor, np.inf]
    
    obs_tier = pd.cut(obs, bins=obs_bins, labels=['Low', 'Med', 'High'])
    pred_tier = pd.cut(pred, bins=pred_bins, labels=['Low', 'Med', 'High'])
    
    # Tier classification accuracy
    tier_accuracy = (obs_tier == pred_tier).mean()
    
    # Identify top 20% highest risk (for intervention targeting)
    obs_top20_threshold = obs.quantile(0.8)
    pred_top20_threshold = pred.quantile(0.8)
    
    obs_top20 = obs >= obs_top20_threshold
    pred_top20 = pred >= pred_top20_threshold
    
    # Overlap between observed and predicted high-risk wells
    true_positives = (obs_top20 & pred_top20).sum()
    false_positives = (~obs_top20 & pred_top20).sum()
    false_negatives = (obs_top20 & ~pred_top20).sum()
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    # Spearman rank correlation
    spearman_rho, spearman_p = spearmanr(obs, pred)
    
    return {
        'tier_accuracy': tier_accuracy,
        'top20_precision': precision,
        'top20_recall': recall,
        'top20_f1': f1_score,
        'spearman_rho': spearman_rho,
        'spearman_p': spearman_p,
        'n_samples': len(obs)
    }


if __name__ == '__main__':
    # Test with actual data
    from app.calibration_engine import CalibrationEngine
    
    calib = CalibrationEngine()
    if calib.load_model_results('fio'):
        matched = calib.match_points()
        
        if not matched.empty:
            obs = matched['fio_obs'].dropna()
            pred = matched['model_conc'].loc[obs.index]
            
            print("=== Ranking Validation ===")
            rank_metrics = validate_rankings(obs, pred)
            for key, val in rank_metrics.items():
                print(f"{key}: {val:.4f}" if isinstance(val, float) else f"{key}: {val}")
            
            print("\n=== Cross-Validation of Log Correction ===")
            cv_metrics = cross_validate_correction(obs, pred, n_folds=5)
            for key, val in cv_metrics.items():
                print(f"{key}: {val:.4f}")
