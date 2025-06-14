"""Run BEST-Z nitrogen model for all scenarios."""

import logging
import webbrowser
from pathlib import Path

import matplotlib.pyplot as plt
import folium
from folium.plugins import Fullscreen

from . import config, ingest, preprocess, n_load

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def run_scenario(name: str, scenario: dict) -> None:
    """Execute one scenario."""
    logging.info('Running scenario %s', name)
    table_dir = config.OUTPUT_DIR / 'tables' / name
    map_png = config.OUTPUT_DIR / 'maps' / f'{name}.png'
    html_path = config.OUTPUT_DIR / 'html' / f'{name}.html'
    geojson_path = config.OUTPUT_DIR / 'geojson' / f'{name}.geojson'

    for d in [table_dir, map_png.parent, html_path.parent, geojson_path.parent]:
        d.mkdir(parents=True, exist_ok=True)

    hh = preprocess.clean_households()
    ingest.write_csv(hh, table_dir / 'households_clean.csv')

    pop = preprocess.group_population(hh)
    pop = preprocess.add_removal_efficiency(pop)
    # Debug: print toilet_type_id values missing removal efficiency
    missing_eff = pop[pop['nitrogen_removal_efficiency'].isna()]['toilet_type_id'].unique()
    if len(missing_eff) > 0:
        print('Missing removal efficiency for toilet_type_id:', missing_eff)
    else:
        print('All toilet_type_id values have removal efficiency.')
    scenario_df = n_load.apply_scenario(pop, scenario)
    ingest.write_csv(scenario_df, table_dir / 'pop_toilet_nload.csv')

    ward = n_load.aggregate_ward(scenario_df)
    ingest.write_csv(ward, table_dir / 'ward_total_n_load.csv')

    gdf = preprocess.attach_geometry(ward)
    ingest.write_geojson(gdf[['ward_name', 'geometry', 'ward_total_n_load_kg']], geojson_path)

    gdf.plot(column='ward_total_n_load_kg', cmap='YlOrRd', legend=True, figsize=(10, 8))
    plt.axis('off')
    plt.title(f'Annual Nitrogen Load ({name})')
    plt.tight_layout()
    plt.savefig(map_png, dpi=300)
    plt.close()

    if gdf.crs and gdf.crs.to_string() != 'EPSG:4326':
        gdf = gdf.to_crs(epsg=4326)
    m = folium.Map(location=[-6.1659, 39.2026], zoom_start=10, control_scale=True)
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap', overlay=False).add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Esri Satellite', overlay=False).add_to(m)
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
        name='Nitrogen Load'
    ).add_to(m)
    # Add popups for ward names
    folium.GeoJson(
        gdf,
        name='Ward Names',
        tooltip=folium.GeoJsonTooltip(
            fields=['ward_name', 'ward_total_n_load_kg', 'H_DISTRICT_NAME', 'reg_name'],
            aliases=['Ward:', 'N Load (kg):', 'District:', 'Region:']
        ),
        popup=folium.GeoJsonPopup(fields=['ward_name'], aliases=['Ward:'])
    ).add_to(m)
    Fullscreen().add_to(m)
    folium.LayerControl().add_to(m)
    m.save(html_path)
    webbrowser.open(html_path.as_uri())
    logging.info('Scenario %s completed', name)


def main() -> None:
    for name, scenario in config.SCENARIOS.items():
        run_scenario(name, scenario)


if __name__ == '__main__':
    main()
