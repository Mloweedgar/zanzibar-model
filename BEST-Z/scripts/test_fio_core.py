#!/usr/bin/env python3
"""Test script for FIO core functions - validates worked example from markdown.

This script tests the core mathematical functions against the worked example
provided in fio_modeling_markdown.md to ensure correctness.

Expected result: C ≈ 12,400 CFU/L
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from fio_core import (
    compute_source_load, apply_decay_time, compute_concentration,
    eta_from_lrv, k_from_T90, choose_decay, flow_m3s_to_Lday,
    concentration_to_100mL
)


def test_worked_example():
    """Test the worked example from fio_modeling_markdown.md."""
    print("=== FIO Core Functions Test - Worked Example ===")
    
    # Worked example parameters
    pop = 500
    efio = 1e9  # 1 billion CFU/person/day
    eta = 0.5   # 50% removal
    k = 0.7     # day⁻¹
    t = 1.0     # days
    Q = 1e7     # L/day
    
    print(f"Parameters: Pop={pop}, EFIO={efio:.0e}, η={eta}, k={k}, t={t}, Q={Q:.0e}")
    
    # Step 1: Net source load
    L = compute_source_load(pop, efio, eta)
    expected_L = 2.5e11
    print(f"Step 1 - Source load: L = {L:.2e} CFU/day (expected: {expected_L:.2e})")
    assert abs(L - expected_L) < 1e9, f"Source load mismatch: {L} vs {expected_L}"
    
    # Step 2: After decay
    L_t = apply_decay_time(L, k, t)
    expected_L_t = 1.24e11  # Approximately
    print(f"Step 2 - After decay: L_t = {L_t:.2e} CFU/day (expected: ≈{expected_L_t:.2e})")
    # Allow some tolerance for floating point
    assert abs(L_t - expected_L_t) / expected_L_t < 0.05, f"Decay result mismatch: {L_t} vs {expected_L_t}"
    
    # Step 3: Final concentration
    C = compute_concentration(L_t, Q)
    expected_C = 1.24e4  # 12,400 CFU/L
    print(f"Step 3 - Concentration: C = {C:.1f} CFU/L (expected: ≈{expected_C:.1f})")
    assert abs(C - expected_C) / expected_C < 0.05, f"Concentration mismatch: {C} vs {expected_C}"
    
    print("✓ Worked example test PASSED")
    return True


def test_conversion_functions():
    """Test LRV and T90 conversion functions."""
    print("\n=== Testing Conversion Functions ===")
    
    # Test LRV to eta conversion
    eta1 = eta_from_lrv(1.0)  # 1 log removal
    print(f"LRV=1 → η={eta1:.2f} (expected: 0.90)")
    assert abs(eta1 - 0.9) < 1e-6
    
    eta2 = eta_from_lrv(2.0)  # 2 log removal
    print(f"LRV=2 → η={eta2:.3f} (expected: 0.990)")
    assert abs(eta2 - 0.99) < 1e-6
    
    # Test T90 to k conversion
    k1 = k_from_T90(1.0)  # 1 day T90
    expected_k1 = 2.302585  # ln(10)
    print(f"T90=1 day → k={k1:.6f} day⁻¹ (expected: ≈{expected_k1:.6f})")
    assert abs(k1 - expected_k1) < 1e-5
    
    print("✓ Conversion functions test PASSED")
    return True


def test_decay_choice():
    """Test decay method selection logic."""
    print("\n=== Testing Decay Choice Logic ===")
    
    L = 1e11
    k = 0.7
    k_s = 0.01
    
    # Test time-based preferred
    L_result, method = choose_decay(L, t=1.0, k=k, d=100.0, k_s=k_s)
    expected_time = apply_decay_time(L, k, 1.0)
    print(f"Time + Distance available → method='{method}', L={L_result:.2e}")
    assert method == "time"
    assert abs(L_result - expected_time) < 1e6
    
    # Test distance-based fallback
    L_result, method = choose_decay(L, t=None, k=k, d=100.0, k_s=k_s)
    expected_dist = L * 0.36787944117  # e^(-0.01*100) ≈ e^(-1)
    print(f"Distance only → method='{method}', L={L_result:.2e}")
    assert method == "distance"
    
    # Test no decay
    L_result, method = choose_decay(L, t=None, k=k, d=None, k_s=k_s)
    print(f"No parameters → method='{method}', L={L_result:.2e}")
    assert method == "none"
    assert L_result == L
    
    print("✓ Decay choice test PASSED")
    return True


def test_unit_conversions():
    """Test unit conversion functions."""
    print("\n=== Testing Unit Conversions ===")
    
    # Flow conversion: m³/s to L/day
    Q_m3s = 1.0  # 1 m³/s
    Q_Lday = flow_m3s_to_Lday(Q_m3s)
    expected_Lday = 86_400_000  # 86.4 million L/day
    print(f"Flow: {Q_m3s} m³/s → {Q_Lday:.0f} L/day (expected: {expected_Lday})")
    assert Q_Lday == expected_Lday
    
    # Concentration conversion: CFU/L to CFU/100mL
    C_L = 12400  # From worked example
    C_100mL = concentration_to_100mL(C_L)
    expected_100mL = 1240  # 12400 * 0.1
    print(f"Concentration: {C_L} CFU/L → {C_100mL} CFU/100mL (expected: {expected_100mL})")
    assert C_100mL == expected_100mL
    
    print("✓ Unit conversion test PASSED")
    return True


def main():
    """Run all tests."""
    print("Testing FIO Core Mathematical Functions")
    print("=" * 50)
    
    try:
        test_worked_example()
        test_conversion_functions() 
        test_decay_choice()
        test_unit_conversions()
        
        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED!")
        print("Core mathematical functions are working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)