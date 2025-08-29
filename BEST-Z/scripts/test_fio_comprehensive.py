#!/usr/bin/env python3
"""Comprehensive FIO Model Tests - Edge Cases and Integration.

This test suite covers edge cases, error handling, and integration scenarios
to ensure the FIO layered model is robust for production use.
"""

import sys
import os
from pathlib import Path
import tempfile
import pandas as pd

# Setup paths for imports
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir.parent))
sys.path.insert(0, str(scripts_dir))

# Import modules
import config
import fio_core
import fio_pipeline


def test_edge_cases():
    """Test edge cases and error handling."""
    print("=== Testing Edge Cases ===")
    
    # Test invalid inputs to core functions
    try:
        fio_core.compute_source_load(-1, 1e9, 0.5)  # Negative population
        assert False, "Should have raised ValueError"
    except ValueError:
        print("✓ Negative population properly rejected")
    
    try:
        fio_core.compute_concentration(1e11, 0)  # Zero flow
        assert False, "Should have raised ValueError"  
    except ValueError:
        print("✓ Zero flow properly rejected")
    
    # Test eta clamping
    L1 = fio_core.compute_source_load(100, 1e9, 1.5)  # eta > 1
    L2 = fio_core.compute_source_load(100, 1e9, 1.0)  # eta = 1
    assert L1 == L2 == 0, "eta > 1 should be clamped to 1"
    print("✓ eta clamping works correctly")
    
    # Test LRV edge cases
    eta_neg = fio_core.eta_from_lrv(-0.5)  # Negative LRV
    assert 0 <= eta_neg <= 1, "Negative LRV should be clamped"
    print(f"✓ Negative LRV handling: LRV=-0.5 → η={eta_neg:.3f}")
    
    # Test T90 edge cases
    try:
        fio_core.k_from_T90(0)  # Zero T90
        assert False, "Should have raised ValueError"
    except ValueError:
        print("✓ Zero T90 properly rejected")
    
    print("✓ Edge cases test PASSED")
    return True


def test_unit_conversions():
    """Test unit conversion edge cases."""
    print("\n=== Testing Unit Conversions ===")
    
    # Flow conversions
    assert fio_core.flow_m3s_to_Lday(0) == 0
    assert fio_core.flow_m3s_to_Lday(1) == 86_400_000
    
    # Concentration conversions 
    assert fio_core.concentration_to_100mL(0) == 0
    assert fio_core.concentration_to_100mL(1000) == 100
    
    # Test large numbers
    large_flow = fio_core.flow_m3s_to_Lday(1000)  # 1000 m³/s
    assert large_flow == 86_400_000_000  # 86.4 billion L/day
    
    print("✓ Unit conversions test PASSED")
    return True


def test_decay_scenarios():
    """Test different decay scenarios."""
    print("\n=== Testing Decay Scenarios ===")
    
    L = 1e11
    k = 0.7
    k_s = 0.01
    
    # Test time decay only
    L_time, method = fio_core.choose_decay(L, 1.0, k, None, k_s)
    assert method == "time"
    expected_time = fio_core.apply_decay_time(L, k, 1.0)
    assert abs(L_time - expected_time) < 1e6
    print(f"✓ Time decay: {L:.2e} → {L_time:.2e} CFU/day")
    
    # Test distance decay only
    L_dist, method = fio_core.choose_decay(L, None, k, 100.0, k_s)
    assert method == "distance"
    expected_dist = fio_core.apply_decay_distance(L, k_s, 100.0)
    assert abs(L_dist - expected_dist) < 1e6
    print(f"✓ Distance decay: {L:.2e} → {L_dist:.2e} CFU/day")
    
    # Test no decay
    L_none, method = fio_core.choose_decay(L, None, k, None, k_s)
    assert method == "none"
    assert L_none == L
    print(f"✓ No decay: {L:.2e} → {L_none:.2e} CFU/day")
    
    # Test time preference over distance
    L_pref, method = fio_core.choose_decay(L, 1.0, k, 100.0, k_s)
    assert method == "time"
    print("✓ Time decay preferred over distance when both available")
    
    print("✓ Decay scenarios test PASSED")
    return True


def test_missing_data_handling():
    """Test handling of missing/incomplete data."""
    print("\n=== Testing Missing Data Handling ===")
    
    # Create households with missing data
    households = pd.DataFrame({
        'household_id': ['H1', 'H2', 'H3'],
        'pop': [None, 20, 30],  # Missing pop for H1
        'efio': [1e9, None, 1e8],  # Missing efio for H2
        'eta': [0.5, 0.8, None],  # Missing eta for H3
    })
    
    # Test with defaults
    defaults = config.FIO_LAYERED_DEFAULTS.copy()
    
    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        households.to_csv(f.name, index=False)
        temp_path = Path(f.name)
    
    try:
        # Load with missing data handling
        loaded = fio_pipeline.load_households_csv(temp_path, defaults)
        
        # Check that missing values were filled
        assert not loaded['pop'].isna().any(), "All pop values should be filled"
        assert not loaded['efio'].isna().any(), "All efio values should be filled" 
        assert not loaded['eta'].isna().any(), "All eta values should be filled"
        
        # Check specific values
        assert loaded.loc[0, 'pop'] == defaults['pop_per_household']  # H1 missing pop
        assert loaded.loc[1, 'efio'] == defaults['efio']  # H2 missing efio
        assert loaded.loc[2, 'eta'] == defaults['eta']  # H3 missing eta
        
        print("✓ Missing data properly filled with defaults")
        
    finally:
        # Clean up
        temp_path.unlink()
    
    print("✓ Missing data handling test PASSED")
    return True


def test_mapping_strategies():
    """Test different mapping strategies."""
    print("\n=== Testing Mapping Strategies ===")
    
    households = pd.DataFrame({
        'household_id': ['H1', 'H2', 'H3'],
        'lat': [-6.1, -6.2, None],
        'lon': [39.1, 39.2, None]
    })
    
    receptors = pd.DataFrame({
        'receptor_id': ['R1', 'R2'],
        'lat': [-6.15, -6.25],
        'lon': [39.15, 39.25],
        'Q': [1e7, 2e7]
    })
    
    defaults = config.FIO_LAYERED_DEFAULTS.copy()
    
    # Test single mode (default)
    config.FIO_MAPPING_CONFIG['mode'] = 'single'
    mapping_single = fio_pipeline.load_mapping_csv(None, households, receptors, defaults)
    assert len(mapping_single) == 3
    assert mapping_single['receptor_id'].nunique() == 1  # All to same receptor
    print("✓ Single mapping strategy works")
    
    # Test round-robin mode
    config.FIO_MAPPING_CONFIG['mode'] = 'round_robin'
    mapping_rr = fio_pipeline.load_mapping_csv(None, households, receptors, defaults)
    assert len(mapping_rr) == 3
    assert mapping_rr['receptor_id'].nunique() == 2  # Distributed across receptors
    print("✓ Round-robin mapping strategy works")
    
    # Test nearest mode (with partial coordinates)
    config.FIO_MAPPING_CONFIG['mode'] = 'nearest'
    mapping_nearest = fio_pipeline.load_mapping_csv(None, households, receptors, defaults)
    assert len(mapping_nearest) == 3
    # H1 and H2 should have distance, H3 should not (no coordinates)
    has_distance = mapping_nearest['d'].notna().sum()
    assert has_distance >= 2, "At least 2 households should have distance calculated"
    print("✓ Nearest mapping strategy works")
    
    # Reset to default
    config.FIO_MAPPING_CONFIG['mode'] = 'single'
    
    print("✓ Mapping strategies test PASSED")
    return True


def test_pipeline_integration():
    """Test end-to-end pipeline with realistic data."""
    print("\n=== Testing Pipeline Integration ===")
    
    # Create realistic test scenario
    households = pd.DataFrame({
        'household_id': [f'H{i}' for i in range(1, 11)],  # 10 households
        'pop': [8, 12, 6, 15, 10, 9, 11, 7, 13, 14],  # Varied population
        'efio': [1e9] * 10,  # Standard EFIO
        'eta': [0.2, 0.4, 0.6, 0.8, 0.9, 0.1, 0.3, 0.5, 0.7, 0.95]  # Varied removal
    })
    
    receptors = pd.DataFrame({
        'receptor_id': ['well_1', 'well_2'],
        'Q': [5e6, 8e6]  # Different flow rates
    })
    
    mapping = pd.DataFrame({
        'household_id': households['household_id'],
        'receptor_id': ['well_1'] * 5 + ['well_2'] * 5,  # Split between wells
        't': [0.5, 1.0, 1.5, 2.0, 0.8, 1.2, 0.9, 1.1, 1.6, 0.7]  # Varied travel times
    })
    
    defaults = config.FIO_LAYERED_DEFAULTS.copy()
    
    # Run pipeline
    concentrations, contributions = fio_pipeline.compute_fio_layered(
        households, receptors, mapping, defaults
    )
    
    # Validate results
    assert len(concentrations) == 2, "Should have 2 receptor results"
    assert len(contributions) == 10, "Should have 10 household contributions"
    
    # Check that concentrations are reasonable
    assert all(concentrations['C'] > 0), "All concentrations should be positive"
    assert all(concentrations['total_households'] > 0), "All should have households"
    
    # Check mass balance
    total_source = contributions['L'].sum()
    total_reaching = contributions['L_reaching'].sum()
    assert total_reaching <= total_source, "Reaching load should not exceed source"
    
    # Test output unit conversion
    defaults['output_unit'] = 'CFU_100mL'
    concentrations_100ml, _ = fio_pipeline.compute_fio_layered(
        households, receptors, mapping, defaults
    )
    
    # 100mL concentrations should be 10% of L concentrations
    ratio = concentrations_100ml['C'].iloc[0] / concentrations['C'].iloc[0]
    assert abs(ratio - 0.1) < 0.001, "CFU/100mL should be 10% of CFU/L"
    
    print(f"✓ Processed {len(households)} households → {len(receptors)} receptors")
    print(f"✓ Total source load: {total_source:.2e} CFU/day")
    print(f"✓ Total reaching: {total_reaching:.2e} CFU/day")
    print(f"✓ Efficiency: {100*(1-total_reaching/total_source):.1f}% reduction")
    
    print("✓ Pipeline integration test PASSED")
    return True


def main():
    """Run all comprehensive tests."""
    print("Comprehensive FIO Model Tests")
    print("=" * 50)
    
    try:
        test_edge_cases()
        test_unit_conversions()
        test_decay_scenarios()
        test_missing_data_handling()
        test_mapping_strategies()
        test_pipeline_integration()
        
        print("\n" + "=" * 50)
        print("🎉 ALL COMPREHENSIVE TESTS PASSED!")
        print("The FIO layered model is robust and ready for production use.")
        return True
        
    except Exception as e:
        print(f"\n❌ COMPREHENSIVE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)