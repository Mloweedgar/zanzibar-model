#!/usr/bin/env python3
"""FIO Layered Model CLI - Command Line Interface.

This module provides a command-line interface for the FIO layered model
following the existing repository patterns.
"""

import sys
import logging
from pathlib import Path
from typing import Optional
import json

# Handle both relative and absolute imports
try:
    from . import config
    from . import ingest
    from . import fio_pipeline
except ImportError:
    # Fallback for direct execution
    import config
    import ingest
    import fio_pipeline

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def load_yaml_config(path: Path) -> dict:
    """Load YAML configuration file."""
    try:
        import yaml
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    except ImportError:
        logging.error("PyYAML not available, please install: pip install pyyaml")
        raise
    except Exception as e:
        logging.error(f"Failed to load config {path}: {e}")
        raise


def load_config(path: Optional[Path]) -> dict:
    """Load configuration from file or use defaults."""
    if path is None:
        logging.info("No config file provided, using defaults")
        return {
            'defaults': config.FIO_LAYERED_DEFAULTS.copy(),
            'mapping': config.FIO_MAPPING_CONFIG.copy()
        }
    
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    suffix = path.suffix.lower()
    if suffix == '.yaml' or suffix == '.yml':
        return load_yaml_config(path)
    elif suffix == '.json':
        with open(path, 'r') as f:
            return json.load(f)
    else:
        raise ValueError(f"Unsupported config format: {suffix}")


def fio_compute(households_path: Path, 
                receptors_path: Optional[Path] = None,
                mapping_path: Optional[Path] = None,
                config_path: Optional[Path] = None,
                output_path: Path = Path("concentrations.csv"),
                contributions_path: Optional[Path] = None,
                verbose: bool = False) -> None:
    """
    Compute FIO concentrations using the three-layer model.
    
    Args:
        households_path: Path to households.csv (required)
        receptors_path: Path to receptors.csv (optional, creates synthetic if missing)
        mapping_path: Path to mapping.csv (optional, auto-generates if missing)
        config_path: Path to config file (optional, uses defaults if missing)
        output_path: Path for concentrations output CSV
        contributions_path: Path for household contributions CSV (optional)
        verbose: Enable verbose logging
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logging.info("🌊 Starting FIO Layered Model computation")
    
    # Load configuration
    try:
        config_data = load_config(config_path)
        defaults = config_data.get('defaults', config.FIO_LAYERED_DEFAULTS)
        mapping_config = config_data.get('mapping', config.FIO_MAPPING_CONFIG)
        
        # Update global mapping config
        config.FIO_MAPPING_CONFIG.update(mapping_config)
        
        logging.info(f"Configuration: {len(defaults)} parameters loaded")
        if config_path:
            logging.info(f"  Config file: {config_path}")
        
    except Exception as e:
        logging.error(f"Failed to load configuration: {e}")
        return
    
    # Load input data
    try:
        logging.info("📊 Loading input data")
        
        # Load households (required)
        if not households_path.exists():
            raise FileNotFoundError(f"Households file not found: {households_path}")
        households = fio_pipeline.load_households_csv(households_path, defaults)
        
        # Load receptors (optional)
        receptors = fio_pipeline.load_receptors_csv(receptors_path, defaults)
        
        # Load or generate mapping
        mapping = fio_pipeline.load_mapping_csv(mapping_path, households, receptors, defaults)
        
        logging.info(f"  Households: {len(households)}")
        logging.info(f"  Receptors: {len(receptors)}")
        logging.info(f"  Mappings: {len(mapping)}")
        
    except Exception as e:
        logging.error(f"Failed to load input data: {e}")
        return
    
    # Run computation
    try:
        logging.info("🧮 Computing FIO concentrations")
        concentrations, contributions = fio_pipeline.compute_fio_layered(
            households, receptors, mapping, defaults
        )
        
        # Log summary
        total_households = contributions['household_id'].nunique()
        total_L = contributions['L'].sum()
        total_L_reaching = contributions['L_reaching'].sum()
        
        logging.info(f"  Processed {total_households} households")
        logging.info(f"  Total source load: {total_L:.2e} CFU/day")
        logging.info(f"  Total reaching receptors: {total_L_reaching:.2e} CFU/day")
        
    except Exception as e:
        logging.error(f"Computation failed: {e}")
        return
    
    # Write outputs
    try:
        logging.info("💾 Writing outputs")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write concentrations (main output)
        ingest.write_csv(concentrations, output_path)
        logging.info(f"  Concentrations: {output_path}")
        
        # Write contributions (optional)
        if contributions_path:
            contributions_path.parent.mkdir(parents=True, exist_ok=True)
            ingest.write_csv(contributions, contributions_path)
            logging.info(f"  Contributions: {contributions_path}")
        
        # Log final results summary
        unit = "CFU/100mL" if defaults.get('output_unit') == 'CFU_100mL' else "CFU/L"
        logging.info("📈 Results summary:")
        for _, row in concentrations.iterrows():
            logging.info(f"  {row['receptor_id']}: {row['C']:.1f} {unit} "
                        f"(from {row['total_households']} households)")
        
    except Exception as e:
        logging.error(f"Failed to write outputs: {e}")
        return
    
    logging.info("✅ FIO computation completed successfully")


def print_help():
    """Print CLI help message."""
    help_text = """
FIO Layered Model CLI

USAGE:
    python fio_cli.py <command> [arguments]

COMMANDS:
    compute   - Run FIO concentration calculations

COMPUTE ARGUMENTS:
    --households <path>      Path to households.csv (required)
    --receptors <path>       Path to receptors.csv (optional)
    --mapping <path>         Path to mapping.csv (optional)
    --config <path>          Path to config file (optional)
    --out <path>             Output path for concentrations.csv (default: concentrations.csv)
    --contributions <path>   Output path for household_contributions.csv (optional)
    --verbose               Enable verbose logging

EXAMPLES:
    # Basic usage with minimal data
    python fio_cli.py compute --households households.csv
    
    # Full usage with all inputs
    python fio_cli.py compute \\
        --households data/households.csv \\
        --receptors data/receptors.csv \\
        --mapping data/mapping.csv \\
        --config data/params.yaml \\
        --out outputs/concentrations.csv \\
        --contributions outputs/household_contributions.csv \\
        --verbose

INPUT FILE FORMATS:
    households.csv: household_id,lat,lon,pop,efio,eta,lrv
    receptors.csv:  receptor_id,lat,lon,Q,Q_m3s
    mapping.csv:    household_id,receptor_id,t,d
    params.yaml:    YAML config with defaults and mapping sections

For more information, see the documentation and examples in data_examples/
"""
    print(help_text)


def main():
    """Main CLI entry point."""
    args = sys.argv[1:]
    
    if not args or args[0] in ['-h', '--help', 'help']:
        print_help()
        return
    
    command = args[0]
    
    if command == 'compute':
        # Parse compute arguments
        kwargs = {}
        i = 1
        while i < len(args):
            arg = args[i]
            
            if arg == '--households' and i + 1 < len(args):
                kwargs['households_path'] = Path(args[i + 1])
                i += 2
            elif arg == '--receptors' and i + 1 < len(args):
                kwargs['receptors_path'] = Path(args[i + 1])
                i += 2
            elif arg == '--mapping' and i + 1 < len(args):
                kwargs['mapping_path'] = Path(args[i + 1])
                i += 2
            elif arg == '--config' and i + 1 < len(args):
                kwargs['config_path'] = Path(args[i + 1])
                i += 2
            elif arg == '--out' and i + 1 < len(args):
                kwargs['output_path'] = Path(args[i + 1])
                i += 2
            elif arg == '--contributions' and i + 1 < len(args):
                kwargs['contributions_path'] = Path(args[i + 1])
                i += 2
            elif arg == '--verbose':
                kwargs['verbose'] = True
                i += 1
            else:
                print(f"Unknown argument: {arg}")
                print_help()
                sys.exit(1)
        
        # Validate required arguments
        if 'households_path' not in kwargs:
            print("Error: --households is required")
            print_help()
            sys.exit(1)
        
        try:
            fio_compute(**kwargs)
        except Exception as e:
            logging.error(f"Command failed: {e}")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()