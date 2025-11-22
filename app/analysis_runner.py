import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging
from . import config

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def analyze_scenario(name, path):
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        logging.warning(f"File not found: {path}")
        return None

    # Filter for private wells
    private = df[df['borehole_type'] == 'private']
    
    if private.empty:
        return None

    # Metrics
    median_conc = private['concentration_CFU_per_100mL'].median()
    mean_conc = private['concentration_CFU_per_100mL'].mean()
    
    # Risk Categories
    high_risk = (private['concentration_CFU_per_100mL'] > 1000).mean() * 100
    med_risk = ((private['concentration_CFU_per_100mL'] > 10) & (private['concentration_CFU_per_100mL'] <= 1000)).mean() * 100
    low_risk = (private['concentration_CFU_per_100mL'] <= 10).mean() * 100
    
    return {
        'Scenario': name,
        'Median CFU': median_conc,
        'Mean CFU': mean_conc,
        '% High Risk (>1000)': high_risk,
        '% Moderate Risk (10-1000)': med_risk,
        '% Low Risk (<10)': low_risk,
        'Count': len(private)
    }

def generate_charts(summary: pd.DataFrame, output_dir: Path):
    """Generate infographics for the report."""
    sns.set_theme(style="whitegrid")
    
    # 1. Mean Contamination Comparison
    plt.figure(figsize=(10, 6))
    ax = sns.barplot(x='Scenario', y='Mean CFU', data=summary, palette='Reds_r')
    plt.title('Average Pathogen Load in Private Wells by Scenario', fontsize=14, fontweight='bold')
    plt.ylabel('Mean E. coli (CFU/100mL)')
    plt.xlabel('')
    plt.xticks(rotation=15)
    
    # Add values on top
    for i, v in enumerate(summary['Mean CFU']):
        ax.text(i, v + 50, f"{v:.0f}", ha='center', fontweight='bold')
        
    plt.tight_layout()
    plt.savefig(output_dir / 'chart_mean_contamination.png', dpi=300)
    plt.close()
    
    # 2. Risk Reduction (High Risk %)
    plt.figure(figsize=(10, 6))
    ax = sns.barplot(x='Scenario', y='% High Risk (>1000)', data=summary, palette='Oranges_r')
    plt.title('Percentage of High Risk Wells (>1000 CFU/100mL)', fontsize=14, fontweight='bold')
    plt.ylabel('% of Wells')
    plt.xlabel('')
    plt.xticks(rotation=15)
    
    for i, v in enumerate(summary['% High Risk (>1000)']):
        ax.text(i, v + 0.5, f"{v:.1f}%", ha='center', fontweight='bold')
        
    plt.tight_layout()
    plt.savefig(output_dir / 'chart_high_risk_reduction.png', dpi=300)
    plt.close()

    logging.info(f"Charts saved to {output_dir}")

def run_comparison():
    """Main entry point for CLI."""
    scenarios = [
        ('Baseline', config.OUTPUT_DATA_DIR / 'fio_baseline.csv'),
        ('Scenario 1 (Targeted)', config.OUTPUT_DATA_DIR / 'fio_scenario1.csv'),
        ('Scenario 2 (CWIS)', config.OUTPUT_DATA_DIR / 'fio_scenario2.csv'),
        ('Scenario 3 (Stone Town)', config.OUTPUT_DATA_DIR / 'fio_scenario3.csv')
    ]

    results = []
    for name, path in scenarios:
        res = analyze_scenario(name, path)
        if res:
            results.append(res)

    if not results:
        logging.error("No results found. Run pipelines first.")
        return

    summary = pd.DataFrame(results)
    
    # Print Table
    print("\n" + "="*80)
    print("SCENARIO COMPARISON SCORECARD")
    print("="*80)
    print(summary[['Scenario', 'Mean CFU', '% High Risk (>1000)', '% Moderate Risk (10-1000)', '% Low Risk (<10)']].to_string(index=False))
    print("="*80)
    
    # Generate Charts
    generate_charts(summary, config.OUTPUT_DATA_DIR)
