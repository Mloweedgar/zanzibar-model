"""Scenario comparison utilities for enhanced dashboard.

This module provides functions to compare multiple scenarios side-by-side
for better decision-making and TOR reporting requirements.
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple
import json
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

from . import fio_config as config
from . import fio_runner


def run_multiple_scenarios(scenarios: List[Dict[str, Any]], scenario_names: List[str]) -> Dict[str, pd.DataFrame]:
    """Run multiple scenarios and collect results for comparison.
    
    Args:
        scenarios: List of scenario parameter dictionaries
        scenario_names: List of names for each scenario
        
    Returns:
        Dictionary mapping scenario names to concentration DataFrames
    """
    results = {}
    
    for i, (scenario, name) in enumerate(zip(scenarios, scenario_names)):
        st.info(f"Running scenario {i+1}/{len(scenarios)}: {name}")
        
        try:
            # Run the scenario
            fio_runner.run_scenario(scenario)
            
            # Load concentration results
            if config.FIO_CONCENTRATION_AT_BOREHOLES_PATH.exists():
                df = pd.read_csv(config.FIO_CONCENTRATION_AT_BOREHOLES_PATH)
                results[name] = df.copy()
            else:
                st.warning(f"No concentration results found for scenario: {name}")
                results[name] = pd.DataFrame()
                
        except Exception as e:
            st.error(f"Error running scenario {name}: {str(e)}")
            results[name] = pd.DataFrame()
    
    return results


def create_comparison_summary(scenario_results: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create a summary table comparing key metrics across scenarios.
    
    Args:
        scenario_results: Dict mapping scenario names to concentration DataFrames
        
    Returns:
        DataFrame with comparison metrics
    """
    summary_data = []
    
    for scenario_name, df in scenario_results.items():
        if df.empty:
            continue
            
        # Calculate key metrics
        concentrations = df['concentration_CFU_per_100mL'].dropna()
        
        if len(concentrations) > 0:
            metrics = {
                'Scenario': scenario_name,
                'Total Boreholes': len(df),
                'Private Boreholes': len(df[df['borehole_type'] == 'private']),
                'Government Boreholes': len(df[df['borehole_type'] == 'government']),
                'Mean Concentration (CFU/100mL)': concentrations.mean(),
                'Median Concentration (CFU/100mL)': concentrations.median(),
                'Max Concentration (CFU/100mL)': concentrations.max(),
                'High Risk Boreholes (≥100 CFU/100mL)': len(concentrations[concentrations >= 100]),
                'High Risk Percentage': len(concentrations[concentrations >= 100]) / len(concentrations) * 100,
                'Very High Risk Boreholes (≥1000 CFU/100mL)': len(concentrations[concentrations >= 1000]),
                'Very High Risk Percentage': len(concentrations[concentrations >= 1000]) / len(concentrations) * 100
            }
        else:
            metrics = {
                'Scenario': scenario_name,
                'Total Boreholes': len(df),
                'Private Boreholes': 0,
                'Government Boreholes': 0,
                'Mean Concentration (CFU/100mL)': 0,
                'Median Concentration (CFU/100mL)': 0,
                'Max Concentration (CFU/100mL)': 0,
                'High Risk Boreholes (≥100 CFU/100mL)': 0,
                'High Risk Percentage': 0,
                'Very High Risk Boreholes (≥1000 CFU/100mL)': 0,
                'Very High Risk Percentage': 0
            }
        
        summary_data.append(metrics)
    
    return pd.DataFrame(summary_data)


def create_comparison_charts(scenario_results: Dict[str, pd.DataFrame]) -> List[plt.Figure]:
    """Create comparison charts for multiple scenarios.
    
    Args:
        scenario_results: Dict mapping scenario names to concentration DataFrames
        
    Returns:
        List of matplotlib figures
    """
    figures = []
    
    # Filter out empty results
    valid_results = {name: df for name, df in scenario_results.items() if not df.empty}
    
    if len(valid_results) < 2:
        return figures
    
    # Set style
    plt.style.use('default')
    sns.set_palette("husl")
    
    # Chart 1: Risk Level Distribution
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    
    risk_data = []
    for scenario_name, df in valid_results.items():
        concentrations = df['concentration_CFU_per_100mL'].dropna()
        if len(concentrations) > 0:
            low = len(concentrations[concentrations < 10])
            moderate = len(concentrations[(concentrations >= 10) & (concentrations < 100)])
            high = len(concentrations[(concentrations >= 100) & (concentrations < 1000)])
            very_high = len(concentrations[concentrations >= 1000])
            
            risk_data.append({
                'Scenario': scenario_name,
                'Low (<10)': low,
                'Moderate (10-99)': moderate,
                'High (100-999)': high,
                'Very High (≥1000)': very_high
            })
    
    if risk_data:
        risk_df = pd.DataFrame(risk_data)
        risk_df.set_index('Scenario')[['Low (<10)', 'Moderate (10-99)', 'High (100-999)', 'Very High (≥1000)']].plot(
            kind='bar', stacked=True, ax=ax1, 
            color=['green', 'blue', 'orange', 'red']
        )
        ax1.set_title('Pathogen Risk Distribution by Scenario', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Scenario')
        ax1.set_ylabel('Number of Boreholes')
        ax1.legend(title='Risk Level (CFU/100mL)', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.xticks(rotation=45)
        plt.tight_layout()
        figures.append(fig1)
    
    # Chart 2: Mean Concentration Comparison
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    
    scenario_names = list(valid_results.keys())
    mean_concentrations = []
    
    for scenario_name, df in valid_results.items():
        concentrations = df['concentration_CFU_per_100mL'].dropna()
        if len(concentrations) > 0:
            mean_concentrations.append(concentrations.mean())
        else:
            mean_concentrations.append(0)
    
    bars = ax2.bar(scenario_names, mean_concentrations, 
                   color=sns.color_palette("husl", len(scenario_names)))
    ax2.set_title('Mean Pathogen Concentration by Scenario', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Scenario')
    ax2.set_ylabel('Mean Concentration (CFU/100mL)')
    ax2.set_yscale('log')
    
    # Add value labels on bars
    for bar, value in zip(bars, mean_concentrations):
        if value > 0:
            ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                    f'{value:.1e}', ha='center', va='bottom', rotation=0)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    figures.append(fig2)
    
    # Chart 3: Box Plot Comparison (log scale)
    fig3, ax3 = plt.subplots(figsize=(12, 8))
    
    concentration_data = []
    scenario_labels = []
    
    for scenario_name, df in valid_results.items():
        concentrations = df['concentration_CFU_per_100mL'].dropna()
        if len(concentrations) > 0:
            # Add small value to avoid log(0)
            log_concentrations = np.log10(concentrations + 1)
            concentration_data.append(log_concentrations)
            scenario_labels.append(scenario_name)
    
    if concentration_data:
        ax3.boxplot(concentration_data, labels=scenario_labels)
        ax3.set_title('Pathogen Concentration Distribution (Log Scale)', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Scenario')
        ax3.set_ylabel('Log10(Concentration + 1)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        figures.append(fig3)
    
    return figures


def generate_comparison_report(scenario_results: Dict[str, pd.DataFrame], 
                             scenario_params: Dict[str, Dict[str, Any]]) -> str:
    """Generate a text report comparing scenarios for TOR compliance.
    
    Args:
        scenario_results: Dict mapping scenario names to concentration DataFrames
        scenario_params: Dict mapping scenario names to parameter dictionaries
        
    Returns:
        Formatted text report
    """
    report_lines = []
    report_lines.append("ZANZIBAR PATHOGEN MODEL - SCENARIO COMPARISON REPORT")
    report_lines.append("=" * 60)
    report_lines.append("")
    report_lines.append("Generated for World Bank Terms of Reference compliance")
    report_lines.append("Ocean Health and Sanitation Nexus in Zanzibar")
    report_lines.append("")
    
    # Executive Summary
    report_lines.append("EXECUTIVE SUMMARY")
    report_lines.append("-" * 20)
    report_lines.append(f"Number of scenarios analyzed: {len(scenario_results)}")
    
    valid_scenarios = [name for name, df in scenario_results.items() if not df.empty]
    report_lines.append(f"Scenarios with valid results: {len(valid_scenarios)}")
    report_lines.append("")
    
    # Scenario Parameters
    report_lines.append("SCENARIO PARAMETERS")
    report_lines.append("-" * 20)
    
    for scenario_name, params in scenario_params.items():
        report_lines.append(f"\n{scenario_name.upper()}:")
        report_lines.append(f"  Population Factor: {params.get('pop_factor', 1.0):.2f}")
        report_lines.append(f"  OD Reduction: {params.get('od_reduction_percent', 0):.0f}%")
        report_lines.append(f"  Infrastructure Upgrade: {params.get('infrastructure_upgrade_percent', 0):.0f}%")
        report_lines.append(f"  Fecal Sludge Treatment: {params.get('fecal_sludge_treatment_percent', 0):.0f}%")
        report_lines.append(f"  Centralized Treatment: {'Enabled' if params.get('centralized_treatment_enabled', False) else 'Disabled'}")
        report_lines.append(f"  EFIO: {params.get('EFIO_override', 'Default')}")
        report_lines.append(f"  Spatial Decay Rate: {params.get('ks_per_m', 0.06):.3f} 1/m")
    
    report_lines.append("")
    
    # Results Summary
    report_lines.append("RESULTS SUMMARY")
    report_lines.append("-" * 20)
    
    summary_df = create_comparison_summary(scenario_results)
    
    if not summary_df.empty:
        report_lines.append("\nKey Metrics:")
        for _, row in summary_df.iterrows():
            report_lines.append(f"\n{row['Scenario'].upper()}:")
            report_lines.append(f"  Total Boreholes: {row['Total Boreholes']:.0f}")
            report_lines.append(f"  Mean Concentration: {row['Mean Concentration (CFU/100mL)']:.1e} CFU/100mL")
            report_lines.append(f"  High Risk Boreholes (≥100 CFU/100mL): {row['High Risk Boreholes (≥100 CFU/100mL)']:.0f} ({row['High Risk Percentage']:.1f}%)")
            report_lines.append(f"  Very High Risk Boreholes (≥1000 CFU/100mL): {row['Very High Risk Boreholes (≥1000 CFU/100mL)']:.0f} ({row['Very High Risk Percentage']:.1f}%)")
    
    report_lines.append("")
    
    # Model Information
    report_lines.append("MODEL DESCRIPTION")
    report_lines.append("-" * 20)
    report_lines.append("3-layer pathogen transport model:")
    report_lines.append("- Layer 1: Household pathogen loads (Pop × EFIO × (1-η))")
    report_lines.append("- Layer 2: Spatial transport with exponential decay")
    report_lines.append("- Layer 3: Borehole concentration calculation")
    report_lines.append("")
    report_lines.append("Risk Categories (CFU/100mL):")
    report_lines.append("- Low: <10")
    report_lines.append("- Moderate: 10-99")
    report_lines.append("- High: 100-999")
    report_lines.append("- Very High: ≥1000")
    report_lines.append("")
    
    # TOR Compliance
    report_lines.append("TOR COMPLIANCE NOTES")
    report_lines.append("-" * 20)
    report_lines.append("This report supports the following TOR deliverables:")
    report_lines.append("- GIS-Based Model scenarios with maps and visualizations")
    report_lines.append("- Well documented model scenarios capturing baseline vs scenario results")
    report_lines.append("- Automated Geospatial Data Workflows")
    report_lines.append("- Ready-to-use geospatial datasets for stakeholder presentations")
    report_lines.append("")
    
    return "\n".join(report_lines)


def display_scenario_comparison_ui():
    """Display the scenario comparison interface in Streamlit."""
    st.subheader("🔀 Scenario Comparison Tool")
    
    st.markdown("""
    Compare multiple sanitation intervention scenarios to evaluate their effectiveness
    in reducing pathogen contamination across Zanzibar's borehole network.
    """)
    
    # Predefined scenario templates
    baseline_scenarios = {
        'Current Baseline': {
            'pop_factor': 1.0,
            'od_reduction_percent': 0.0,
            'infrastructure_upgrade_percent': 0.0,
            'fecal_sludge_treatment_percent': 0.0,
            'centralized_treatment_enabled': False,
            'EFIO_override': 1.0e7,
            'ks_per_m': 0.06,
            'radius_by_type': {'private': 35, 'government': 100},
            'efficiency_override': {1: 0.50, 2: 0.10, 3: 0.30, 4: 0.0},
            'link_batch_size': 1000,
            'rebuild_standardized': False
        },
        '50% Infrastructure Improvement': {
            'pop_factor': 1.0,
            'od_reduction_percent': 30.0,
            'infrastructure_upgrade_percent': 50.0,
            'fecal_sludge_treatment_percent': 25.0,
            'centralized_treatment_enabled': False,
            'EFIO_override': 1.0e7,
            'ks_per_m': 0.06,
            'radius_by_type': {'private': 35, 'government': 100},
            'efficiency_override': {1: 0.50, 2: 0.10, 3: 0.30, 4: 0.0},
            'link_batch_size': 1000,
            'rebuild_standardized': False
        },
        'Full Intervention': {
            'pop_factor': 1.0,
            'od_reduction_percent': 80.0,
            'infrastructure_upgrade_percent': 70.0,
            'fecal_sludge_treatment_percent': 60.0,
            'centralized_treatment_enabled': True,
            'EFIO_override': 1.0e7,
            'ks_per_m': 0.06,
            'radius_by_type': {'private': 35, 'government': 100},
            'efficiency_override': {1: 0.50, 2: 0.10, 3: 0.30, 4: 0.0},
            'link_batch_size': 1000,
            'rebuild_standardized': False
        }
    }
    
    # Scenario selection
    selected_scenarios = st.multiselect(
        "Select scenarios to compare:",
        options=list(baseline_scenarios.keys()),
        default=['Current Baseline', '50% Infrastructure Improvement'],
        help="Choose 2-3 scenarios for meaningful comparison"
    )
    
    if len(selected_scenarios) < 2:
        st.info("📋 Please select at least 2 scenarios for comparison.")
        return
    
    if len(selected_scenarios) > 4:
        st.warning("⚠️ Comparing more than 4 scenarios may take significant time.")
    
    # Display selected scenarios
    with st.expander("📊 Preview Selected Scenario Parameters", expanded=True):
        for scenario_name in selected_scenarios:
            scenario = baseline_scenarios[scenario_name]
            st.markdown(f"**{scenario_name}:**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"• OD Reduction: {scenario['od_reduction_percent']:.0f}%")
                st.write(f"• Infrastructure Upgrade: {scenario['infrastructure_upgrade_percent']:.0f}%")
            with col2:
                st.write(f"• Fecal Sludge Treatment: {scenario['fecal_sludge_treatment_percent']:.0f}%")
                st.write(f"• Centralized Treatment: {'Yes' if scenario['centralized_treatment_enabled'] else 'No'}")
            with col3:
                st.write(f"• Population Factor: {scenario['pop_factor']:.1f}x")
                st.write(f"• EFIO: {scenario['EFIO_override']:.1e}")
            st.markdown("---")
    
    # Run comparison button
    if st.button("🔄 Run Scenario Comparison", type="primary"):
        if len(selected_scenarios) >= 2:
            scenarios_to_run = [baseline_scenarios[name] for name in selected_scenarios]
            
            with st.spinner(f"Running {len(selected_scenarios)} scenarios... This may take several minutes."):
                try:
                    results = run_multiple_scenarios(scenarios_to_run, selected_scenarios)
                    
                    # Store results in session state
                    st.session_state['comparison_results'] = results
                    st.session_state['comparison_params'] = {name: baseline_scenarios[name] for name in selected_scenarios}
                    
                    st.success("✅ Scenario comparison completed!")
                    
                except Exception as e:
                    st.error(f"❌ Error running scenario comparison: {str(e)}")
                    st.exception(e)
    
    # Display results if available
    if 'comparison_results' in st.session_state and st.session_state['comparison_results']:
        results = st.session_state['comparison_results']
        params = st.session_state['comparison_params']
        
        st.markdown("---")
        
        # Summary table
        st.subheader("📊 Comparison Summary")
        try:
            summary_df = create_comparison_summary(results)
            if not summary_df.empty:
                # Format the dataframe for better display
                display_df = summary_df.copy()
                
                # Round numeric columns
                numeric_cols = ['Mean Concentration (CFU/100mL)', 'Median Concentration (CFU/100mL)', 
                               'Max Concentration (CFU/100mL)']
                for col in numeric_cols:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:.2e}" if x > 1000 else f"{x:.1f}")
                
                st.dataframe(display_df, use_container_width=True)
                
                # Key insights
                if len(summary_df) >= 2:
                    baseline_row = summary_df.iloc[0]
                    best_row = summary_df.loc[summary_df['High Risk Percentage'].idxmin()]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            "Baseline High Risk %", 
                            f"{baseline_row['High Risk Percentage']:.1f}%",
                            help="Percentage of boreholes with ≥100 CFU/100mL"
                        )
                    with col2:
                        st.metric(
                            "Best Scenario High Risk %", 
                            f"{best_row['High Risk Percentage']:.1f}%",
                            delta=f"{best_row['High Risk Percentage'] - baseline_row['High Risk Percentage']:.1f}%",
                            help=f"Best performance: {best_row['Scenario']}"
                        )
            else:
                st.warning("No valid results to display in summary.")
                
        except Exception as e:
            st.error(f"Error creating summary: {str(e)}")
        
        # Charts
        st.subheader("📈 Comparison Charts")
        try:
            charts = create_comparison_charts(results)
            
            if charts:
                for i, fig in enumerate(charts):
                    st.pyplot(fig)
                    plt.close(fig)  # Close to free memory
            else:
                st.info("No charts available. This may occur if scenarios have insufficient data.")
                
        except Exception as e:
            st.error(f"Error creating charts: {str(e)}")
        
        # Generate report
        st.subheader("📄 Comparison Report")
        try:
            report_text = generate_comparison_report(results, params)
            
            with st.expander("📋 View Full Report", expanded=False):
                st.text(report_text)
            
            # Download report
            st.download_button(
                label="📋 Download Comparison Report",
                data=report_text,
                file_name=f"scenario_comparison_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.txt",
                mime='text/plain',
                help="Download the complete comparison report for TOR deliverables"
            )
            
        except Exception as e:
            st.error(f"Error generating report: {str(e)}")
    
    else:
        st.info("👆 Select scenarios and click 'Run Scenario Comparison' to see detailed analysis.")