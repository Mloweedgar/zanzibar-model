"""Core Engine for Zanzibar Pathogen & Nitrogen Model.

Handles:
1. Data Loading & Standardization
2. Intervention Application (Scenario Logic)
3. Layer 1: Load Calculation (Polymorphic: FIO vs Nitrogen)
4. Layer 2: Transport (Vectorized BallTree)
5. Layer 3: Concentration (Dilution)
"""

import logging
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, Optional, Literal
from sklearn.neighbors import BallTree

from . import config

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class PollutantConfig:
    """Configuration for a specific pollutant type."""
    name: Literal['fio', 'nitrogen', 'phosphorus']
    output_load_path: Path
    output_conc_path: Optional[Path] = None
    
    # FIO specific
    efio: float = 0.0
    decay_rate: float = 0.0
    
    # Nitrogen specific
    protein_per_capita: float = 0.0
    protein_conversion: float = 0.0
    
    # Phosphorus specific (detergent-based)
    phosphorus_detergent_consumption_g: float = 0.0
    phosphorus_fraction: float = 0.0

def _get_pollutant_config(model_type: str, scenario: Dict[str, Any]) -> PollutantConfig:
    if model_type == 'fio':
        return PollutantConfig(
            name='fio',
            output_load_path=config.FIO_LOAD_PATH,
            output_conc_path=config.FIO_CONCENTRATION_PATH,
            efio=scenario.get('EFIO_override', config.EFIO_DEFAULT),
            decay_rate=scenario.get('ks_per_m', config.KS_PER_M_DEFAULT)
        )
    elif model_type == 'nitrogen':
        return PollutantConfig(
            name='nitrogen',
            output_load_path=config.NET_NITROGEN_LOAD_PATH,
            protein_per_capita=scenario.get('protein_per_capita_override', config.PROTEIN_PER_CAPITA_DEFAULT),
            protein_conversion=scenario.get('protein_to_nitrogen_conversion_override', config.PROTEIN_TO_NITROGEN_CONVERSION)
        )
    elif model_type == 'phosphorus':
        return PollutantConfig(
            name='phosphorus',
            output_load_path=config.NET_PHOSPHORUS_LOAD_PATH,
            phosphorus_detergent_consumption_g=scenario.get(
                'phosphorus_detergent_consumption_override',
                config.PHOSPHORUS_DETERGENT_CONSUMPTION_G_PER_CAPITA
            ),
            phosphorus_fraction=scenario.get(
                'phosphorus_detergent_fraction_override',
                config.PHOSPHORUS_DETERGENT_PHOSPHORUS_FRACTION
            )
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")

# --- Step 1: Standardization & Interventions ---

def load_and_standardize_sanitation() -> pd.DataFrame:
    """Load raw sanitation data and standardize columns."""
    if config.SANITATION_STANDARDIZED_PATH.exists():
        logging.info(f"Loading standardized sanitation from {config.SANITATION_STANDARDIZED_PATH}")
        return pd.read_csv(config.SANITATION_STANDARDIZED_PATH)

    logging.info(f"Standardizing raw data from {config.SANITATION_RAW_PATH}")
    df = pd.read_csv(config.SANITATION_RAW_PATH)
    
    # Rename columns
    df = df.rename(columns={k: v for k, v in config.SANITATION_COLUMN_MAPPING.items() if k in df.columns})
    
    # Ensure required columns
    required = ['id', 'lat', 'long', 'toilet_category_id']
    if not all(c in df.columns for c in required):
        raise ValueError(f"Missing columns. Found: {df.columns}, Required: {required}")

    # Clean types
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['long'] = pd.to_numeric(df['long'], errors='coerce')
    df = df.dropna(subset=['lat', 'long'])
    
    # Defaults
    df['household_population'] = df.get('household_population', config.HOUSEHOLD_POPULATION_DEFAULT)
    df['pathogen_containment_efficiency'] = df['toilet_category_id'].map(config.CONTAINMENT_EFFICIENCY_DEFAULT).fillna(0.0)
    
    # Save
    config.SANITATION_STANDARDIZED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.SANITATION_STANDARDIZED_PATH, index=False)
    return df

def apply_interventions(df: pd.DataFrame, scenario: Dict[str, Any]) -> pd.DataFrame:
    """Apply scenario interventions (population growth, toilet upgrades)."""
    df = df.copy()
    
    # 1. Population Growth
    pop_factor = scenario.get('pop_factor', 1.0)
    df['household_population'] *= pop_factor
    
    # 2. Efficiency Overrides
    eff_map = config.CONTAINMENT_EFFICIENCY_DEFAULT.copy()
    if 'efficiency_override' in scenario:
        eff_map.update({int(k): float(v) for k, v in scenario['efficiency_override'].items()})
    
    # Helper to split rows (preserve mass)
    def convert_fraction(mask, fraction, new_cat_id, new_eff):
        if not mask.any() or fraction <= 0:
            return
        
        # Rows to convert
        converted = df[mask].copy()
        converted['household_population'] *= fraction
        converted['toilet_category_id'] = new_cat_id
        converted['pathogen_containment_efficiency'] = new_eff
        
        # Reduce pop in original rows
        df.loc[mask, 'household_population'] *= (1 - fraction)
        
        # Append converted
        return converted

    new_rows = []
    
    # OD Reduction -> Septic
    od_red = scenario.get('od_reduction_percent', 0.0) / 100.0
    if od_red > 0:
        res = convert_fraction(df['toilet_category_id'] == 4, od_red, 3, eff_map[3])
        if res is not None: new_rows.append(res)

    # Pit Upgrade -> Septic (Well-managed: 80% efficiency)
    pit_up = scenario.get('infrastructure_upgrade_percent', 0.0) / 100.0
    if pit_up > 0:
        # Report says "upgrading... to a well-managed septic system (80% containment)"
        res = convert_fraction(df['toilet_category_id'] == 2, pit_up, 3, 0.80)
        if res is not None: new_rows.append(res)

    # Fecal Sludge Treatment (Septic -> Better Septic/Sewer eff)
    fst = scenario.get('fecal_sludge_treatment_percent', 0.0) / 100.0
    if fst > 0:
        # Upgrade existing poor septics (0.50) to well-managed (0.80)
        res = convert_fraction(df['toilet_category_id'] == 3, fst, 3, 0.80)
        if res is not None: new_rows.append(res)

    if new_rows:
        df = pd.concat([df] + new_rows, ignore_index=True)

    # --- Spatial Interventions (New for Scenarios) ---
    
    # Scenario 1: Targeted Protection (Top 5% Risk)
    if scenario.get('targeted_protection_enabled'):
        # Load Baseline Risk if available
        baseline_path = config.FIO_CONCENTRATION_PATH
        if baseline_path.exists():
            logging.info("Loading Baseline Risk for Targeted Protection...")
            bdf = pd.read_csv(baseline_path)
            if 'risk_score' in bdf.columns:
                # Top 5% Risk
                threshold = bdf['risk_score'].quantile(0.95)
                high_risk_bh = bdf[bdf['risk_score'] >= threshold]
                logging.info(f"Identified {len(high_risk_bh)} High-Risk Boreholes (Score > {threshold:.1f})")
                
                # Find toilets within 50m of these boreholes
                from sklearn.neighbors import BallTree
                
                # Build Tree of Toilets
                df_rad = np.deg2rad(df[['lat', 'long']].values)
                bh_rad = np.deg2rad(high_risk_bh[['lat', 'long']].values)
                
                tree = BallTree(df_rad, metric='haversine')
                
                # Query radius (35m) - Matches Report Scenario 1
                radius_rad = 35.0 / config.EARTH_RADIUS_M
                indices = tree.query_radius(bh_rad, r=radius_rad)
                
                # Flatten indices
                toilet_indices = np.unique(np.concatenate(indices))
                
                # Upgrade these toilets to Septic (3) with high efficiency (Well-managed)
                if len(toilet_indices) > 0:
                    logging.info(f"Upgrading {len(toilet_indices)} toilets near high-risk boreholes.")
                    df.loc[toilet_indices, 'toilet_category_id'] = 3
                    df.loc[toilet_indices, 'pathogen_containment_efficiency'] = 0.80 # Well-managed Septic (Report Scenario 2 target)
            else:
                logging.warning("Baseline file missing 'risk_score'. Skipping Targeted Protection.")
        else:
            logging.warning("Baseline results not found. Run 'baseline_2025' first.")

    # Scenario 3: Stone Town Sewer
    if scenario.get('stone_town_sewer_enabled'):
        # Stone Town Bounding Box (Approx)
        # Lat: -6.166 to -6.155, Long: 39.185 to 39.195
        mask = (
            (df['lat'] >= -6.170) & (df['lat'] <= -6.150) &
            (df['long'] >= 39.180) & (df['long'] <= 39.200)
        )
        count = mask.sum()
        if count > 0:
            # Get treatment efficiency from scenario (default 0.90)
            treatment_eff = scenario.get('treatment_efficiency', 0.90)
            logging.info(f"Sewering Stone Town: Upgrading {count} toilets to Sewer (Efficiency: {treatment_eff:.0%}).")
            df.loc[mask, 'toilet_category_id'] = 1
            df.loc[mask, 'pathogen_containment_efficiency'] = treatment_eff

    # Centralized Treatment (Sewer efficiency boost globally)
    if scenario.get('centralized_treatment_enabled'):
        treatment_eff = scenario.get('treatment_efficiency', 0.90)
        df.loc[df['toilet_category_id'] == 1, 'pathogen_containment_efficiency'] = treatment_eff
        logging.info(f"Applied centralized treatment efficiency: {treatment_eff:.0%}")

    return df[df['household_population'] > 0].reset_index(drop=True)

# --- Step 2: Layer 1 Calculation ---

def compute_load(df: pd.DataFrame, pcfg: PollutantConfig, save_output: bool = True) -> pd.DataFrame:
    """Compute initial pollutant load per household."""
    df = df.copy()
    leakage = 1.0 - df['pathogen_containment_efficiency']
    
    if pcfg.name == 'fio':
        # Load = Pop * EFIO * Leakage
        df['load'] = df['household_population'] * pcfg.efio * leakage
    elif pcfg.name == 'nitrogen':
        # Nitrogen = Pop * Protein * Conversion * Leakage * 365
        df['load'] = (df['household_population'] * 
                      pcfg.protein_per_capita * 
                      pcfg.protein_conversion * 
                      leakage * 365)
    else:
        # Phosphorus = Pop * Detergent Use (g/day) * 365 * P fraction * Leakage, converted to kg/yr
        df['load'] = (df['household_population'] *
                      pcfg.phosphorus_detergent_consumption_g *
                      365 *
                      pcfg.phosphorus_fraction *
                      leakage) / 1000.0
    
    if pcfg.name == 'nitrogen':
        df = df.rename(columns={'load': 'nitrogen_load'})
    elif pcfg.name == 'phosphorus':
        df = df.rename(columns={'load': 'phosphorus_load'})
    
    # Save intermediate (optional, skip during grid-search calibration to avoid I/O cost)
    if save_output:
        # TODO: drop columns that are not needed for the next step
        df.to_csv(pcfg.output_load_path, index=False)
        logging.info(f"Saved Layer 1 load to {pcfg.output_load_path}")
    return df

# --- Step 3: Layer 2 Transport (Vectorized) ---

def run_transport(toilets: pd.DataFrame, boreholes: pd.DataFrame, pcfg: PollutantConfig, radius_m: float) -> pd.DataFrame:
    """Link toilets to boreholes and compute decayed load using Vectorized BallTree."""
    if pcfg.name != 'fio':
        logging.info("Skipping transport layer for non-FIO model (not required).")
        return pd.DataFrame()

    logging.info(f"Running Transport Layer (Radius: {radius_m}m, Decay: {pcfg.decay_rate})")
    
    # Convert to radians for BallTree
    t_rad = np.radians(toilets[['lat', 'long']].values)
    b_rad = np.radians(boreholes[['lat', 'long']].values)
    
    tree = BallTree(t_rad, metric='haversine')
    
    # Query all boreholes at once (or in chunks if memory is tight, but 20k is fine)
    # query_radius returns array of arrays of indices
    radius_rad = radius_m / config.EARTH_RADIUS_M
    indices, distances = tree.query_radius(b_rad, r=radius_rad, return_distance=True)
    
    # Vectorized accumulation
    total_loads = np.zeros(len(boreholes))
    
    # Flatten for processing (this is still somewhat iterative but much faster than pure python loops)
    # For true vectorization with variable length neighbors, we can use sparse matrices or simple iteration over the result arrays
    # Given the density, simple iteration over the `indices` array (which is length N_boreholes) is fast enough in Python
    # because the inner loop is avoided.
    
    toilet_loads = toilets['load'].values
    
    for i, (t_indices, t_dists) in enumerate(zip(indices, distances)):
        if len(t_indices) == 0:
            continue
            
        dists_m = t_dists * config.EARTH_RADIUS_M
        decay_factors = np.exp(-pcfg.decay_rate * dists_m)
        
        # Sum of (Load * Decay)
        total_loads[i] = np.sum(toilet_loads[t_indices] * decay_factors)
        
    boreholes = boreholes.copy()
    boreholes['aggregated_load'] = total_loads
    return boreholes

# --- Step 4: Layer 3 Concentration ---

def compute_concentration(boreholes: pd.DataFrame, flow_multiplier: float = 1.0) -> pd.DataFrame:
    """Convert aggregated load to concentration."""
    # Conc = Load / Flow, converted to CFU/100mL
    # Load is in CFU/day, Q is in L/day
    # Load/Q gives CFU/L
    # To convert CFU/L to CFU/100mL: divide by 10 (since 1L = 10×100mL)
    if 'Q_L_per_day' not in boreholes.columns:
        # Default to 20,000 L/day for government boreholes (realistic for community supply)
        # This balances the high EFIO (1e9) to produce realistic concentration magnitudes.
        logging.warning("Q_L_per_day missing, using default 20,000L")
        boreholes['Q_L_per_day'] = 20000.0
        
    # Allow scenario-level flow scaling (e.g., when measured/assumed pumping rates are uncertain)
    boreholes['concentration_CFU_per_100mL'] = (
        boreholes['aggregated_load'] /
        (boreholes['Q_L_per_day'] * max(flow_multiplier, 1e-6))
    ) / 10.0

    # Calculate Risk Score (0-100)
    # Log-transform: 0 -> 0, 1 -> 20, 100 -> 60, 10000 -> 100
    # Formula: 20 * log10(conc + 1), capped at 100
    boreholes['risk_score'] = 20 * np.log10(boreholes['concentration_CFU_per_100mL'] + 1)
    boreholes['risk_score'] = boreholes['risk_score'].clip(0, 100)
    return boreholes

# --- Main Pipeline ---

def run_pipeline(model_type: str, scenario_name: str = 'baseline_2025', scenario_override: Dict[str, Any] = None):
    base_scenario = config.SCENARIOS.get(scenario_name, config.SCENARIOS['baseline_2025'])
    
    # Merge override if provided
    if scenario_override:
        scenario = base_scenario.copy()
        scenario.update(scenario_override)
    else:
        scenario = base_scenario
        
    pcfg = _get_pollutant_config(model_type, scenario)
    
    logging.info(f"Starting {model_type.upper()} Pipeline | Scenario: {scenario_name}")
    
    # 1. Load & Intervene
    df = load_and_standardize_sanitation()
    df = apply_interventions(df, scenario)
    
    # 2. Layer 1
    df = compute_load(df, pcfg)
    
    if model_type != 'fio':
        logging.info(f"{model_type.capitalize()} pipeline complete.")
        return

    # 3. Layer 2 & 3 (FIO only)
    # Load boreholes (Private & Gov)
    # For simplicity, we process them together or separate. Let's do separate and concat.
    results = []
    flow_multipliers = scenario.get('flow_multiplier_by_type', {'private': 1.0, 'government': 1.0})
    for btype, path in [('private', config.PRIVATE_BOREHOLES_ENRICHED_PATH), 
                        ('government', config.GOVERNMENT_BOREHOLES_ENRICHED_PATH)]:
        if not path.exists():
            logging.warning(f"Borehole file {path} not found. Skipping {btype}.")
            continue
            
        bdf = pd.read_csv(path)
        radius = scenario['radius_by_type'].get(btype, 35.0)
        flow_multiplier = flow_multipliers.get(btype, 1.0)
        
        bdf_linked = run_transport(df, bdf, pcfg, radius)
        bdf_conc = compute_concentration(bdf_linked, flow_multiplier=flow_multiplier)
        bdf_conc['borehole_type'] = btype
        results.append(bdf_conc)
        
    if results:
        final_df = pd.concat(results, ignore_index=True)
        # TODO: drop columns that are not needed for the next step
        final_df.to_csv(pcfg.output_conc_path, index=False)
        logging.info(f"Saved FIO concentrations to {pcfg.output_conc_path}")
    else:
        logging.warning("No borehole results generated.")
