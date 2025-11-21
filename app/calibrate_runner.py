import pandas as pd
import numpy as np
import logging
from app import engine
from app.calibration_engine import CalibrationEngine

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_grid_search():
    """
    Run a grid search to find optimal parameters for the FIO model.
    Parameters tuned:
    - Decay Rate (ks_per_m): Controls how fast pathogens die.
    - Base Load (EFIO_override): Controls how many pathogens are produced.
    
    UPDATED SEARCH SPACE (Post-Assessment):
    - Lower decay rates for karst conduit flow (pathogens survive longer)
    - Broader EFIO range to account for magnitude uncertainty after unit fix
    """
    
    # Define Expanded Search Space
    # Decay: 0.001 to 0.05 (Expanded for karst conduits)
    decay_rates = [0.001, 0.005, 0.01, 0.02, 0.03, 0.05]
    
    # EFIO: 1e7 to 1e10 (Broader range post unit-fix)
    efio_values = [1e7, 5e7, 1e8, 5e8, 1e9, 5e9, 1e10]
    
    results = []
    calib = CalibrationEngine()
    
    print(f"Starting Grid Search: {len(decay_rates) * len(efio_values)} combinations")
    
    for decay in decay_rates:
        for efio in efio_values:
            print(f"Testing: Decay={decay}, EFIO={efio:.0e}")
            
            # 1. Run Pipeline with Override
            override = {
                'ks_per_m': decay,
                'EFIO_override': efio
            }
            
            # We suppress logs to keep output clean
            logging.getLogger().setLevel(logging.WARNING)
            engine.run_pipeline('fio', scenario_override=override)
            logging.getLogger().setLevel(logging.INFO)
            
            # 2. Evaluate
            if calib.load_model_results('fio'):
                matched = calib.match_points()
                metrics = calib.calculate_metrics(matched)
                
                res = {
                    'decay_rate': decay,
                    'efio': efio,
                    'rmse_log': metrics.get('rmse_log', np.nan),
                    'bias_log': metrics.get('bias_log', np.nan),
                    'correlation': metrics.get('correlation', np.nan)
                }
                results.append(res)
                print(f"  -> RMSE: {res['rmse_log']:.4f}, Corr: {res['correlation']:.4f}")
            else:
                print("  -> Failed to load results")

    # 3. Analyze Results
    df = pd.DataFrame(results)
    
    if df.empty or df['rmse_log'].isna().all():
        print("No valid results generated.")
        return
        
    # Find Best RMSE
    best_rmse = df.loc[df['rmse_log'].idxmin()]
    
    # Find Best Correlation
    best_corr = df.loc[df['correlation'].idxmax()]
    
    print("\n" + "="*40)
    print("CALIBRATION RESULTS")
    print("="*40)
    print("\nBest RMSE Configuration:")
    print(best_rmse)
    
    print("\nBest Correlation Configuration:")
    print(best_corr)
    
    # Save to CSV
    df.to_csv('calibration_results.csv', index=False)
    print("\nFull results saved to 'calibration_results.csv'")

if __name__ == "__main__":
    run_grid_search()
