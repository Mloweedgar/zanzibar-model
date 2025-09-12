#!/usr/bin/env python3
"""
Generate figures for Zanzibar FIO model deliverables.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr

def create_model_vs_lab_scatter():
    """Create model vs lab scatter plot."""
    # Load government data
    gov_data = pd.read_csv('data/output/dashboard_government_boreholes.csv')
    
    # Process lab data
    gov_data['lab_ecoli_numeric'] = pd.to_numeric(gov_data['lab_e_coli_CFU_per_100mL'], errors='coerce')
    
    # Get data for plotting (use floor of 0.1 for non-detects)
    has_lab = gov_data[gov_data['lab_ecoli_numeric'].notna()].copy()
    has_lab['lab_floor'] = has_lab['lab_ecoli_numeric'].apply(lambda x: max(x, 0.1))
    
    model_vals = has_lab['concentration_CFU_per_100mL'].values
    lab_vals = has_lab['lab_floor'].values
    
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    
    # Scatter plot with different markers for detects vs non-detects
    detects = has_lab['lab_ecoli_numeric'] > 0
    non_detects = has_lab['lab_ecoli_numeric'] == 0
    
    # Plot non-detects
    if non_detects.any():
        ax.scatter(model_vals[non_detects], lab_vals[non_detects], 
                  marker='s', s=60, alpha=0.6, c='lightblue', 
                  label=f'Non-detects (n={non_detects.sum()})')
    
    # Plot detects
    if detects.any():
        ax.scatter(model_vals[detects], lab_vals[detects], 
                  marker='o', s=80, alpha=0.8, c='red',
                  label=f'Detections (n={detects.sum()})')
    
    # Set log scales
    ax.set_xscale('log')
    ax.set_yscale('log')
    
    # Add 1:1 line
    min_val = 0.01
    max_val = max(model_vals.max(), lab_vals.max()) * 2
    line_vals = np.logspace(np.log10(min_val), np.log10(max_val), 100)
    ax.plot(line_vals, line_vals, 'k--', alpha=0.5, label='1:1 Line')
    
    # Calculate correlations for positive detections only
    if detects.sum() >= 2:
        pos_model = model_vals[detects]
        pos_lab = has_lab.loc[detects, 'lab_ecoli_numeric'].values
        
        from scipy.stats import spearmanr, kendalltau
        spear_rho, _ = spearmanr(pos_model, pos_lab)
        kendall_tau, _ = kendalltau(pos_model, pos_lab)
        
        # Log-space Pearson
        model_log = np.log10(pos_model + 1)
        lab_log = np.log10(pos_lab + 1)
        pearson_log, _ = pearsonr(model_log, lab_log)
        
        # Add correlation text
        corr_text = f'Positive Detections (n={detects.sum()}):\n'
        corr_text += f'Spearman ρ = {spear_rho:.3f}\n'
        corr_text += f'Kendall τ = {kendall_tau:.3f}\n'
        corr_text += f'Pearson r (log) = {pearson_log:.3f}'
        
        ax.text(0.02, 0.98, corr_text, transform=ax.transAxes, 
               fontsize=10, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Labels and title
    ax.set_xlabel('Modeled Concentration (CFU/100mL)', fontsize=12)
    ax.set_ylabel('Laboratory E. coli (CFU/100mL)', fontsize=12)
    ax.set_title('Model vs Laboratory Validation\nZanzibar Government Boreholes', fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('deliverables/model_vs_lab_scatter.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Created scatter plot: deliverables/model_vs_lab_scatter.png")

def create_concentration_distributions():
    """Create concentration distribution comparison."""
    # Load data
    gov_data = pd.read_csv('data/output/dashboard_government_boreholes.csv')
    private_data = pd.read_csv('data/output/dashboard_private_boreholes.csv')
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Government histogram
    gov_conc = gov_data['concentration_CFU_per_100mL']
    ax1.hist(gov_conc, bins=20, alpha=0.7, color='red', edgecolor='black')
    ax1.set_xlabel('Concentration (CFU/100mL)')
    ax1.set_ylabel('Count')
    ax1.set_title(f'Government Boreholes (n={len(gov_conc)})')
    ax1.set_yscale('log')
    ax1.grid(True, alpha=0.3)
    
    # Add median line
    ax1.axvline(gov_conc.median(), color='darkred', linestyle='--', 
               label=f'Median: {gov_conc.median():.1f}')
    ax1.legend()
    
    # Private histogram (sample for visibility)
    private_conc = private_data['concentration_CFU_per_100mL']
    # Sample if too many points
    if len(private_conc) > 5000:
        sample_conc = private_conc.sample(n=5000, random_state=42)
    else:
        sample_conc = private_conc
        
    ax2.hist(sample_conc, bins=50, alpha=0.7, color='blue', edgecolor='black')
    ax2.set_xlabel('Concentration (CFU/100mL)')  
    ax2.set_ylabel('Count')
    ax2.set_title(f'Private Boreholes (n={len(private_conc)}, sample shown)')
    ax2.set_yscale('log')
    ax2.grid(True, alpha=0.3)
    
    # Add median line
    ax2.axvline(private_conc.median(), color='darkblue', linestyle='--',
               label=f'Median: {private_conc.median():.1f}')
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig('deliverables/concentration_distributions.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Created distribution plot: deliverables/concentration_distributions.png")

def create_category_comparison():
    """Create concentration category comparison chart."""
    # Load data
    gov_data = pd.read_csv('data/output/dashboard_government_boreholes.csv')
    private_data = pd.read_csv('data/output/dashboard_private_boreholes.csv')
    
    def categorize_concentration(conc):
        if conc < 10: return 'Low (<10)'
        elif conc < 100: return 'Moderate (10-99)'  
        elif conc < 1000: return 'High (100-999)'
        else: return 'Very High (≥1000)'
    
    # Categorize
    gov_data['category'] = gov_data['concentration_CFU_per_100mL'].apply(categorize_concentration)
    private_data['category'] = private_data['concentration_CFU_per_100mL'].apply(categorize_concentration)
    
    # Count categories
    categories = ['Low (<10)', 'Moderate (10-99)', 'High (100-999)', 'Very High (≥1000)']
    gov_counts = [gov_data[gov_data['category'] == cat].shape[0] for cat in categories]
    priv_counts = [private_data[private_data['category'] == cat].shape[0] for cat in categories]
    
    # Convert to percentages
    gov_pcts = [count/len(gov_data)*100 for count in gov_counts]
    priv_pcts = [count/len(private_data)*100 for count in priv_counts]
    
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    
    x = np.arange(len(categories))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, gov_pcts, width, label='Government', color='red', alpha=0.7)
    bars2 = ax.bar(x + width/2, priv_pcts, width, label='Private', color='blue', alpha=0.7)
    
    # Add value labels on bars
    for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
        height1 = bar1.get_height()
        height2 = bar2.get_height()
        ax.text(bar1.get_x() + bar1.get_width()/2., height1 + 0.5,
               f'{height1:.1f}%\n({gov_counts[i]})', ha='center', va='bottom', fontsize=9)
        ax.text(bar2.get_x() + bar2.get_width()/2., height2 + 0.5,
               f'{height2:.1f}%\n({priv_counts[i]})', ha='center', va='bottom', fontsize=9)
    
    ax.set_xlabel('Concentration Category (CFU/100mL)')
    ax.set_ylabel('Percentage of Boreholes')
    ax.set_title('Concentration Category Distribution by Borehole Type')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('deliverables/category_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Created category comparison: deliverables/category_comparison.png")

def main():
    print("Generating figures for Zanzibar FIO model deliverables...")
    
    # Set style
    plt.style.use('default')
    sns.set_palette("husl")
    
    try:
        create_model_vs_lab_scatter()
        create_concentration_distributions()
        create_category_comparison()
        print("\\nAll figures generated successfully!")
        print("\\nFiles created:")
        print("- deliverables/model_vs_lab_scatter.png")  
        print("- deliverables/concentration_distributions.png")
        print("- deliverables/category_comparison.png")
    except Exception as e:
        print(f"Error generating figures: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()