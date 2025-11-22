import pandas as pd
import numpy as np

def analyze_scenario(name, path):
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        print(f"File not found: {path}")
        return None

    # Filter for private wells (as they are the main focus of the report)
    # The report mentions 18,916 private wells.
    private = df[df['borehole_type'] == 'private']
    
    # Metrics
    median_conc = private['concentration_CFU_per_100mL'].median()
    mean_conc = private['concentration_CFU_per_100mL'].mean()
    
    # Risk Categories
    # > 1000 CFU (High Risk)
    high_risk = (private['concentration_CFU_per_100mL'] > 1000).mean() * 100
    # > 100 CFU (Significant Risk)
    med_risk = (private['concentration_CFU_per_100mL'] > 100).mean() * 100
    
    return {
        'Scenario': name,
        'Median CFU': median_conc,
        'Mean CFU': mean_conc,
        '% > 1000 CFU': high_risk,
        '% > 100 CFU': med_risk,
        'Count': len(private)
    }

scenarios = [
    ('Baseline', 'data/output/fio_baseline.csv'),
    ('Scenario 1 (Targeted)', 'data/output/fio_scenario1.csv'),
    ('Scenario 2 (CWIS)', 'data/output/fio_scenario2.csv'),
    ('Scenario 3 (Stone Town)', 'data/output/fio_scenario3.csv')
]

results = []
for name, path in scenarios:
    res = analyze_scenario(name, path)
    if res:
        results.append(res)

summary = pd.DataFrame(results)
print(summary.to_string(index=False))

# Calculate Reductions
baseline = summary.iloc[0]
print("\n--- Reductions vs Baseline ---")
for i in range(1, len(summary)):
    scen = summary.iloc[i]
    red_median = (baseline['Median CFU'] - scen['Median CFU']) / baseline['Median CFU'] * 100
    red_high_risk = (baseline['% > 1000 CFU'] - scen['% > 1000 CFU']) / baseline['% > 1000 CFU'] * 100
    print(f"{scen['Scenario']}:")
    print(f"  Median CFU Reduction: {red_median:.1f}%")
    print(f"  High Risk (>1000) Reduction: {red_high_risk:.1f}%")
