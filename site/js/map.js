/**
 * Plan for Chicago 2030 — Deck.gl Interactive Map
 * ================================================
 * Loads optimised PMTiles (vector tiles) or GeoJSON layers from site/data/,
 * provides toggleable overlays, parcel pop-ups, story-map guided tours,
 * geocoding, and before/after comparison support.
 *
 * Uses deck.gl 9.x UMD bundle loaded via CDN.
 */

/* global deck, pmtiles */

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const DATA_BASE = "data/";
const CHICAGO_CENTER = [-87.6298, 41.8781];
const INITIAL_ZOOM = 10.5;

// Color helpers
function hexToRGBA(hex, alpha = 255) {
  hex = hex.replace("#", "");
  if (hex.length === 3) hex = hex.split("").map(c => c + c).join("");
  return [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16),
          parseInt(hex.slice(4, 6), 16), alpha];
}

// Chicago zoning color scheme — mirrors secondcityzoning.org / Chicago Zoning Map
// Colors keyed by zone_class prefix (RS, RT, RM, B, C, M, DX, PD, POS, T …)
function zoningCategory(zoneClass) {
  if (!zoneClass) return 'other';
  const c = zoneClass.toUpperCase();
  if (c.startsWith('RS'))                                                   return 'RS';
  if (c.startsWith('RTA') || c.startsWith('RT'))                           return 'RT';
  if (c.startsWith('RM')  || c.startsWith('RB'))                           return 'RM';
  if (c.startsWith('DX')  || c.startsWith('DC') ||
      c.startsWith('DR')  || c.startsWith('DS'))                           return 'D';
  if (c.startsWith('PMD'))                                                  return 'PMD';
  if (c.startsWith('PD'))                                                   return 'PD';
  if (c.startsWith('POS'))                                                  return 'POS';
  if (c.startsWith('B'))                                                    return 'B';
  if (c.startsWith('C'))                                                    return 'C';
  if (c.startsWith('M'))                                                    return 'M';
  if (c.startsWith('T'))                                                    return 'T';
  return 'other';
}

// RGBA values (R, G, B, A) — alpha 145 gives good polygon fill at default opacity
const ZONING_COLORS = {
  RS:    [253, 219,  72, 145],  // single-family: bright yellow
  RT:    [251, 169,  56, 145],  // two-flat / townhouse: amber
  RM:    [240, 126,  36, 145],  // multi-unit residential: deep orange
  D:     [155,  89, 182, 145],  // downtown mixed (DX/DC/DR/DS): purple
  B:     [232,  87,  87, 145],  // neighborhood business: coral
  C:     [192,  57,  43, 145],  // commercial: deep red
  M:     [127, 110, 170, 145],  // industrial / manufacturing: muted purple
  PMD:   [108,  52, 131, 145],  // planned manufacturing district: dark purple
  PD:    [180, 175, 210, 145],  // planned development: lavender
  POS:   [ 39, 174,  96, 145],  // parks / open space: green
  T:     [149, 165, 166, 130],  // transportation: gray
  other: [150, 150, 150, 100],  // fallback
};

// TOD score → YlGnBu 5-stop color ramp
const TOD_STOPS = [
  { v: 0,   c: [255, 255, 204] },
  { v: 25,  c: [161, 218, 180] },
  { v: 50,  c: [65,  182, 196] },
  { v: 75,  c: [44,  127, 184] },
  { v: 100, c: [37,   52, 148] },
];

function todScoreColor(score, alpha = 140) {
  if (score == null || isNaN(score)) return [200, 200, 200, 80];
  score = Math.max(0, Math.min(100, score));
  for (let i = 0; i < TOD_STOPS.length - 1; i++) {
    const a = TOD_STOPS[i], b = TOD_STOPS[i + 1];
    if (score <= b.v) {
      const t = (score - a.v) / (b.v - a.v);
      return [
        Math.round(a.c[0] + t * (b.c[0] - a.c[0])),
        Math.round(a.c[1] + t * (b.c[1] - a.c[1])),
        Math.round(a.c[2] + t * (b.c[2] - a.c[2])),
        alpha,
      ];
    }
  }
  return [...TOD_STOPS[TOD_STOPS.length - 1].c, alpha];
}

// Station type → color & radius
const STATION_COLORS = {
  CTA_L:    [31, 120, 180],
  Metra:    [51, 160, 44],
  Proposed: [227, 26, 28],
};
const STATION_RADII = { CTA_L: 80, Metra: 80, Proposed: 60 };

// Layer definitions — id → config
const LAYER_DEFS = {
  zoning: {
    file: "zoning.geojson",
    label: "Current Zoning",
    defaultOn: true,
    swatch: "#fddb48",
    layerType: "polygon",
    getFillColor: (d) => {
      const zc = (d.properties || d).zone_class;
      const cat = zoningCategory(zc);
      return ZONING_COLORS[cat] || ZONING_COLORS.other;
    },
    getLineColor: [30, 30, 30, 55],
    lineWidthMinPixels: 0.4,
  },
  proposed_zoning: {
    file: "proposed_zoning.geojson",
    label: "Proposed Zoning",
    defaultOn: false,
    swatch: "#ff6600",
    layerType: "polygon",
    getFillColor: (d) => {
      const changed = (d.properties || d).changed;
      return changed === true || changed === "true"
        ? [255, 102, 0, 128] : [170, 170, 170, 80];
    },
    getLineColor: [51, 51, 51, 50],
    lineWidthMinPixels: 0.3,
  },
  transit: {
    file: "transit_stations.geojson",
    label: "Transit Stations",
    defaultOn: true,
    swatch: "#1f78b4",
    layerType: "point",
    getFillColor: (d) => {
      const t = (d.properties || d).station_type;
      return [...(STATION_COLORS[t] || [153, 153, 153]), 220];
    },
    getRadius: (d) => {
      const t = (d.properties || d).station_type;
      return STATION_RADII[t] || 60;
    },
  },
  parcels: {
    file: "parcels.geojson",
    label: "TOD Opportunity Scores",
    defaultOn: false,
    swatch: "#41b6c4",
    layerType: "point",
    getFillColor: (d) => {
      const score = parseFloat((d.properties || d).tod_score) || 0;
      return todScoreColor(score, 180);
    },
    getRadius: 40,
  },
  transit_lines: {
    file: "transit_lines.geojson",
    label: "Transit Lines",
    defaultOn: true,
    swatch: "#c60c30",
    layerType: "line",
    getColor: (d) => {
      const hex = (d.properties || d).colour || "#888888";
      const type = (d.properties || d).line_type || "";
      // Metra lines slightly more transparent
      const alpha = type === "Metra" ? 180 : 230;
      return hexToRGBA(hex, alpha);
    },
    getWidth: (d) => {
      const type = (d.properties || d).line_type || "";
      return type === "Metra" ? 40 : 55;
    },
    widthUnits: "meters",
    widthMinPixels: 1.5,
  },
  metra_stations: {
    file: "metra_stations.geojson",
    label: "Metra Stations",
    defaultOn: true,
    swatch: "#2d6b37",
    layerType: "point",
    getFillColor: (d) => hexToRGBA((d.properties || d).colour || "#2d6b37", 220),
    getRadius: 120,
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
  { name: "Soldier Field Analysis", center: [-87.622, 41.859], zoom: 14.5,
    desc: "Soldier Field tear-down: comparing to the reference neighborhood." },
];

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let deckgl;
let manifest = {};
let layerData = {};        // id → GeoJSON FeatureCollection or URL for MVT
let layerVisible = {};     // id → boolean
let currentPopup = null;   // DOM element for active popup

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------
function initMap() {
  // Set initial visibility from defaults
  for (const [id, def] of Object.entries(LAYER_DEFS)) {
    layerVisible[id] = def.defaultOn;
  }

  deckgl = new deck.DeckGL({
    container: "map",
    initialViewState: {
      longitude: CHICAGO_CENTER[0],
      latitude: CHICAGO_CENTER[1],
      zoom: INITIAL_ZOOM,
      pitch: 0,
      bearing: 0,
    },
    controller: { keyboard: true, doubleClickZoom: true, touchRotate: true },
    layers: [],
    getTooltip: null,
    onClick: (info, event) => {
      if (info.layer && info.object) {
        showPopup(info);
      } else {
        closePopup();
      }
    },
    onViewStateChange: ({ viewState }) => {
      // Close popup on pan/zoom to keep it from dangling
      closePopup();
    },
  });

  // Load the CARTO Positron basemap as a TileLayer
  loadManifestAndLayers();
  wireUI();
}

// ---------------------------------------------------------------------------
// Basemap
// ---------------------------------------------------------------------------
function createBasemapLayer() {
  return new deck.TileLayer({
    id: "basemap",
    data: [
      "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
      "https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
      "https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
    ],
    minZoom: 0,
    maxZoom: 20,
    tileSize: 256,
    renderSubLayers: (props) => {
      const { boundingBox } = props.tile;
      return new deck.BitmapLayer(props, {
        data: null,
        image: props.data,
        bounds: [boundingBox[0][0], boundingBox[0][1], boundingBox[1][0], boundingBox[1][1]],
      });
    },
  });
}

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------
async function loadManifestAndLayers() {
  try {
    const resp = await fetch(DATA_BASE + "manifest.json");
    manifest = await resp.json();
  } catch {
    manifest = {};
    for (const id of Object.keys(LAYER_DEFS)) {
      manifest[id] = { file: LAYER_DEFS[id].file, sourceType: "geojson" };
    }
  }

  // Load each layer's data
  const promises = Object.entries(LAYER_DEFS).map(async ([id, def]) => {
    const info = manifest[id];
    if (!info) return;

    // Normalize old manifest format (string instead of object)
    const layerInfo = typeof info === "string" ? { file: info, sourceType: "geojson" } : info;

    if (layerInfo.sourceType === "vector") {
      // PMTiles — store the URL for MVTLayer
      layerData[id] = {
        type: "vector",
        url: DATA_BASE + layerInfo.file,
        sourceLayer: layerInfo.sourceLayer || id,
        geojsonFallback: layerInfo.geojsonFallback ? DATA_BASE + layerInfo.geojsonFallback : null,
      };
    } else {
      // GeoJSON — fetch and store
      try {
        const resp = await fetch(DATA_BASE + layerInfo.file);
        if (!resp.ok) { console.warn(`Layer ${id}: ${resp.statusText}`); return; }
        layerData[id] = { type: "geojson", data: await resp.json() };
      } catch (err) {
        console.warn(`Could not load layer ${id}:`, err);
      }
    }
    console.log(`Layer loaded: ${id} (${layerData[id]?.type})`);
  });

  await Promise.all(promises);
  rebuildLayers();
}

// ---------------------------------------------------------------------------
// Layer construction
// ---------------------------------------------------------------------------
function rebuildLayers() {
  const layers = [createBasemapLayer()];

  for (const [id, def] of Object.entries(LAYER_DEFS)) {
    const info = layerData[id];
    if (!info) continue;
    const visible = layerVisible[id];

    if (def.layerType === "line") {
      // PathLayer for transit lines (LineString / MultiLineString)
      if (info.type === "geojson" && info.data) {
        const pathFeatures = [];
        for (const feat of info.data.features) {
          const geomType = feat.geometry && feat.geometry.type;
          if (geomType === "LineString") {
            pathFeatures.push({ path: feat.geometry.coordinates, properties: feat.properties });
          } else if (geomType === "MultiLineString") {
            for (const seg of feat.geometry.coordinates) {
              pathFeatures.push({ path: seg, properties: feat.properties });
            }
          }
        }
        layers.push(new deck.PathLayer({
          id: id + "-lines",
          data: pathFeatures,
          visible,
          pickable: true,
          getPath: d => d.path,
          getColor: d => def.getColor({ properties: d.properties }),
          getWidth: d => def.getWidth({ properties: d.properties }),
          widthUnits: def.widthUnits || "meters",
          widthMinPixels: def.widthMinPixels || 2,
          capRounded: true,
          jointRounded: true,
          autoHighlight: true,
          highlightColor: [255, 255, 100, 200],
        }));
      }
    } else if (def.layerType === "point") {
      // ScatterplotLayer for transit stations
      if (info.type === "geojson" && info.data) {
        layers.push(new deck.GeoJsonLayer({
          id: id + "-pt",
          data: info.data,
          visible,
          pickable: true,
          pointType: "circle",
          getFillColor: def.getFillColor,
          getPointRadius: def.getRadius || 60,
          pointRadiusUnits: "meters",
          pointRadiusMinPixels: 3,
          pointRadiusMaxPixels: 12,
          getLineColor: [255, 255, 255, 200],
          lineWidthMinPixels: 1,
          stroked: true,
          autoHighlight: true,
          highlightColor: [255, 255, 0, 128],
        }));
      }
    } else {
      // Polygon layers — prefer MVT if available
      if (info.type === "vector") {
        layers.push(new deck.MVTLayer({
          id: id + "-fill",
          data: info.url,
          visible,
          pickable: true,
          getFillColor: def.getFillColor,
          getLineColor: def.getLineColor || [0, 0, 0, 30],
          lineWidthMinPixels: def.lineWidthMinPixels || 0.3,
          autoHighlight: true,
          highlightColor: [255, 255, 0, 80],
          // Use pmtiles protocol loader if URL ends in .pmtiles
          ...(info.url.endsWith(".pmtiles") ? { loaders: [pmtiles.PMTilesLoader] } : {}),
        }));
      } else if (info.data) {
        layers.push(new deck.GeoJsonLayer({
          id: id + "-fill",
          data: info.data,
          visible,
          pickable: true,
          getFillColor: def.getFillColor,
          getLineColor: def.getLineColor || [0, 0, 0, 30],
          lineWidthMinPixels: def.lineWidthMinPixels || 0.3,
          stroked: true,
          autoHighlight: true,
          highlightColor: [255, 255, 0, 80],
        }));
      }
    }
  }

  deckgl.setProps({ layers });
}

// ---------------------------------------------------------------------------
// Pop-ups
// ---------------------------------------------------------------------------
function showPopup(info) {
  closePopup();

  const props = info.object.properties || info.object;
  const layerId = (info.layer.id || "").replace(/-fill$|-pt$|-outline$|-lines$/, "");
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
  } else if (layerId === "transit_lines") {
    html += `${props.line_name || "Transit Line"}</div>`;
    html += popupRow("Type", props.line_type);
  } else if (layerId === "metra_stations") {
    html += `${props.station_name || "Metra Station"}</div>`;
    html += popupRow("Line", props.line_abbrev);
  } else if (layerId === "zoning" || layerId === "proposed_zoning") {
    const zc = props.ZONE_CLASS || props.zone_class || "—";
    html += `Zone ${zc}</div>`;
    if (props.zone_name) html += popupRow("Type", props.zone_name);
    if (props.proposed_zone) html += popupRow("Proposed", props.proposed_zone);
    if (props.changed !== undefined) html += popupRow("Changed", (props.changed === true || props.changed === "true") ? "Yes" : "No");
  } else {
    html += "Feature</div>";
  }

  // Create popup element
  const popup = document.createElement("div");
  popup.className = "deck-popup";
  popup.innerHTML = `
    <button class="popup-close" aria-label="Close popup">&times;</button>
    ${html}
  `;
  popup.style.left = info.x + "px";
  popup.style.top = info.y + "px";

  popup.querySelector(".popup-close").addEventListener("click", closePopup);

  document.getElementById("map").appendChild(popup);
  currentPopup = popup;
}

function closePopup() {
  if (currentPopup) {
    currentPopup.remove();
    currentPopup = null;
  }
}

function popupRow(label, value) {
  return `<div class="popup-row"><span class="popup-label">${label}</span><span>${value ?? "—"}</span></div>`;
}

// ---------------------------------------------------------------------------
// UI wiring
// ---------------------------------------------------------------------------
function wireUI() {
  // Layer toggles — data-layers="a,b" groups multiple layers under one checkbox
  document.querySelectorAll(".layer-toggle input").forEach((cb) => {
    cb.addEventListener("change", () => {
      const ids = (cb.dataset.layers || cb.dataset.layer || "")
        .split(",").map(s => s.trim()).filter(Boolean);
      ids.forEach(id => { layerVisible[id] = cb.checked; });
      rebuildLayers();
    });
  });

  // Tour buttons → fly-to with smooth transition
  document.querySelectorAll(".tour-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const lng = parseFloat(btn.dataset.lng);
      const lat = parseFloat(btn.dataset.lat);
      const zoom = parseFloat(btn.dataset.zoom);
      flyTo(lng, lat, zoom);
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

}

// ---------------------------------------------------------------------------
// Fly-to animation
// ---------------------------------------------------------------------------
function flyTo(lng, lat, zoom, duration = 2000) {
  closePopup();
  deckgl.setProps({
    initialViewState: {
      longitude: lng,
      latitude: lat,
      zoom: zoom,
      pitch: 0,
      bearing: 0,
      transitionDuration: duration,
      transitionInterpolator: new deck.FlyToInterpolator(),
    },
  });
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
      flyTo(parseFloat(lon), parseFloat(lat), 16, 1500);
      // Show a temporary popup at the geocoded location after transition
      setTimeout(() => {
        // Create a synthetic info object to show popup at screen center
        const mapEl = document.getElementById("map");
        const cx = mapEl.clientWidth / 2;
        const cy = mapEl.clientHeight / 2;
        const popup = document.createElement("div");
        popup.className = "deck-popup";
        popup.innerHTML = `
          <button class="popup-close" aria-label="Close popup">&times;</button>
          <div class="popup-title">${display_name}</div>
        `;
        popup.style.left = cx + "px";
        popup.style.top = cy + "px";
        popup.querySelector(".popup-close").addEventListener("click", closePopup);
        closePopup();
        mapEl.appendChild(popup);
        currentPopup = popup;
      }, 1600);
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
  if (document.activeElement === document.getElementById("map") ||
      document.activeElement === document.body) {
    const vs = deckgl.viewManager?.getViewState() ||
               deckgl.props?.initialViewState || {};
    const PAN_DELTA = 0.005;
    switch (e.key) {
      case "ArrowUp":
        flyTo(vs.longitude, vs.latitude + PAN_DELTA, vs.zoom, 200);
        e.preventDefault(); break;
      case "ArrowDown":
        flyTo(vs.longitude, vs.latitude - PAN_DELTA, vs.zoom, 200);
        e.preventDefault(); break;
      case "ArrowLeft":
        flyTo(vs.longitude - PAN_DELTA, vs.latitude, vs.zoom, 200);
        e.preventDefault(); break;
      case "ArrowRight":
        flyTo(vs.longitude + PAN_DELTA, vs.latitude, vs.zoom, 200);
        e.preventDefault(); break;
      case "+": case "=":
        flyTo(vs.longitude, vs.latitude, (vs.zoom || INITIAL_ZOOM) + 1, 300);
        e.preventDefault(); break;
      case "-":
        flyTo(vs.longitude, vs.latitude, (vs.zoom || INITIAL_ZOOM) - 1, 300);
        e.preventDefault(); break;
    }
  }
});

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", initMap);
