from app import calibration_utils
from app.calibration_engine import CalibrationEngine
import pandas as pd

# 1. Load Raw Data via Utils
df = calibration_utils.load_government_data()
print(f"Rows loaded by utils: {len(df)}")

# 2. Check for duplicates
print(f"Duplicates: {df.duplicated().sum()}")

# 3. Check valid samples for calibration
# We need to match with model data to see final n_samples
calib = CalibrationEngine()
if calib.load_model_results('fio'):
    matched = calib.match_points()
    metrics = calib.calculate_metrics(matched)
    print(f"Final n_samples used in metrics: {metrics.get('n_samples')}")
else:
    print("Could not load model results to verify n_samples")
