import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
import logging
from app import config
from app import calibration_utils

class CalibrationEngine:
    def __init__(self):
        self.obs_df = calibration_utils.load_government_data()
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
        Match each government observation to the nearest model prediction point.
        Returns DataFrame with matched pairs.
        """
        if self.obs_df.empty or self.model_df.empty:
            return pd.DataFrame()
            
        # Build BallTree on model points
        # Convert lat/long to radians for BallTree
        model_rad = np.radians(self.model_df[['lat', 'long']].values)
        obs_rad = np.radians(self.obs_df[['lat', 'long']].values)
        
        tree = BallTree(model_rad, metric='haversine')
        
        # Query nearest neighbor for each observation
        dist, ind = tree.query(obs_rad, k=1)
        
        # Create matched DataFrame
        matched = self.obs_df.copy()
        matched['model_idx'] = ind.flatten()
        matched['dist_m'] = dist.flatten() * 6371000 # Convert rad to meters
        
        # Join model values
        # We use iloc to fetch rows by integer index
        model_vals = self.model_df.iloc[matched['model_idx']].reset_index(drop=True)
        
        # Combine
        matched['model_conc'] = model_vals['concentration_CFU_per_100mL'].values
        matched['model_lat'] = model_vals['lat'].values
        matched['model_long'] = model_vals['long'].values
        
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
        from scipy.stats import median_abs_deviation, spearmanr
        mad = median_abs_deviation(log_true - log_pred, nan_policy='omit')
        
        # Spearman rank correlation (robust to outliers, preserves monotonic relationships)
        spearman_rho, spearman_p = spearmanr(y_true, y_pred, nan_policy='omit')
        
        return {
            'n_samples': len(valid),
            'rmse_log': rmse,
            'bias_log': bias,
            'correlation': valid['fio_obs'].corr(valid['model_conc']),
            'mad': mad,
            'spearman_rho': spearman_rho,
            'spearman_p': spearman_p
        }
