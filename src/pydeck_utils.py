"""
PyDeck Shared Utilities
========================
Common helpers for building PyDeck (deck.gl) maps across the project.
Replaces the former Folium-based map generation pattern.

All standalone HTML maps (in ``maps/``) now use PyDeck instead of Folium.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pydeck as pdk


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# CARTO Positron basemap (same as the site's Deck.gl TileLayer)
CARTO_POSITRON = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"

# Chicago centre — (lat, lon) for PyDeck ViewState
CHICAGO_LAT = 41.8781
CHICAGO_LNG = -87.6298


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def hex_to_rgba(hex_color: str, alpha: int = 200) -> list[int]:
    """Convert a hex color string (#RRGGBB or shorthand) to an [R, G, B, A] list."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [alpha]


def rgba_column(gdf, color_fn, col_name: str = "rgba"):
    """
    Add an ``[R, G, B, A]`` list column to *gdf* by applying *color_fn*
    to each row.  *color_fn* receives a ``pd.Series`` (one row) and must
    return a 4-element list.

    This pre-computes colours so PyDeck can reference the column directly
    via ``get_fill_color='rgba'`` instead of using a JS accessor.
    """
    gdf = gdf.copy()
    gdf[col_name] = gdf.apply(color_fn, axis=1)
    return gdf


# ---------------------------------------------------------------------------
# Deck builder
# ---------------------------------------------------------------------------

def create_deck(
    layers: Sequence[pdk.Layer],
    *,
    center: tuple[float, float] = (CHICAGO_LAT, CHICAGO_LNG),
    zoom: int | float = 11,
    tooltip_html: str | None = None,
    tooltip_style: dict | None = None,
    description: str | None = None,
    map_style: str = CARTO_POSITRON,
) -> pdk.Deck:
    """
    Construct a ``pdk.Deck`` with sensible defaults.

    Parameters
    ----------
    layers : sequence of pdk.Layer
        One or more PyDeck layers.
    center : (lat, lon)
        Map centre.  Note: PyDeck ViewState takes lat/lon, not lon/lat.
    zoom : number
        Initial zoom level.
    tooltip_html : str, optional
        HTML template for hover/pick tooltips.  Use ``{property}`` for
        feature property interpolation (PyDeck syntax).
    tooltip_style : dict, optional
        CSS dict applied to the tooltip container.
    description : str, optional
        HTML injected below the map canvas (useful for legends).
    map_style : str
        Mapbox/MapLibre style URL.
    """
    tooltip = None
    if tooltip_html:
        tooltip = {
            "html": tooltip_html,
            "style": tooltip_style or {
                "backgroundColor": "white",
                "color": "#222",
                "fontSize": "13px",
                "padding": "8px 12px",
                "borderRadius": "6px",
                "boxShadow": "0 2px 8px rgba(0,0,0,.15)",
            },
        }

    view_state = pdk.ViewState(
        latitude=center[0],
        longitude=center[1],
        zoom=zoom,
        pitch=0,
        bearing=0,
    )

    return pdk.Deck(
        layers=list(layers),
        initial_view_state=view_state,
        map_style=map_style,
        tooltip=tooltip,  # type: ignore[arg-type]  # pdk stubs say bool, but dict is valid at runtime
        description=description,
    )


def save_map(deck: pdk.Deck, output_path: str | Path, *, title: str = "Map") -> Path:
    """Save *deck* as a self-contained HTML file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    deck.to_html(str(output_path), notebook_display=False, open_browser=False)
    print(f"Saved map: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Common layer factories
# ---------------------------------------------------------------------------

def geojson_fill_layer(
    layer_id: str,
    data,
    *,
    get_fill_color: str | list = "rgba",
    get_line_color: list | None = None,
    line_width_min_pixels: float = 0.5,
    opacity: float = 1.0,
    pickable: bool = True,
    auto_highlight: bool = True,
    stroked: bool = True,
) -> pdk.Layer:
    """Create a GeoJsonLayer for polygon data with fill + outline."""
    return pdk.Layer(
        "GeoJsonLayer",
        id=layer_id,
        data=data,
        pickable=pickable,
        stroked=stroked,
        filled=True,
        extruded=False,
        get_fill_color=get_fill_color,
        get_line_color=get_line_color or [0, 0, 0, 40],
        line_width_min_pixels=line_width_min_pixels,
        opacity=opacity,
        auto_highlight=auto_highlight,
        highlight_color=[255, 255, 0, 128],
    )


def scatterplot_layer(
    layer_id: str,
    data,
    *,
    get_position: str = "[longitude, latitude]",
    get_fill_color: str | list = "rgba",
    get_radius: int | str = 60,
    radius_min_pixels: int = 3,
    radius_max_pixels: int = 15,
    pickable: bool = True,
) -> pdk.Layer:
    """Create a ScatterplotLayer for point data."""
    return pdk.Layer(
        "ScatterplotLayer",
        id=layer_id,
        data=data,
        get_position=get_position,
        get_fill_color=get_fill_color,
        get_radius=get_radius,
        radius_min_pixels=radius_min_pixels,
        radius_max_pixels=radius_max_pixels,
        get_line_color=[255, 255, 255, 200],
        line_width_min_pixels=1,
        stroked=True,
        pickable=pickable,
        auto_highlight=True,
        highlight_color=[255, 255, 0, 128],
    )


def legend_html(title: str, items: list[tuple[str, str]], footer: str = "") -> str:
    """
    Generate an HTML legend block for injection via ``pdk.Deck(description=...)``.

    Parameters
    ----------
    title : str
        Legend heading.
    items : list of (color_hex, label)
        Each entry is a colour swatch + label.
    footer : str, optional
        Extra text below the legend entries.
    """
    rows = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0">'
        f'<span style="display:inline-block;width:14px;height:14px;border-radius:3px;'
        f'background:{color};border:1px solid #999"></span>'
        f'<span>{label}</span></div>'
        for color, label in items
    )
    return (
        f'<div style="position:fixed;bottom:30px;right:30px;background:#fff;'
        f'padding:12px 16px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,.15);'
        f'font-size:13px;z-index:9999;max-width:260px">'
        f'<div style="font-weight:700;margin-bottom:6px">{title}</div>'
        f'{rows}'
        f'{f"<div style=margin-top:6px;font-size:11px;color:#666>{footer}</div>" if footer else ""}'
        f'</div>'
    )
