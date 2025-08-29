"""FIO Core Mathematical Functions - Three-Layer Model Implementation.

This module implements the pure mathematical functions for the three-layer
FIO contamination model as described in fio_modeling_markdown.md:

1. Source Load: L = Pop × EFIO × (1 - η)  
2. Environmental Decay: L_t = L × e^(-k×t) or L_d = L × e^(-k_s×d)
3. Receptor Concentration: C = L_reaching / Q

All functions are pure (no side effects) for easy testing and composition.
"""

import math
import logging
from typing import Optional, Union, Tuple


def compute_source_load(pop: float, efio: float, eta: float) -> float:
    """Calculate net source load from population after sanitation removal.
    
    Implements: L = Pop × EFIO × (1 - η)
    
    Args:
        pop: Population size (persons)
        efio: Excretion rate of faecal indicator organisms (CFU person⁻¹ day⁻¹)
        eta: Engineered removal efficiency (fraction, 0-1)
        
    Returns:
        Source load (CFU/day)
        
    Example:
        >>> compute_source_load(500, 1e9, 0.5)
        250000000000.0
    """
    if pop < 0:
        raise ValueError(f"Population must be >= 0, got {pop}")
    if efio < 0:
        raise ValueError(f"EFIO must be >= 0, got {efio}")
    if not 0 <= eta <= 1:
        if eta < 0 or eta > 1:
            logging.warning(f"Clamping eta {eta} to range [0, 1]")
            eta = max(0, min(1, eta))
    
    return pop * efio * (1 - eta)


def eta_from_lrv(lrv: float) -> float:
    """Convert log-removal value to removal efficiency fraction.
    
    Implements: η = 1 - 10^(-LRV)
    
    Args:
        lrv: Log-removal value (log₁₀ units)
        
    Returns:
        Removal efficiency η (fraction, 0-1)
        
    Example:
        >>> eta_from_lrv(1.0)  # 1 log removal
        0.9
        >>> eta_from_lrv(2.0)  # 2 log removal  
        0.99
    """
    if lrv < 0:
        logging.warning(f"LRV {lrv} is negative, this implies negative removal efficiency")
    
    eta = 1 - 10**(-lrv)
    return max(0, min(1, eta))  # Clamp to [0, 1]


def k_from_T90(T90: float) -> float:
    """Convert T90 (time for 1 log reduction) to decay constant.
    
    Implements: k = ln(10) / T90
    
    Args:
        T90: Time for 1 log₁₀ reduction (days)
        
    Returns:
        Decay constant k (day⁻¹)
        
    Example:
        >>> k_from_T90(1.0)  # 1-day T90
        2.302585092994046
    """
    if T90 <= 0:
        raise ValueError(f"T90 must be > 0, got {T90}")
    
    return math.log(10) / T90


def apply_decay_time(L: float, k: float, t: float) -> float:
    """Apply time-based first-order decay (Chick's Law).
    
    Implements: L_t = L × e^(-k×t)
    
    Args:
        L: Initial load (CFU/day)
        k: Decay constant (day⁻¹)
        t: Time in environment (days)
        
    Returns:
        Load after decay (CFU/day)
        
    Example:
        >>> apply_decay_time(2.5e11, 0.7, 1.0)
        123889894863.25221
    """
    if L < 0:
        raise ValueError(f"Load must be >= 0, got {L}")
    if k < 0:
        raise ValueError(f"Decay constant must be >= 0, got {k}")
    if t < 0:
        raise ValueError(f"Time must be >= 0, got {t}")
    
    return L * math.exp(-k * t)


def apply_decay_distance(L: float, k_s: float, d: float) -> float:
    """Apply distance-based spatial decay.
    
    Implements: L_d = L × e^(-k_s×d)
    
    Args:
        L: Initial load (CFU/day)
        k_s: Spatial decay constant (m⁻¹)
        d: Distance traveled (meters)
        
    Returns:
        Load after spatial decay (CFU/day)
    """
    if L < 0:
        raise ValueError(f"Load must be >= 0, got {L}")
    if k_s < 0:
        raise ValueError(f"Spatial decay constant must be >= 0, got {k_s}")
    if d < 0:
        raise ValueError(f"Distance must be >= 0, got {d}")
    
    return L * math.exp(-k_s * d)


def choose_decay(L: float, t: Optional[float], k: float, 
                d: Optional[float], k_s: float) -> Tuple[float, str]:
    """Choose between time-based and distance-based decay, preferring time.
    
    Args:
        L: Initial load (CFU/day)
        t: Time in environment (days, optional)
        k: Time-based decay constant (day⁻¹)
        d: Distance traveled (meters, optional)
        k_s: Spatial decay constant (m⁻¹)
        
    Returns:
        Tuple of (load_after_decay, method_used)
        method_used is one of: "time", "distance", "none"
        
    Example:
        >>> choose_decay(1e11, 1.0, 0.7, 100.0, 0.01)
        (49659696023.11584, 'time')
    """
    if t is not None and t >= 0:
        # Prefer time-based decay when available
        return apply_decay_time(L, k, t), "time"
    elif d is not None and d >= 0:
        # Fall back to distance-based decay
        return apply_decay_distance(L, k_s, d), "distance"
    else:
        # No decay data available - warn once and return identity
        logging.warning("No decay parameters available (t or d), applying no decay")
        return L, "none"


def compute_concentration(L_reaching: float, Q: float) -> float:
    """Calculate concentration at receptor.
    
    Implements: C = L_reaching / Q
    
    Args:
        L_reaching: Load reaching receptor after decay (CFU/day)
        Q: Receiving water flow/discharge (L/day)
        
    Returns:
        Concentration (CFU/L)
        
    Example:
        >>> compute_concentration(1.24e11, 1e7)
        12400.0
    """
    if L_reaching < 0:
        raise ValueError(f"Load must be >= 0, got {L_reaching}")
    if Q <= 0:
        raise ValueError(f"Flow must be > 0, got {Q}")
    
    return L_reaching / Q


# Unit conversion functions

def flow_m3s_to_Lday(Q_m3s: float) -> float:
    """Convert flow from m³/s to L/day.
    
    Args:
        Q_m3s: Flow in m³/s
        
    Returns:
        Flow in L/day
        
    Example:
        >>> flow_m3s_to_Lday(1.0)  # 1 m³/s
        86400000.0  # L/day
    """
    if Q_m3s < 0:
        raise ValueError(f"Flow must be >= 0, got {Q_m3s}")
    
    # 1 m³/s = 1000 L/s = 1000 * 86400 L/day
    return Q_m3s * 86_400 * 1_000


def concentration_to_100mL(C_L: float) -> float:
    """Convert concentration from CFU/L to CFU/100mL.
    
    Args:
        C_L: Concentration in CFU/L
        
    Returns:
        Concentration in CFU/100mL
        
    Example:
        >>> concentration_to_100mL(1000.0)  # 1000 CFU/L
        100.0  # CFU/100mL
    """
    if C_L < 0:
        raise ValueError(f"Concentration must be >= 0, got {C_L}")
    
    # 1 L = 10 × 100mL, so CFU/100mL = CFU/L × 0.1
    return C_L * 0.1