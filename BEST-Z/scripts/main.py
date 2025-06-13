"""Run BEST-Z nitrogen model and generate maps."""

import argparse
import logging
import webbrowser
from pathlib import Path

import matplotlib.pyplot as plt
import folium
from folium.plugins import Fullscreen

from . import config, ingest, preprocess, n_load

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def compute_scenario_data(name: str, scenario: dict) -> folium.GeoJson:
    """Return GeoDataFrame for a scenario after writing outputs."""
    logging.info('Running scenario %s', name)
    table_dir = config.OUTPUT_DIR / 'tables' / name
    geojson_path = config.OUTPUT_DIR / 'geojson' / f'{name}.geojson'

    for d in [table_dir, geojson_path.parent]:
        d.mkdir(parents=True, exist_ok=True)

    hh = preprocess.clean_households()
    ingest.write_csv(hh, table_dir / 'households_clean.csv')

    pop = preprocess.group_population(hh)
    pop = preprocess.add_removal_efficiency(pop)
    scenario_df = n_load.apply_scenario(pop, scenario)
    ingest.write_csv(scenario_df, table_dir / 'pop_toilet_nload.csv')

    ward = n_load.aggregate_ward(scenario_df)
    ingest.write_csv(ward, table_dir / 'ward_total_n_load.csv')

    gdf = preprocess.attach_geometry(ward)
    ingest.write_geojson(gdf[['ward_name', 'geometry', 'ward_total_n_load_kg']], geojson_path)
    return gdf



def run_scenario(name: str, scenario: dict, map_obj: folium.Map | None = None) -> None:
    """Execute one scenario and optionally add it to ``map_obj``."""
    map_png = config.OUTPUT_DIR / 'maps' / f'{name}.png'
    html_path = config.OUTPUT_DIR / 'html' / f'{name}.html'

    for d in [map_png.parent, html_path.parent]:
        d.mkdir(parents=True, exist_ok=True)

    gdf = compute_scenario_data(name, scenario)

    gdf.plot(column='ward_total_n_load_kg', cmap='YlOrRd', legend=True, figsize=(10, 8))
    plt.axis('off')
    plt.title(f'Annual Nitrogen Load ({name})')
    plt.tight_layout()
    plt.savefig(map_png, dpi=300)
    plt.close()

    if gdf.crs and gdf.crs.to_string() != 'EPSG:4326':
        gdf = gdf.to_crs(epsg=4326)

    if map_obj is None:
        m = folium.Map(location=[-6.1659, 39.2026], zoom_start=10, control_scale=True)
        folium.TileLayer('OpenStreetMap', name='OpenStreetMap', overlay=False).add_to(m)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', name='Esri Satellite', overlay=False).add_to(m)
        target_map = m
    else:
        target_map = map_obj

    folium.Choropleth(
        geo_data=gdf,
        data=gdf,
        columns=['ward_name', 'ward_total_n_load_kg'],
        key_on='feature.properties.ward_name',
        fill_color='YlOrRd',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Annual Nitrogen Load (kg)',
        nan_fill_color='white',
        name=name
    ).add_to(target_map)

    if map_obj is None:
        Fullscreen().add_to(target_map)
        folium.LayerControl().add_to(target_map)
        target_map.save(html_path)
        webbrowser.open(html_path.as_uri())
    logging.info('Scenario %s completed', name)


def run_combined_map() -> None:
    """Run all configured scenarios and output one HTML map."""
    html_path = config.OUTPUT_DIR / 'html' / 'combined.html'
    html_path.parent.mkdir(parents=True, exist_ok=True)

    m = folium.Map(location=[-6.1659, 39.2026], zoom_start=10, control_scale=True)
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap', overlay=False).add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Esri Satellite', overlay=False).add_to(m)

    for name, scenario in config.SCENARIOS.items():
        run_scenario(name, scenario, map_obj=m)

    Fullscreen().add_to(m)
    folium.LayerControl().add_to(m)
    m.save(html_path)
    webbrowser.open(html_path.as_uri())


def main() -> None:
    parser = argparse.ArgumentParser(description='Run BEST-Z nitrogen load model')
    parser.add_argument('--combined', action='store_true', help='combine all scenarios into one map')
    parser.add_argument('--pop_factor', type=float, help='population scaling factor')
    parser.add_argument('--nre_override', action='append', help='override removal efficiency as TOILET=VALUE')
    parser.add_argument('--scenario', help='name of predefined scenario to run')
    args = parser.parse_args()

    if args.combined:
        run_combined_map()
        return

    if args.pop_factor or args.nre_override:
        overrides = {}
        if args.nre_override:
            for ov in args.nre_override:
                if '=' in ov:
                    key, val = ov.split('=', 1)
                    try:
                        overrides[key] = float(val)
                    except ValueError:
                        logging.warning('Invalid override %s', ov)
        scenario = {
            'pop_factor': args.pop_factor if args.pop_factor else 1.0,
            'nre_override': overrides,
        }
        run_scenario('custom', scenario)
        return

    if args.scenario:
        scenario = config.SCENARIOS.get(args.scenario)
        if scenario is None:
            logging.error('Scenario %s not found', args.scenario)
            return
        run_scenario(args.scenario, scenario)
        return

    for name, scenario in config.SCENARIOS.items():
        run_scenario(name, scenario)


if __name__ == '__main__':
    main()
