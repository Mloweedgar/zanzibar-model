"""Risk tier classification thresholds and utilities.

Defines WHO-based risk tiers for both observed data and calibrated
thresholds for model predictions that account for systematic overestimation.
"""

import numpy as np
from typing import Dict, Tuple

# === OBSERVED DATA THRESHOLDS ===
# Based on WHO drinking water guidelines for Total Coliforms
# Reference: WHO Guidelines for Drinking-water Quality (4th ed.)

RISK_TIERS_OBSERVED = {
    'Low': {
        'range': (0, 10),
        'label': 'Safe',
        'description': 'Acceptable for consumption (with chlorination)',
        'color': [0, 200, 0, 200],  # Green
        'action': 'Routine monitoring'
    },
    'Medium': {
        'range': (10, 50),
        'label': 'Treatment Recommended',
        'description': 'Contamination detected, treatment advised',
        'color': [255, 165, 0, 200],  # Orange
        'action': 'Enhanced monitoring, consider point-of-use treatment'
    },
    'High': {
        'range': (50, np.inf),
        'label': 'Unsafe',
        'description': 'High contamination, immediate action required',
        'color': [255, 0, 0, 200],  # Red
        'action': 'Boil water advisory, find alternative source, upgrade sanitation'
    }
}

# === MODEL PREDICTION THRESHOLDS (CALIBRATED) ===
# Adjusted for systematic 3.3× overestimation
# 
# Background:
# - After unit fix: median predicted = 81 CFU/100mL
# - Observed median = 24.5 CFU/100mL
# - Overestimation factor = 81 / 24.5 ≈ 3.3×
#
# Implication:
# - Model prediction of 33 CFU/100mL ≈ actual 10 CFU/100mL (Low/Med boundary)
# - Model prediction of 165 CFU/100mL ≈ actual 50 CFU/100mL (Med/High boundary)

CALIBRATION_FACTOR = 3.3

RISK_TIERS_PREDICTED = {
    'Low': {
        'range': (0, 33),  # 10 × 3.3
        'label': 'Low Risk (Model)',
        'description': 'Model predicts <33 → likely <10 actual',
        'color': [0, 200, 0, 200],
        'action': 'Continue routine monitoring'
    },
    'Medium': {
        'range': (33, 165),  # 10×3.3 to 50×3.3
        'label': 'Medium Risk (Model)',
        'description': 'Model predicts 33-165 → likely 10-50 actual',
        'color': [255, 165, 0, 200],
        'action': 'Priority for field sampling and confirmation'
    },
    'High': {
        'range': (165, np.inf),  # 50 × 3.3
        'label': 'High Risk (Model)',
        'description': 'Model predicts >165 → likely >50 actual',
        'color': [255, 0, 0, 200],
        'action': 'Urgent: field validation, immediate intervention planning'
    }
}


def get_risk_tier(concentration: float, is_predicted: bool = False) -> str:
    """
    Classify a concentration value into Low/Medium/High risk tier.
    
    Args:
        concentration: FIO concentration in CFU/100mL
        is_predicted: If True, use calibrated thresholds for model predictions
                     If False, use standard thresholds for observed data
    
    Returns:
        Risk tier label: 'Low', 'Medium', or 'High'
    """
    tiers = RISK_TIERS_PREDICTED if is_predicted else RISK_TIERS_OBSERVED
    
    for tier_name, tier_info in tiers.items():
        low, high = tier_info['range']
        if low <= concentration < high:
            return tier_name
    
    return 'High'  # Default to High if above all thresholds


def get_risk_color(concentration: float, is_predicted: bool = False) -> list:
    """
    Get RGBA color for a concentration value based on risk tier.
    
    Args:
        concentration: FIO concentration in CFU/100mL
        is_predicted: If True, use calibrated thresholds
        
    Returns:
        List [R, G, B, A] for visualization
    """
    tier = get_risk_tier(concentration, is_predicted)
    tiers = RISK_TIERS_PREDICTED if is_predicted else RISK_TIERS_OBSERVED
    return tiers[tier]['color']


def get_tier_bins(is_predicted: bool = False) -> Tuple[list, list]:
    """
    Get bin edges and labels for pd.cut() tier classification.
    
    Args:
        is_predicted: If True, use calibrated thresholds
        
    Returns:
        Tuple of (bins, labels) for pd.cut()
    """
    tiers = RISK_TIERS_PREDICTED if is_predicted else RISK_TIERS_OBSERVED
    
    # Extract boundaries in order: Low, Medium, High
    bins = [0, 
            tiers['Low']['range'][1],
            tiers['Medium']['range'][1],
            np.inf]
    labels = ['Low', 'Medium', 'High']
    
    return bins, labels


# Summary for documentation
CALIBRATION_SUMMARY = f"""
Risk Tier Classification Thresholds

OBSERVED DATA (Ground Truth):
  Low Risk:    0-10 CFU/100mL
  Medium Risk: 10-50 CFU/100mL
  High Risk:   >50 CFU/100mL

MODEL PREDICTIONS (Calibrated for {CALIBRATION_FACTOR}× overestimation):
  Low Risk:    0-33 CFU/100mL   (corresponds to 0-10 actual)
  Medium Risk: 33-165 CFU/100mL (corresponds to 10-50 actual)
  High Risk:   >165 CFU/100mL   (corresponds to >50 actual)

USAGE:
  - For field measurements: use observed thresholds
  - For model predictions: use calibrated (predicted) thresholds
  - This accounts for systematic model overestimation after unit fix
  
VALIDATION:
  - Median observed: 24.5 CFU/100mL
  - Median predicted: 80.9 CFU/100mL
  - Calibration factor: 80.9 / 24.5 = {CALIBRATION_FACTOR}
"""


if __name__ == '__main__':
    print(CALIBRATION_SUMMARY)
    
    # Test classifications
    test_values = [5, 25, 75, 40, 120, 200]
    print("\nExample Classifications:")
    print("-" * 60)
    for val in test_values:
        obs_tier = get_risk_tier(val, is_predicted=False)
        pred_tier = get_risk_tier(val, is_predicted=True)
        print(f"{val:6.1f} CFU/100mL → Observed: {obs_tier:6s} | Predicted: {pred_tier:6s}")
