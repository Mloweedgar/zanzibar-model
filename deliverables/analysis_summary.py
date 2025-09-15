#!/usr/bin/env python3
"""
Generate analysis tables and figures for Zanzibar FIO model deliverables.
"""
import pandas as pd
import numpy as np
import json
import os
import matplotlib.pyplot as plt
from scipy.stats import spearmanr, kendalltau, pearsonr

def _load_model_thresholds(defaults=(10.0, 100.0, 1000.0)) -> tuple[float, float, float]:
    """Load model-side category thresholds from calibration_mapping.json with fallback."""
    mapping_path = os.path.join('data', 'output', 'calibration_mapping.json')
    try:
        with open(mapping_path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        node = data.get('category_thresholds_model_CFU_per_100mL')
        t1 = float(node['Low_Upper'])
        t2 = float(node['Moderate_Upper'])
        t3 = float(node['High_Upper'])
        if not (t1 > 0 and t2 > t1 and t3 > t2):
            raise ValueError('thresholds not strictly increasing')
        return (t1, t2, t3)
    except Exception:
        return defaults

def _categorizer(T1: float, T2: float, T3: float):
    def _cat(conc):
        try:
            x = float(conc)
        except Exception:
            return 'Unknown'
        if np.isnan(x) or x < 0:
            return 'Unknown'
        if x < T1:
            return 'Low'
        if x < T2:
            return 'Moderate'
        if x < T3:
            return 'High'
        return 'Very High'
    return _cat

def _fmt_large(x) -> str:
    try:
        x = float(x)
        a = abs(x)
        if a >= 1e12: return f"{x/1e12:.1f}T"
        if a >= 1e9: return f"{x/1e9:.1f}B"
        if a >= 1e6: return f"{x/1e6:.1f}M"
        if a >= 1e3: return f"{x/1e3:.1f}K"
        return f"{x:.0f}"
    except Exception:
        return "-"

def _fmt_float(x, prec=3) -> str:
    try:
        if x is None:
            return 'N/A'
        xf = float(x)
        if np.isnan(xf):
            return 'N/A'
        return f"{xf:.{prec}f}"
    except Exception:
        return 'N/A'

def categorize_concentration(conc):
    """Categorize concentration according to dashboard semantics."""
    if conc < 10: 
        return 'Low'
    elif conc < 100: 
        return 'Moderate'  
    elif conc < 1000: 
        return 'High'
    else: 
        return 'Very High'

def calculate_metrics(model_vals, lab_vals):
    """Calculate calibration metrics."""
    if len(model_vals) != len(lab_vals) or len(model_vals) == 0:
        return {}
    
    # Remove any NaN values
    mask = ~(np.isnan(model_vals) | np.isnan(lab_vals))
    if mask.sum() == 0:
        return {}
    
    model_clean = model_vals[mask]
    lab_clean = lab_vals[mask]
    
    # Spearman and Kendall rank correlations
    try:
        spear_rho, spear_p = spearmanr(model_clean, lab_clean)
        kendall_tau, kendall_p = kendalltau(model_clean, lab_clean)
    except:
        spear_rho = spear_p = kendall_tau = kendall_p = np.nan
    
    # Log-space analysis
    model_log = np.log10(model_clean + 1)
    lab_log = np.log10(lab_clean + 1)
    
    try:
        pearson_log, pearson_p = pearsonr(model_log, lab_log)
        rmse_log = np.sqrt(np.mean((model_log - lab_log)**2))
    except:
        pearson_log = pearson_p = rmse_log = np.nan
    
    return {
        'n': len(model_clean),
        'spearman_rho': spear_rho,
        'spearman_p': spear_p,
        'kendall_tau': kendall_tau,
        'kendall_p': kendall_p,
        'pearson_log': pearson_log,
        'pearson_p': pearson_p,
        'rmse_log': rmse_log
    }

def main():
    print("=== ZANZIBAR FIO MODEL ANALYSIS SUMMARY ===\n")
    
    # Load data
    try:
        gov_data = pd.read_csv('data/output/dashboard_government_boreholes.csv')
        private_data = pd.read_csv('data/output/dashboard_private_boreholes.csv')
        scenario_data = json.loads(open('data/output/last_scenario.json').read())
        all_boreholes = pd.read_csv('data/output/fio_concentration_at_boreholes.csv')
    except FileNotFoundError as e:
        print(f"Error: Could not find required data file: {e}")
        return
    
    print(f"Data loaded successfully:")
    print(f"- Government boreholes: {len(gov_data)}")
    print(f"- Private boreholes: {len(private_data)}")
    print(f"- All concentrations: {len(all_boreholes)}")
    print()
    
    # === SCENARIO PARAMETERS ===
    print("=== SCENARIO PARAMETERS (from last_scenario.json) ===")
    print(f"Scenario name: {scenario_data['scenario_name']}")
    params = scenario_data['parameters']
    for key, value in params.items():
        print(f"  {key}: {value}")
    print()
    # === CATEGORY THRESHOLDS (MODEL SIDE) ===
    T1, T2, T3 = _load_model_thresholds()
    print("=== CATEGORY THRESHOLDS (model side, CFU/100mL) ===")
    print(f"  Low: <{_fmt_large(T1)}  | Moderate: {_fmt_large(T1)}–{_fmt_large(T2)}  | High: {_fmt_large(T2)}–{_fmt_large(T3)}  | Very High: ≥{_fmt_large(T3)}")
    print()
    
    # === CONCENTRATION STATISTICS ===
    print("=== CONCENTRATION DISTRIBUTIONS ===")
    
    # Government boreholes
    gov_conc = gov_data['concentration_CFU_per_100mL']
    print("Government Boreholes (CFU/100mL):")
    print(f"  n = {len(gov_conc)}")
    print(f"  Median: {gov_conc.median():.1f}")
    print(f"  25th percentile: {gov_conc.quantile(0.25):.1f}")
    print(f"  75th percentile: {gov_conc.quantile(0.75):.1f}")
    print(f"  Maximum: {gov_conc.max():.1f}")
    print(f"  Minimum: {gov_conc.min():.3f}")
    print()
    
    # Private boreholes  
    priv_conc = private_data['concentration_CFU_per_100mL']
    print("Private Boreholes (CFU/100mL):")
    print(f"  n = {len(priv_conc)}")
    print(f"  Median: {priv_conc.median():.1f}")
    print(f"  25th percentile: {priv_conc.quantile(0.25):.1f}")
    print(f"  75th percentile: {priv_conc.quantile(0.75):.1f}")
    print(f"  Maximum: {priv_conc.max():.1f}")
    print(f"  Minimum: {priv_conc.min():.3f}")
    print()
    
    # === CONCENTRATION CATEGORIES ===
    print("=== CONCENTRATION CATEGORIES ===")
    
    # Government categories
    gov_data['category'] = gov_data['concentration_CFU_per_100mL'].apply(_categorizer(T1, T2, T3))
    gov_counts = gov_data['category'].value_counts()
    print("Government Boreholes:")
    desc_map = {
        'Low': f"<{_fmt_large(T1)}",
        'Moderate': f"{_fmt_large(T1)}–{_fmt_large(T2)}",
        'High': f"{_fmt_large(T2)}–{_fmt_large(T3)}",
        'Very High': f"≥{_fmt_large(T3)}",
    }
    for cat in ['Low', 'Moderate', 'High', 'Very High']:
        count = int(gov_counts.get(cat, 0))
        pct = (count/len(gov_data)*100) if len(gov_data) else 0.0
        print(f"  {cat} ({desc_map[cat]} CFU/100mL): {count} boreholes ({pct:.1f}%)")
    print()
    
    # Private categories  
    private_data['category'] = private_data['concentration_CFU_per_100mL'].apply(_categorizer(T1, T2, T3))
    priv_counts = private_data['category'].value_counts()
    print("Private Boreholes:")
    for cat in ['Low', 'Moderate', 'High', 'Very High']:
        count = int(priv_counts.get(cat, 0))
        pct = (count/len(private_data)*100) if len(private_data) else 0.0
        print(f"  {cat} ({desc_map[cat]} CFU/100mL): {count} boreholes ({pct:.1f}%)")
    print()
    
    # === TOP 10 TABLES ===
    print("=== TOP 10 HIGHEST CONCENTRATIONS (Government) ===")
    top10_gov = gov_data.nlargest(10, 'concentration_CFU_per_100mL')
    display_cols = ['borehole_id', 'Q_L_per_day', 'concentration_CFU_per_100mL', 'lab_e_coli_CFU_per_100mL']
    if all(col in top10_gov.columns for col in display_cols):
        print(top10_gov[display_cols].to_string(index=False, float_format='%.1f'))
    else:
        print(f"Missing columns for display. Available: {list(top10_gov.columns)}")
    print()
    
    print("=== TOP 10 HIGHEST CONCENTRATIONS (Private) ===")
    top10_priv = private_data.nlargest(10, 'concentration_CFU_per_100mL')
    priv_display_cols = ['borehole_id', 'Q_L_per_day', 'concentration_CFU_per_100mL']
    if all(col in top10_priv.columns for col in priv_display_cols):
        print(top10_priv[priv_display_cols].to_string(index=False, float_format='%.1f'))
    else:
        print(f"Missing columns for display. Available: {list(top10_priv.columns)}")
    print()
    
    # === CALIBRATION ANALYSIS ===
    print("=== CALIBRATION METRICS ===")
    
    # === Choose laboratory column ===
    # Prefer lab column used during calibration (from calibration_mapping.json),
    # fall back to lab_e_coli if present.
    lab_pref = None
    try:
        with open(os.path.join('data','output','calibration_mapping.json'), 'r', encoding='utf-8') as fh:
            lab_pref = json.load(fh).get('lab_column_used')
    except Exception:
        lab_pref = None
    lab_col = lab_pref if (lab_pref in gov_data.columns) else (
        'lab_e_coli_CFU_per_100mL' if 'lab_e_coli_CFU_per_100mL' in gov_data.columns else None
    )

    if lab_col is not None:
        # Process lab data
        gov_data['lab_ecoli_numeric'] = pd.to_numeric(gov_data[lab_col], errors='coerce')
        
        # All data with lab measurements (including non-detects as 0.1)
        has_lab = gov_data[gov_data['lab_ecoli_numeric'].notna()].copy()
        has_lab['lab_floor'] = has_lab['lab_ecoli_numeric'].apply(lambda x: max(x, 0.1))
        
        if len(has_lab) > 0:
            print(f"Total boreholes with lab data: {len(has_lab)}")
            print(f"Non-detects (lab = 0): {(has_lab['lab_ecoli_numeric'] == 0).sum()}")
            print(f"Positive detections: {(has_lab['lab_ecoli_numeric'] > 0).sum()}")
            
            # Calculate log differences  
            has_lab['model_log'] = np.log10(has_lab['concentration_CFU_per_100mL'] + 1)
            has_lab['lab_log'] = np.log10(has_lab['lab_floor'])
            has_lab['log_diff'] = has_lab['model_log'] - has_lab['lab_log'] 
            has_lab['abs_log_diff'] = np.abs(has_lab['log_diff'])
            
            print("\nTop 10 Largest Absolute Log10 Differences:")
            cols_present = [c for c in ['borehole_id', 'concentration_CFU_per_100mL', lab_col, 'abs_log_diff'] if c in has_lab.columns]
            top_diff = has_lab.nlargest(10, 'abs_log_diff')[cols_present]
            print(top_diff.to_string(index=False, float_format='%.3f'))
            
            # Metrics for all data (with floor)
            all_metrics = calculate_metrics(
                has_lab['concentration_CFU_per_100mL'].values,
                has_lab['lab_floor'].values  
            )
            
            print(f"\nAll Lab Data (n={all_metrics.get('n', 0)}):")
            if all_metrics:
                print(f"  RMSE (log-space): {_fmt_float(all_metrics.get('rmse_log'))}")
                print(f"  Spearman ρ: {_fmt_float(all_metrics.get('spearman_rho'))}")
                print(f"  Kendall τ: {_fmt_float(all_metrics.get('kendall_tau'))}")
                print(f"  Pearson r (log): {_fmt_float(all_metrics.get('pearson_log'))}")
            
            # Metrics for positive detections only
            positives = has_lab[has_lab['lab_ecoli_numeric'] > 0]
            if len(positives) >= 2:
                pos_metrics = calculate_metrics(
                    positives['concentration_CFU_per_100mL'].values,
                    positives['lab_ecoli_numeric'].values
                )
                print(f"\nPositive Detections Only (n={pos_metrics.get('n', 0)}):")
                if pos_metrics:
                    print(f"  RMSE (log-space): {_fmt_float(pos_metrics.get('rmse_log'))}")
                    print(f"  Spearman ρ: {_fmt_float(pos_metrics.get('spearman_rho'))}")
                    print(f"  Kendall τ: {_fmt_float(pos_metrics.get('kendall_tau'))}")
                    print(f"  Pearson r (log): {_fmt_float(pos_metrics.get('pearson_log'))}")
        else:
            print("No laboratory data available for calibration.")
    else:
        print("No recognized lab column found in government borehole data.")

    print()
    
    # === SUMMARY STATISTICS TABLE ===
    print("=== SUMMARY TABLE ===")
    try:
        efio_val = params.get('EFIO_override')
        efio_str = f"{float(efio_val):.0e}" if efio_val is not None else 'N/A'
    except Exception:
        efio_str = 'N/A'
    summary_data = [
        ["Total Sanitation Facilities", "279,934", "Island-wide survey"],
        ["Private Boreholes", f"{len(private_data):,}", "Residential water points"],
        ["Government Boreholes", f"{len(gov_data)}", "Regulated water points"],
        ["Laboratory Validation Points", f"{len(has_lab) if 'has_lab' in locals() else 'N/A'}", "Lab measurements"],
        ["Scenario", scenario_data['scenario_name'], "Parameter set used"],
        ["EFIO (CFU/person/day)", efio_str, "Pathogen shedding rate"],
        ["Decay coefficient (m⁻¹)", f"{params.get('ks_per_m', 'N/A')}", "Distance decay parameter"],
        ["Private radius (m)", f"{params.get('radius_by_type', {}).get('private', 'N/A')}", "Influence distance"],
        ["Government radius (m)", f"{params.get('radius_by_type', {}).get('government', 'N/A')}", "Influence distance"]
    ]
    
    print("Parameter | Value | Description")
    print("----------|-------|------------")
    for row in summary_data:
        print(f"{row[0]:<30} | {row[1]:<12} | {row[2]}")
    
    print("\n=== ANALYSIS COMPLETE ===")

if __name__ == "__main__":
    main()