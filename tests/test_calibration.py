import unittest
import pandas as pd
import numpy as np
from app.calibration_engine import CalibrationEngine
from app import config

class TestCalibrationEngine(unittest.TestCase):
    def setUp(self):
        self.engine = CalibrationEngine()
        
    def test_load_data(self):
        # This might fail if files don't exist, so we mock or check existence
        if config.GOVERNMENT_BOREHOLES_PATH.exists():
            self.assertFalse(self.engine.obs_df.empty)
            self.assertIn('fio_obs', self.engine.obs_df.columns)
            
    def test_match_logic(self):
        # Create dummy data
        self.engine.obs_df = pd.DataFrame({
            'lat': [0, 1],
            'long': [0, 1],
            'fio_obs': [10, 100]
        })
        self.engine.model_df = pd.DataFrame({
            'lat': [0.0001, 1.0001], # Very close
            'long': [0, 1],
            'concentration_CFU_per_100mL': [12, 90]
        })
        
        matched = self.engine.match_points()
        self.assertEqual(len(matched), 2)
        self.assertIn('model_conc', matched.columns)
        self.assertIn('dist_m', matched.columns)
        
        # Check metrics
        metrics = self.engine.calculate_metrics(matched)
        self.assertIn('rmse_log', metrics)
        self.assertIn('correlation', metrics)

if __name__ == '__main__':
    unittest.main()
