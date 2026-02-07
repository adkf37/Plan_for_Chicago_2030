"""
Centralized Configuration for Plan for Chicago 2030
====================================================
All file paths, API settings, and shared constants in one place.
Every script imports paths from here — no more hardcoded absolute paths.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present (for local development)
load_dotenv()

# --- Project Root ---
# Two levels up from src/config.py → project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- API Configuration ---
SOCRATA_APP_TOKEN = os.environ.get("SOCRATA_APP_TOKEN", "")
SOCRATA_LIMIT = 50000  # Records per API page

# API endpoints
PARCEL_GEOMETRY_URL = "https://datacatalog.cookcountyil.gov/resource/nj4t-kc8j.geojson"
ASSESSMENT_DATA_URL = "https://datacatalog.cookcountyil.gov/resource/uzyt-m557.geojson"
ASSESSMENT_JSON_URL = "https://datacatalog.cookcountyil.gov/resource/uzyt-m557.json"
ZONING_DATA_URL = "https://data.cityofchicago.org/resource/dj47-wfun.geojson"

# --- Data Paths ---

# Raw data (immutable downloads — gitignored)
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_ASSESSMENT_CSV = RAW_DIR / "Assessor_-_Assessed_Values_20250430.csv"
RAW_PARCEL_UNIVERSE_CSV = RAW_DIR / "Assessor_-_Parcel_Universe_20250430.csv"
RAW_HISTORICAL_DIR = RAW_DIR / "historical"
RAW_HISTORICAL_CSV = RAW_HISTORICAL_DIR / "Assessor_-_Assessed_Values_since_1999_20251004.csv"

# GeoJSON data (downloaded spatial files — gitignored)
GEOJSON_DIR = PROJECT_ROOT / "data" / "geojson"
PARCEL_GEOJSON = GEOJSON_DIR / "parcel_data.geojson"
ASSESSMENT_GEOJSON = GEOJSON_DIR / "assessment_data.geojson"
ZONING_GEOJSON = GEOJSON_DIR / "zoning_data.geojson"
CHICAGO_ZONING_GEOJSON = GEOJSON_DIR / "chicago_zoning_2025.geojson"

# Reference data (small, tracked in git)
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
ZONING_CODES_CSV = REFERENCE_DIR / "zoning_codes.csv"

# Processed data (script outputs — gitignored)
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PARCELS_IN_AREA_CSV = PROCESSED_DIR / "parcels_in_area.csv"
UPZONING_CHANGES_CSV = PROCESSED_DIR / "upzoning_scenario_changes.csv"
VALUE_IMPACT_CSV = PROCESSED_DIR / "zoning_value_impact_analysis.csv"
HISTORICAL_DATA_DIR = PROCESSED_DIR / "historical_data"
UPLIFT_SCENARIOS_DIR = PROCESSED_DIR / "uplift_scenarios"

# --- Output Paths ---

# Generated HTML maps
MAPS_DIR = PROJECT_ROOT / "maps"
AREA_VALUE_MAP = MAPS_DIR / "area_value_map.html"
INTERACTIVE_MAP = MAPS_DIR / "chicago_interactive_map.html"
ZONING_MAP = MAPS_DIR / "chicago_zoning_map.html"
COMPARISON_MAP = MAPS_DIR / "zoning_comparison_map.html"
VALUE_IMPACT_MAP = MAPS_DIR / "zoning_value_impact_map.html"

# Analysis results
ANALYSIS_RESULTS_DIR = PROJECT_ROOT / "analysis_results"

# Reports and visualizations
REPORTS_DIR = PROJECT_ROOT / "reports"
VISUALIZATIONS_DIR = REPORTS_DIR / "visualizations"

# Cache
CACHE_DIR = PROJECT_ROOT / "cache"

# --- Analysis Configuration ---

# Cook County assessment ratio (assessed value / market value)
ASSESSMENT_RATIO = 0.10

# Property tax rate
PROPERTY_TAX_RATE = 0.025

# Study area bounding box (Near South Side)
STUDY_AREA = {
    "min_lon": -87.630,
    "max_lon": -87.617,
    "min_lat": 41.852,
    "max_lat": 41.867,
}

# Historical years to analyze
HISTORICAL_YEARS = [2000, 2005, 2010, 2015, 2020, 2023, 2024, 2025]

# --- Housing Density Categories ---
HOUSING_DENSITY_CATEGORIES = {
    "SFH": {"name": "Single-Family Home", "units_per_acre_min": 0, "units_per_acre_max": 8},
    "TH": {"name": "Townhouse / Duplex", "units_per_acre_min": 8, "units_per_acre_max": 16},
    "LR": {"name": "Low-Rise Apartment (2-4 stories)", "units_per_acre_min": 16, "units_per_acre_max": 30},
    "MR": {"name": "Mid-Rise Apartment (5-8 stories)", "units_per_acre_min": 30, "units_per_acre_max": 60},
    "HR": {"name": "High-Rise Apartment (9+ stories)", "units_per_acre_min": 60, "units_per_acre_max": 150},
    "MX_L": {"name": "Mixed-Use Low/Mid", "units_per_acre_min": 16, "units_per_acre_max": 60},
    "MX_H": {"name": "Mixed-Use High", "units_per_acre_min": 60, "units_per_acre_max": 150},
    "IND": {"name": "Industrial", "units_per_acre_min": 0, "units_per_acre_max": 0},
    "COM": {"name": "Commercial", "units_per_acre_min": 0, "units_per_acre_max": 0},
    "OS": {"name": "Open Space / Park", "units_per_acre_min": 0, "units_per_acre_max": 0},
}

# --- Value Uplift Model Parameters ---

# FAR-based appreciation rate (per FAR point increase)
FAR_APPRECIATION_RATE = 0.15

# Zone-to-zone transition factors (from case studies)
ZONE_TRANSITION_FACTORS = {
    ("RS-1", "RS-2"): 1.08,
    ("RS-1", "RS-3"): 1.12,
    ("RS-2", "RS-3"): 1.10,
    ("RS-3", "RT-4"): 1.18,
    ("RT-4", "RM-5"): 1.15,
    ("RM-5", "RM-6"): 1.20,
    ("B1-1", "B1-2"): 1.10,
    ("B1-2", "B1-3"): 1.12,
    ("B2-1", "B2-2"): 1.10,
    ("B2-2", "B2-3"): 1.12,
    ("B1", "B2"): 1.12,
    ("B2", "B3"): 1.15,
}

# Development rights adjustment factor
DEVELOPMENT_RIGHTS_ADJUSTMENT = 0.7

# Median property values by zone type (for estimation)
MEDIAN_VALUES_BY_ZONE = {
    "RS-1": 400000,
    "RS-2": 350000,
    "RS-3": 250000,
    "RT-4": 300000,
    "RM-5": 280000,
}

# --- Zoning Visualization ---

ZONE_TYPE_COLORS = {
    1: "#0000ff",   # Business (Blue)
    2: "#0000ff",   # Commercial/Mixed-Use (Blue)
    3: "#ffff00",   # Manufacturing (Yellow)
    4: "#00ff00",   # Residential (Green)
    5: "#ff0000",   # Planned Development (Red)
    6: "#ffff00",   # Planned Manufacturing District (Yellow)
    7: "#0000ff",   # Downtown Mixed-Use (Blue)
    8: "#0000ff",   # Downtown Core (Blue)
    9: "#00ff00",   # Downtown Residential (Green)
    10: "#0000ff",  # Downtown Service (Blue)
    11: "#666666",  # Transportation (Gray)
    12: "#38761d",  # Parks and Open Space (Dark Green)
}

ZONE_TYPE_NAMES = {
    1: "Business",
    2: "Commercial / Mixed-Use",
    3: "Manufacturing",
    4: "Residential",
    5: "Planned Development",
    6: "Planned Manufacturing District",
    7: "Downtown Mixed-Use",
    8: "Downtown Core",
    9: "Downtown Residential",
    10: "Downtown Service",
    11: "Transportation",
    12: "Parks and Open Space",
}


def ensure_dirs():
    """Create all output directories if they don't exist."""
    for d in [
        RAW_DIR, RAW_HISTORICAL_DIR, GEOJSON_DIR, REFERENCE_DIR,
        PROCESSED_DIR, HISTORICAL_DATA_DIR, UPLIFT_SCENARIOS_DIR,
        MAPS_DIR, ANALYSIS_RESULTS_DIR, REPORTS_DIR, VISUALIZATIONS_DIR,
        CACHE_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Socrata token configured: {'Yes' if SOCRATA_APP_TOKEN else 'No (set SOCRATA_APP_TOKEN)'}")
    ensure_dirs()
    print("All directories verified.")
