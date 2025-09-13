"""Optimized Streamlit dashboard for pathogen scenario modeling.

Fast and lightweight dashboard with essential features focused on
decision-making metrics for stakeholders.
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

# Support both package and script execution
try:
    from app import fio_config as config
    from app import fio_runner
except Exception:
    from . import fio_config as config
    from . import fio_runner


def set_page_config():
    """Configure the Streamlit page."""
    st.set_page_config(
        page_title="Zanzibar Pathogen Model",
        page_icon="🌊",
        layout="centered"
    )


def load_minimal_outputs() -> Dict[str, Any]:
    """Load only essential data for display to minimize memory usage."""
    outputs = {}
    
    # Only load borehole concentrations if available
    if config.FIO_CONCENTRATION_AT_BOREHOLES_PATH.exists():
        try:
            df = pd.read_csv(config.FIO_CONCENTRATION_AT_BOREHOLES_PATH)
            # Calculate summary stats immediately to avoid storing full dataframe
            concentrations = df['concentration_CFU_per_100mL'].dropna()
            
            outputs['stats'] = {
                'total_boreholes': len(df),
                'private_boreholes': len(df[df['borehole_type'] == 'private']),
                'government_boreholes': len(df[df['borehole_type'] == 'government']),
                'avg_concentration': float(concentrations.mean()) if len(concentrations) > 0 else 0,
                'max_concentration': float(concentrations.max()) if len(concentrations) > 0 else 0,
                'min_concentration': float(concentrations.min()) if len(concentrations) > 0 else 0,
                'low_risk': len(concentrations[concentrations < 10]),
                'moderate_risk': len(concentrations[(concentrations >= 10) & (concentrations < 100)]),
                'high_risk': len(concentrations[(concentrations >= 100) & (concentrations < 1000)]),
                'very_high_risk': len(concentrations[concentrations >= 1000])
            }
            # Clear the dataframe from memory
            del df, concentrations
        except Exception as e:
            outputs['stats'] = None
    else:
        outputs['stats'] = None
    
    return outputs


def create_simple_scenario_form() -> Dict[str, Any]:
    """Create a minimal scenario form with only essential parameters."""
    st.sidebar.header("🎯 Scenario Parameters")
    
    # Essential parameters only
    st.sidebar.subheader("Core Settings")
    
    population_factor = st.sidebar.slider(
        "Population Factor", 
        0.5, 2.0, 1.0, 0.1,
        help="Adjust population density (1.0 = baseline)"
    )
    
    od_reduction = st.sidebar.slider(
        "Open Defecation Reduction (%)", 
        0, 100, 50, 10,
        help="Percentage reduction in open defecation"
    )
    
    infrastructure_upgrade = st.sidebar.slider(
        "Infrastructure Upgrade (%)", 
        0, 100, 25, 10,
        help="Percentage of sanitation infrastructure upgraded"
    )
    
    # Build minimal scenario
    scenario = {
        'scenario_name': 'optimized_scenario',
        'pop_factor': float(population_factor),
        'od_reduction_percent': float(od_reduction),
        'infrastructure_upgrade_percent': float(infrastructure_upgrade),
        'fecal_sludge_treatment_percent': 0.0,  # Default
        'centralized_treatment_enabled': False,  # Default
        'ks_per_m': 0.06,  # Default spatial decay
        'radius_by_type': {'private': 35, 'government': 100},  # Defaults
        'efficiency_override': {1: 0.5, 2: 0.1, 3: 0.3, 4: 0.0},  # Defaults
        'heatmap_radius': 18,  # Default
        'link_batch_size': 1000,  # Default
        'rebuild_standardized': False
    }
    
    return scenario


def display_minimal_results(stats: Optional[Dict[str, Any]]):
    """Display essential results in a compact format."""
    if stats is None:
        st.info("📊 Run a scenario to see results")
        return
    
    st.subheader("📊 Key Results")
    
    # Essential metrics in a compact layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Boreholes", f"{stats['total_boreholes']:,}")
        st.metric("Private Boreholes", f"{stats['private_boreholes']:,}")
        st.metric("Government Boreholes", f"{stats['government_boreholes']:,}")
    
    with col2:
        if stats['avg_concentration'] > 0:
            st.metric("Average Concentration", f"{stats['avg_concentration']:.1f} CFU/100mL")
            st.metric("Maximum Concentration", f"{stats['max_concentration']:.1f} CFU/100mL")
        else:
            st.metric("Average Concentration", "0 CFU/100mL")
            st.metric("Maximum Concentration", "0 CFU/100mL")
    
    # Risk distribution in simple text format
    st.subheader("🚨 Risk Assessment")
    
    total_wells = sum([stats['low_risk'], stats['moderate_risk'], 
                      stats['high_risk'], stats['very_high_risk']])
    
    if total_wells > 0:
        risk_data = [
            ("Low Risk (<10 CFU/100mL)", stats['low_risk'], "green"),
            ("Moderate Risk (10-99 CFU/100mL)", stats['moderate_risk'], "blue"),
            ("High Risk (100-999 CFU/100mL)", stats['high_risk'], "orange"),
            ("Very High Risk (≥1000 CFU/100mL)", stats['very_high_risk'], "red")
        ]
        
        for category, count, color in risk_data:
            percentage = (count / total_wells) * 100
            st.write(f"**{category}**: {count:,} wells ({percentage:.1f}%)")
    else:
        st.write("No risk data available")


def display_scenario_summary(scenario: Dict[str, Any]):
    """Display current scenario parameters."""
    st.subheader("⚙️ Current Scenario")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Population Factor**: {scenario['pop_factor']:.1f}x")
        st.write(f"**OD Reduction**: {scenario['od_reduction_percent']:.0f}%")
    
    with col2:
        st.write(f"**Infrastructure Upgrade**: {scenario['infrastructure_upgrade_percent']:.0f}%")
        st.write(f"**Scenario Name**: {scenario['scenario_name']}")


def main():
    """Main lightweight dashboard application."""
    set_page_config()
    
    # Simple header
    st.title("🌊 Zanzibar Pathogen Model")
    st.markdown("**Optimized Dashboard - Fast & Lightweight**")
    
    # Load minimal data
    outputs = load_minimal_outputs()
    
    # Create simple scenario form
    scenario = create_simple_scenario_form()
    
    # Display current scenario
    display_scenario_summary(scenario)
    
    # Run scenario button
    if st.sidebar.button("🚀 Run Scenario", type="primary"):
        with st.spinner("Running pathogen model..."):
            try:
                # Run scenario
                fio_runner.run_scenario(scenario)
                st.success("✅ Scenario completed!")
                
                # Reload results
                outputs = load_minimal_outputs()
                
                # Force page refresh
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error running scenario: {str(e)}")
    
    # Display results
    display_minimal_results(outputs.get('stats'))
    
    # Simple instructions
    with st.expander("ℹ️ How to Use"):
        st.write("""
        1. **Adjust Parameters**: Use the sliders in the sidebar to set scenario parameters
        2. **Run Scenario**: Click the 'Run Scenario' button to execute the model
        3. **Review Results**: Key metrics and risk assessment will appear below
        
        **Optimized Performance**: This dashboard uses minimal memory and processing power,
        suitable for systems with limited resources.
        """)
    
    # Performance info
    st.caption("⚡ Optimized for speed and low memory usage")


if __name__ == "__main__":
    main()