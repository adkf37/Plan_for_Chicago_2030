"""
Chicago Interactive Map — City-Wide Data Layers
================================================
Creates a comprehensive PyDeck map with street network, parcels, zoning,
census tracts, and assessment overlays.

Usage:
    python -m viz.loading_data
"""

from src.config import (
    PARCEL_GEOJSON, ZONING_GEOJSON, ASSESSMENT_GEOJSON,
    INTERACTIVE_MAP, ensure_dirs,
)
from src.pydeck_utils import (
    create_deck, save_map, geojson_fill_layer,
    legend_html, hex_to_rgba,
)


def main():
    ensure_dirs()

    try:
        import osmnx as ox
    except ImportError:
        print("WARNING: osmnx not installed — street network will be skipped.")
        ox = None

    try:
        import geopandas as gpd
    except ImportError:
        print("ERROR: geopandas required. pip install geopandas")
        return

    city = "Chicago, Illinois, USA"

    # Fetch boundary
    print("Fetching Chicago boundary...")
    chicago_gdf = ox.geocode_to_gdf(city) if ox else None
    chicago_polygon = chicago_gdf.geometry.iloc[0] if chicago_gdf is not None else None

    # Fetch street network
    roads = None
    if ox:
        print("Fetching street network...")
        G = ox.graph_from_place(city, network_type="drive")
        roads = ox.graph_to_gdfs(G, nodes=False)

    # Load local datasets
    parcels = _load_geojson(gpd, PARCEL_GEOJSON, "Parcel")
    zoning = _load_geojson(gpd, ZONING_GEOJSON, "Zoning")
    assessment_df = _load_geojson(gpd, ASSESSMENT_GEOJSON, "Assessment")

    # Build map layers
    center = (chicago_polygon.centroid.y, chicago_polygon.centroid.x) if chicago_polygon else (41.88, -87.63)
    layers = []

    if chicago_gdf is not None:
        chicago_gdf["rgba"] = [[0, 128, 0, 0]] * len(chicago_gdf)
        layers.append(geojson_fill_layer(
            "boundary",
            chicago_gdf,
            get_fill_color=[0, 128, 0, 0],
            get_line_color=[0, 128, 0, 200],
            line_width_min_pixels=2,
            pickable=False,
        ))

    if roads is not None:
        roads = roads.reset_index(drop=True)
        layers.append(geojson_fill_layer(
            "roads",
            roads,
            get_fill_color=[255, 0, 0, 0],
            get_line_color=[255, 0, 0, 130],
            line_width_min_pixels=1,
            pickable=False,
        ))

    if parcels is not None:
        sample = parcels.iloc[:1000].copy()
        sample["rgba"] = [[128, 0, 128, 25]] * len(sample)
        layers.append(geojson_fill_layer(
            "parcels-sample",
            sample,
            get_fill_color="rgba",
            get_line_color=[128, 0, 128, 80],
            line_width_min_pixels=0.5,
        ))

    if zoning is not None:
        zoning["rgba"] = [[255, 165, 0, 100]] * len(zoning)
        layers.append(geojson_fill_layer(
            "zoning-districts",
            zoning,
            get_fill_color="rgba",
            get_line_color=[0, 0, 0, 130],
            line_width_min_pixels=1,
        ))

    legend_desc = legend_html(
        "City-Wide Layers",
        [
            ("#008000", "Chicago Boundary"),
            ("#ff0000", "Roads"),
            ("#800080", "Parcels (sample)"),
            ("#ffa500", "Zoning Districts"),
        ],
        footer="Note: polygon draw tool removed in Deck.gl migration.",
    )

    deck = create_deck(
        layers,
        center=center,
        zoom=11,
        tooltip_html="<b>{PIN}</b>" if parcels is not None else None,
        description=legend_desc,
    )
    save_map(deck, INTERACTIVE_MAP)


def _load_geojson(gpd, path, label):
    """Load a GeoJSON file, returning None on failure."""
    print(f"Loading {label} data from '{path}'...")
    try:
        gdf = gpd.read_file(path).to_crs(epsg=4326)
        print(f"  {label} data loaded ({len(gdf)} features).")
        return gdf
    except Exception as e:
        print(f"  Could not load {label}: {e}")
        return None


if __name__ == "__main__":
    main()
