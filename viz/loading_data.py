"""
Chicago Interactive Map — City-Wide Data Layers
================================================
Creates a comprehensive Folium map with street network, parcels, zoning,
census tracts, and assessment overlays.

Usage:
    python -m viz.loading_data
"""

import folium
from folium.plugins import Draw

from src.config import (
    PARCEL_GEOJSON, ZONING_GEOJSON, ASSESSMENT_GEOJSON,
    INTERACTIVE_MAP, ensure_dirs,
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

    # Build map
    center = [chicago_polygon.centroid.y, chicago_polygon.centroid.x] if chicago_polygon else [41.88, -87.63]
    m = folium.Map(location=center, zoom_start=11, tiles="CartoDB positron")

    if chicago_gdf is not None:
        folium.GeoJson(
            chicago_gdf.__geo_interface__, name="Chicago Boundary",
            style_function=lambda f: {"color": "green", "weight": 2, "fillOpacity": 0},
        ).add_to(m)

    if roads is not None:
        folium.GeoJson(
            roads.__geo_interface__, name="Roads",
            style_function=lambda f: {"color": "red", "weight": 1},
        ).add_to(m)

    if parcels is not None:
        folium.GeoJson(
            parcels.iloc[:1000], name="Parcels (Sample)",
            style_function=lambda f: {"color": "purple", "weight": 0.5, "fillOpacity": 0.1},
            tooltip=folium.features.GeoJsonTooltip(fields=["PIN"], aliases=["Parcel ID:"]),
        ).add_to(m)

    if zoning is not None:
        folium.GeoJson(
            zoning, name="Zoning Districts",
            style_function=lambda f: {"fillColor": "orange", "color": "black", "weight": 1, "fillOpacity": 0.4},
        ).add_to(m)

    Draw(export=True, filename="edited_data.geojson").add_to(m)
    folium.LayerControl().add_to(m)

    m.save(str(INTERACTIVE_MAP))
    print(f"\nSaved: {INTERACTIVE_MAP}")


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
