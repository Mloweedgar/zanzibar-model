# BEST-Z Nitrogen Load Model

Automated workflows to estimate annual nitrogen load from sanitation in Zanzibar. Run all scenarios sequentially:

```bash
python scripts/main.py
```

Outputs are saved in the `outputs/` directory with tables, maps, html, and geojson per scenario.

To create a single interactive map containing all scenarios use:

```bash
python scripts/main.py --combined
```

You can override parameters for a custom run:

```bash
python scripts/main.py --pop_factor 1.2 --nre_override flush_septic=0.7
```

## Installation

Install the required Python packages from the repository root:

```bash
pip install -r requirements.txt
```
