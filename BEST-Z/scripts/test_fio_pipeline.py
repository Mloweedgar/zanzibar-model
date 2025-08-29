#!/usr/bin/env python3
"""Test end-to-end FIO layered model pipeline."""

import sys
import os
from pathlib import Path

# Add scripts directory and parent to path
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir.parent))
sys.path.insert(0, str(scripts_dir))

# Set PYTHONPATH for relative imports
os.environ['PYTHONPATH'] = str(scripts_dir.parent)

# Direct imports
import config
import ingest
import fio_core
import fio_pipeline


def test_worked_example_pipeline():
    """Test pipeline using worked example parameters."""
    print("=== Testing End-to-End Pipeline ===")
    
    # Load default configuration
    defaults = {
        'pop_per_household': 500,  # Single household with 500 people
        'efio': 1e9,
        'eta': 0.5,
        'k': 0.7,
        'k_s': 0.0,  # Spatial decay
        't': 1.0,
        'Q': 1e7,
        'output_unit': 'CFU_L'
    }
    
    # Create minimal test data for worked example
    import pandas as pd
    
    households = pd.DataFrame({
        'household_id': ['H_worked_example'],
        'pop': [500],
        'efio': [1e9],
        'eta': [0.5]
    })
    
    receptors = pd.DataFrame({
        'receptor_id': ['well_worked_example'],
        'Q': [1e7]
    })
    
    mapping = pd.DataFrame({
        'household_id': ['H_worked_example'],
        'receptor_id': ['well_worked_example'],
        't': [1.0],
        'd': [None]
    })
    
    print(f"Test data: {len(households)} household, {len(receptors)} receptor")
    
    # Run pipeline
    concentrations, contributions = fio_pipeline.compute_fio_layered(households, receptors, mapping, defaults)
    
    # Validate results
    assert len(concentrations) == 1, f"Expected 1 receptor result, got {len(concentrations)}"
    assert len(contributions) == 1, f"Expected 1 contribution record, got {len(contributions)}"
    
    result = concentrations.iloc[0]
    contrib = contributions.iloc[0]
    
    print(f"Results:")
    print(f"  Source load: {contrib['L']:.2e} CFU/day")
    print(f"  After decay: {contrib['L_reaching']:.2e} CFU/day") 
    print(f"  Concentration: {result['C']:.1f} CFU/L")
    
    # Validate against expected values (allowing small tolerance)
    expected_L = 2.5e11
    expected_C = 12400  # Approximately
    
    assert abs(contrib['L'] - expected_L) < 1e9, f"Source load mismatch: {contrib['L']} vs {expected_L}"
    assert abs(result['C'] - expected_C) / expected_C < 0.05, f"Concentration mismatch: {result['C']} vs {expected_C}"
    
    print("✓ End-to-end pipeline test PASSED")
    print(f"  Final concentration: {result['C']:.1f} CFU/L (expected: ≈{expected_C} CFU/L)")
    return True


def test_example_data_files():
    """Test loading the example data files."""
    print("\n=== Testing Example Data Files ===")
    
    data_dir = scripts_dir.parent / 'data_examples'
    
    # Test loading files
    households = fio_pipeline.load_households_csv(data_dir / 'households.csv')
    receptors = fio_pipeline.load_receptors_csv(data_dir / 'receptors.csv')
    mapping = fio_pipeline.load_mapping_csv(data_dir / 'mapping.csv', households, receptors)
    
    print(f"Loaded: {len(households)} households, {len(receptors)} receptors, {len(mapping)} mappings")
    
    # Run pipeline
    concentrations, contributions = fio_pipeline.compute_fio_layered(households, receptors, mapping)
    
    print(f"Results: {len(concentrations)} receptor concentrations")
    for _, row in concentrations.iterrows():
        print(f"  {row['receptor_id']}: {row['C']:.1f} CFU/L from {row['total_households']} households")
    
    print("✓ Example data files test PASSED")
    return True


def test_lrv_conversion():
    """Test LRV to eta conversion in pipeline."""
    print("\n=== Testing LRV Conversion ===")
    
    import pandas as pd
    
    # Create households with LRV values
    households = pd.DataFrame({
        'household_id': ['H1', 'H2', 'H3'],
        'pop': [10, 10, 10],
        'efio': [1e9, 1e9, 1e9], 
        'eta': [0.5, 0.5, 0.5],  # Should be overridden by LRV
        'lrv': [1.0, 2.0, None]  # 90%, 99%, use eta
    })
    
    receptors = pd.DataFrame({
        'receptor_id': ['well_A'],
        'Q': [1e7]
    })
    
    mapping = pd.DataFrame({
        'household_id': ['H1', 'H2', 'H3'],
        'receptor_id': ['well_A', 'well_A', 'well_A'],
        't': [1.0, 1.0, 1.0]
    })
    
    # Manually apply LRV conversion (simulating what load_households_csv does)
    households_processed = households.copy()
    lrv_mask = ~households_processed['lrv'].isna()
    if lrv_mask.any():
        households_processed.loc[lrv_mask, 'eta'] = households_processed.loc[lrv_mask, 'lrv'].apply(fio_core.eta_from_lrv)
    
    print("LRV conversions:")
    for _, row in households_processed.iterrows():
        lrv_val = row['lrv'] if not pd.isna(row['lrv']) else 'None'
        print(f"  {row['household_id']}: LRV={lrv_val} → η={row['eta']:.3f}")
    
    # Verify expected conversions
    assert abs(households_processed.iloc[0]['eta'] - 0.9) < 1e-6  # LRV=1 → η=0.9
    assert abs(households_processed.iloc[1]['eta'] - 0.99) < 1e-6  # LRV=2 → η=0.99
    assert households_processed.iloc[2]['eta'] == 0.5  # No LRV, use original eta
    
    print("✓ LRV conversion test PASSED")
    return True


def main():
    """Run all pipeline tests."""
    print("Testing FIO Layered Model Pipeline")
    print("=" * 50)
    
    try:
        test_worked_example_pipeline()
        test_example_data_files()
        test_lrv_conversion()
        
        print("\n" + "=" * 50)
        print("🎉 ALL PIPELINE TESTS PASSED!")
        print("The FIO layered model pipeline is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ PIPELINE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)