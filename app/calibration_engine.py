import pandas as pd
import numpy as np

import logging
from scipy.stats import spearmanr, kendalltau, median_abs_deviation
from app import config
from app import calibration_utils

class CalibrationEngine:
    def __init__(self):
        # No longer loading external obs file, will use model output directly
        self.model_df = pd.DataFrame()
        
    def load_model_results(self, model_type='fio'):
        """Load the latest model results."""
        path = config.FIO_CONCENTRATION_PATH if model_type == 'fio' else config.NET_NITROGEN_LOAD_PATH
        if not path.exists():
            logging.warning(f"Model results not found at {path}")
            return False
            
        self.model_df = pd.read_csv(path)
        return True

    def match_points(self):
        """
        Prepare matched DataFrame from model results.
        Since model output preserves input columns, we just need to:
        1. Filter for government boreholes
        2. Parse the observed 'Total Coli' column
        """
        if self.model_df.empty:
            return pd.DataFrame()
            
        # Filter for government boreholes only
        # (Private wells don't have lab data in this context)
        if 'borehole_type' in self.model_df.columns:
            matched = self.model_df[self.model_df['borehole_type'] == 'government'].copy()
        else:
            # Fallback if column missing (unlikely)
            matched = self.model_df.copy()
            
        # Check if observation column exists
        if 'Total Coli' not in matched.columns:
            logging.warning("'Total Coli' column not found in model output. Cannot calibrate.")
            return pd.DataFrame()
            
        # Parse observations using the utility function
        matched['fio_obs'] = matched['Total Coli'].apply(calibration_utils.parse_concentration)
        
        # Rename model prediction to standard name for metrics
        matched['model_conc'] = matched['concentration_CFU_per_100mL']
        
        # Keep coordinates for debugging/plotting if needed
        matched['model_lat'] = matched['lat']
        matched['model_long'] = matched['long']
        
        return matched


    def calculate_metrics(self, matched_df):
        """Calculate RMSE and other metrics, including robust alternatives."""
        if matched_df.empty:
            return {}
            
        # Filter valid pairs (ignore NaNs)
        valid = matched_df.dropna(subset=['fio_obs', 'model_conc'])
        
        if valid.empty:
            return {}
            
        y_true = valid['fio_obs']
        y_pred = valid['model_conc']
        
        # Log-space RMSE (since concentrations vary by orders of magnitude)
        # Add 1 to avoid log(0)
        log_true = np.log1p(y_true)
        log_pred = np.log1p(y_pred)
        
        rmse = np.sqrt(((log_true - log_pred) ** 2).mean())
        bias = (log_pred - log_true).mean()
        
        # Robust metrics (less sensitive to outliers)
        mad = median_abs_deviation(log_true - log_pred, nan_policy='omit')
        
        # Rank correlations (raw + log space)
        spearman_rho, spearman_p = spearmanr(y_true, y_pred, nan_policy='omit')
        spearman_log, _ = spearmanr(log_true, log_pred, nan_policy='omit')
        kendall_rho, kendall_p = kendalltau(y_true, y_pred, nan_policy='omit')
        
        return {
            'n_samples': len(valid),
            'rmse_log': rmse,
            'bias_log': bias,
            'correlation': valid['fio_obs'].corr(valid['model_conc']),
            'correlation_log': log_true.corr(log_pred),
            'mad': mad,
            'spearman_rho': spearman_rho,
            'spearman_log_rho': spearman_log,
            'spearman_p': spearman_p,
            'kendall_rho': kendall_rho,
            'kendall_p': kendall_p
        }
