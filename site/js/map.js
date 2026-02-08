/**
 * Plan for Chicago 2030 — MapLibre GL JS Interactive Map
 * ======================================================
 * Loads optimised GeoJSON layers from site/data/, provides toggleable
 * overlays, parcel pop-ups, story-map guided tours, geocoding, and
 * before/after comparison support.
 */

/* global maplibregl */

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const DATA_BASE = "data/";          // relative to site/
const CHICAGO_CENTER = [-87.6298, 41.8781];
const INITIAL_ZOOM = 10.5;

// Layer definitions: id → { file, type, paint, ... }
const LAYER_DEFS = {
  zoning: {
    file: "zoning.geojson",
    sourceType: "geojson",
    layerType: "fill",
    paint: {
      "fill-color": ["coalesce", ["get", "zone_color"], "#808080"],
      "fill-opacity": 0.45,
    },
    outline: {
      "line-color": "#000",
      "line-width": 0.3,
    },
    label: "Current Zoning",
    defaultOn: true,
    swatch: "#00ff00",
  },
  proposed_zoning: {
    file: "proposed_zoning.geojson",
    sourceType: "geojson",
    layerType: "fill",
    paint: {
      "fill-color": [
        "case",
        ["==", ["get", "changed"], true], "#ff6600",
        "#aaaaaa",
      ],
      "fill-opacity": 0.5,
    },
    outline: {
      "line-color": "#333",
      "line-width": 0.3,
    },
    label: "Proposed Zoning",
    defaultOn: false,
    swatch: "#ff6600",
  },
  transit: {
    file: "transit_stations.geojson",
    sourceType: "geojson",
    layerType: "circle",
    paint: {
      "circle-radius": [
        "match", ["get", "station_type"],
        "CTA_L", 5,
        "Metra", 5,
        "Proposed", 4,
        4,
      ],
      "circle-color": [
        "match", ["get", "station_type"],
        "CTA_L", "#1f78b4",
        "Metra", "#33a02c",
        "Proposed", "#e31a1c",
        "#999",
      ],
      "circle-stroke-width": 1,
      "circle-stroke-color": "#fff",
    },
    label: "Transit Stations",
    defaultOn: true,
    swatch: "#1f78b4",
  },
  parcels: {
    file: "parcels.geojson",
    sourceType: "geojson",
    layerType: "fill",
    paint: {
      "fill-color": [
        "interpolate", ["linear"],
        ["coalesce", ["get", "tod_score"], 0],
        0, "#ffffcc",
        25, "#a1dab4",
        50, "#41b6c4",
        75, "#2c7fb8",
        100, "#253494",
      ],
      "fill-opacity": 0.55,
    },
    outline: {
      "line-color": "#555",
      "line-width": 0.2,
    },
    label: "Parcel Values / TOD",
    defaultOn: false,
    swatch: "#41b6c4",
  },
};

// Story-map tour stops
const TOUR_STOPS = [
  { name: "The Loop", center: [-87.6298, 41.8819], zoom: 14,
    desc: "Chicago's central business district — highest density zoning and transit access." },
  { name: "Ashland BRT Corridor", center: [-87.6668, 41.8673], zoom: 13.5,
    desc: "Proposed Ashland Ave BRT route — key north-south corridor for upzoning." },
  { name: "Red Line Extension", center: [-87.6250, 41.6923], zoom: 12.5,
    desc: "Planned CTA Red Line Extension south to 130th Street." },
  { name: "Pilsen / Circle Line", center: [-87.6560, 41.8565], zoom: 14,
    desc: "Pilsen neighbourhood — potential Circle Line infill station area." },
  { name: "Near South Side Study Area", center: [-87.623, 41.859], zoom: 15,
    desc: "Primary study area for property-value uplift modelling." },
];

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let map;
const loadedSources = new Set();

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------
function initMap() {
  map = new maplibregl.Map({
    container: "map",
    style: {
      version: 8,
      name: "Chicago 2030",
      sources: {
        "carto-positron": {
          type: "raster",
          tiles: [
            "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
            "https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
          ],
          tileSize: 256,
          attribution: '&copy; <a href="https://carto.com/">CARTO</a> | &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
        },
      },
      layers: [{
        id: "basemap",
        type: "raster",
        source: "carto-positron",
        minzoom: 0,
        maxzoom: 20,
      }],
    },
    center: CHICAGO_CENTER,
    zoom: INITIAL_ZOOM,
    attributionControl: true,
  });

  map.addControl(new maplibregl.NavigationControl(), "top-right");
  map.addControl(new maplibregl.ScaleControl({ maxWidth: 200 }), "bottom-right");

  map.on("load", () => {
    loadManifestAndLayers();
    wireUI();
  });
}

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------
async function loadManifestAndLayers() {
  let manifest;
  try {
    const resp = await fetch(DATA_BASE + "manifest.json");
    manifest = await resp.json();
  } catch {
    // No manifest — try loading all layers anyway
    manifest = {};
    for (const id of Object.keys(LAYER_DEFS)) manifest[id] = LAYER_DEFS[id].file;
  }

  for (const [id, def] of Object.entries(LAYER_DEFS)) {
    const filename = manifest[id] || def.file;
    if (!filename) continue;
    addLayerFromFile(id, DATA_BASE + filename, def);
  }
}

async function addLayerFromFile(id, url, def) {
  try {
    const resp = await fetch(url);
    if (!resp.ok) { console.warn(`Layer ${id}: ${resp.statusText}`); return; }
    const data = await resp.json();

    map.addSource(id, { type: "geojson", data });
    loadedSources.add(id);

    if (def.layerType === "fill") {
      map.addLayer({
        id: id + "-fill",
        type: "fill",
        source: id,
        paint: def.paint,
        layout: { visibility: def.defaultOn ? "visible" : "none" },
      });
      if (def.outline) {
        map.addLayer({
          id: id + "-outline",
          type: "line",
          source: id,
          paint: def.outline,
          layout: { visibility: def.defaultOn ? "visible" : "none" },
        });
      }
    } else {
      map.addLayer({
        id: id + "-pt",
        type: def.layerType,
        source: id,
        paint: def.paint,
        layout: { visibility: def.defaultOn ? "visible" : "none" },
      });
    }

    // Pop-ups
    const clickLayer = def.layerType === "fill" ? id + "-fill" : id + "-pt";
    map.on("click", clickLayer, (e) => showPopup(e, id));
    map.on("mouseenter", clickLayer, () => { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", clickLayer, () => { map.getCanvas().style.cursor = ""; });

    console.log(`Layer loaded: ${id}`);
  } catch (err) {
    console.warn(`Could not load layer ${id}:`, err);
  }
}

// ---------------------------------------------------------------------------
// Pop-ups
// ---------------------------------------------------------------------------
function showPopup(e, layerId) {
  const props = e.features[0].properties;
  let html = '<div class="popup-title">';

  if (layerId === "transit") {
    html += `${props.station_name || "Station"}</div>`;
    html += popupRow("Type", props.station_type);
  } else if (layerId === "parcels") {
    const pin = props.pin || props.PIN || props.pin14 || props.PIN14 || "—";
    html += `Parcel ${pin}</div>`;
    html += popupRow("Zone", props.zone_class || props.ZONE_CLASS);
    if (props.current_value) html += popupRow("Current Value", "$" + Number(props.current_value).toLocaleString());
    if (props.moderate_projected) html += popupRow("Projected Value", "$" + Number(props.moderate_projected).toLocaleString());
    if (props.moderate_uplift_pct) html += popupRow("Uplift", (props.moderate_uplift_pct * 100).toFixed(1) + "%");
    if (props.tod_score) html += popupRow("TOD Score", Number(props.tod_score).toFixed(0) + " / 100");
    if (props.transit_tier) html += popupRow("Transit Tier", props.transit_tier);
  } else if (layerId === "zoning" || layerId === "proposed_zoning") {
    const zc = props.ZONE_CLASS || props.zone_class || "—";
    html += `Zone ${zc}</div>`;
    if (props.zone_name) html += popupRow("Type", props.zone_name);
    if (props.proposed_zone) html += popupRow("Proposed", props.proposed_zone);
    if (props.changed !== undefined) html += popupRow("Changed", props.changed ? "Yes" : "No");
  } else {
    html += "Feature</div>";
  }

  new maplibregl.Popup({ maxWidth: "300px" })
    .setLngLat(e.lngLat)
    .setHTML(html)
    .addTo(map);
}

function popupRow(label, value) {
  return `<div class="popup-row"><span class="popup-label">${label}</span><span>${value ?? "—"}</span></div>`;
}

// ---------------------------------------------------------------------------
// UI wiring
// ---------------------------------------------------------------------------
function wireUI() {
  // Layer toggles
  document.querySelectorAll(".layer-toggle input").forEach((cb) => {
    cb.addEventListener("change", () => {
      const layerId = cb.dataset.layer;
      const vis = cb.checked ? "visible" : "none";
      setLayerVisibility(layerId, vis);
    });
  });

  // Tour buttons
  document.querySelectorAll(".tour-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const lng = parseFloat(btn.dataset.lng);
      const lat = parseFloat(btn.dataset.lat);
      const zoom = parseFloat(btn.dataset.zoom);
      map.flyTo({ center: [lng, lat], zoom, duration: 2000 });
    });
  });

  // Geocoder
  const geoInput = document.getElementById("geocoder-input");
  const geoBtn   = document.getElementById("geocoder-btn");
  if (geoBtn && geoInput) {
    const doGeocode = () => geocode(geoInput.value);
    geoBtn.addEventListener("click", doGeocode);
    geoInput.addEventListener("keydown", (e) => { if (e.key === "Enter") doGeocode(); });
  }

  // Sidebar toggle (mobile)
  const toggle = document.getElementById("sidebar-toggle");
  const sidebar = document.getElementById("sidebar");
  if (toggle && sidebar) {
    toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
  }

  // High-contrast toggle
  const hcBtn = document.getElementById("hc-toggle");
  if (hcBtn) {
    hcBtn.addEventListener("click", () => document.body.classList.toggle("high-contrast"));
  }

  // Before/after comparison toggle
  const compareCheck = document.getElementById("compare-mode");
  if (compareCheck) {
    compareCheck.addEventListener("change", () => {
      // Show both zoning + proposed_zoning when compare mode on
      if (compareCheck.checked) {
        setLayerVisibility("zoning", "visible");
        setLayerVisibility("proposed_zoning", "visible");
        document.getElementById("compare-container").style.display = "block";
      } else {
        setLayerVisibility("proposed_zoning", "none");
        document.getElementById("compare-container").style.display = "none";
      }
    });
  }
}

function setLayerVisibility(layerId, vis) {
  const suffixes = ["-fill", "-outline", "-pt"];
  for (const s of suffixes) {
    if (map.getLayer(layerId + s)) {
      map.setLayoutProperty(layerId + s, "visibility", vis);
    }
  }
}

// ---------------------------------------------------------------------------
// Geocoding (Nominatim)
// ---------------------------------------------------------------------------
async function geocode(query) {
  if (!query) return;
  const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query + ", Chicago, IL")}&limit=1`;
  try {
    const resp = await fetch(url, { headers: { "Accept-Language": "en" } });
    const results = await resp.json();
    if (results.length > 0) {
      const { lon, lat, display_name } = results[0];
      map.flyTo({ center: [parseFloat(lon), parseFloat(lat)], zoom: 16, duration: 1500 });
      new maplibregl.Popup()
        .setLngLat([parseFloat(lon), parseFloat(lat)])
        .setHTML(`<div class="popup-title">${display_name}</div>`)
        .addTo(map);
    } else {
      alert("Address not found. Try a different query.");
    }
  } catch (err) {
    console.error("Geocode error:", err);
  }
}

// ---------------------------------------------------------------------------
// Keyboard navigation helpers (accessibility)
// ---------------------------------------------------------------------------
document.addEventListener("keydown", (e) => {
  // Arrow keys pan the map when focused
  if (document.activeElement === document.getElementById("map")) {
    const PAN = 100;
    switch (e.key) {
      case "ArrowUp":    map.panBy([0, -PAN]); e.preventDefault(); break;
      case "ArrowDown":  map.panBy([0, PAN]);  e.preventDefault(); break;
      case "ArrowLeft":  map.panBy([-PAN, 0]); e.preventDefault(); break;
      case "ArrowRight": map.panBy([PAN, 0]);  e.preventDefault(); break;
      case "+": case "=":  map.zoomIn();  e.preventDefault(); break;
      case "-":            map.zoomOut(); e.preventDefault(); break;
    }
  }
});

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", initMap);
