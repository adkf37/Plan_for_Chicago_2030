# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a comprehensive urban planning project that creates an interactive visualization and analysis platform for reimagining Chicago's land use and transportation systems. The project combines geospatial data analysis, property value modeling, transportation simulation, and web-based interactive mapping to support policy analysis and community engagement.

## Core Architecture

### Data Processing Pipeline
- **Data Sources**: Cook County parcel/assessment data, Chicago zoning data, OpenStreetMap network data
- **Processing**: `download_data.py` handles API data fetching with pagination, `data_utils.py` provides utilities for Socrata API interactions
- **Storage**: Local files in GeoJSON and CSV formats for processed datasets

### Analysis Modules
- **`analyze_area.py`**: Core spatial analysis engine that merges parcel geometries with assessment data, performs value aggregation for defined areas, and exports filtered datasets
- **`property_value.py`**: Property value uplift modeling with appreciation factors based on proximity to transit and upzoning scenarios
- **`transportation.py`**: Transportation network analysis and simulation framework (placeholder for SUMO/A-B Street integration)
- **`zoning.py`**: Zoning classification and proposed density mapping with 8-10 housing density categories

### Visualization Layer
- **`loading_data.py`**: Creates comprehensive interactive maps with multiple data layers using Folium
- **Output**: HTML files with LayerControl, drawing tools, and responsive design for policy presentation

## Common Development Commands

### Data Download and Processing
```powershell
# Download all datasets from Cook County and Chicago data portals
python download_data.py

# Analyze specific geographic area (currently focused on Near South Side)
python analyze_area.py

# Generate comprehensive city-wide interactive map
python loading_data.py
```

### Zoning Analysis and Visualization
```powershell
# Create interactive zoning map with detailed zone information
python visualize_zoning.py

# Compare current vs proposed upzoning scenarios
python compare_zoning_scenarios.py
```

### Analysis Workflows
```powershell
# Run property value uplift analysis
python property_value.py

# Execute transportation analysis (requires additional setup)
python transportation.py

# Process zoning and density classification
python zoning.py
```

### Testing Individual Components
```powershell
# Test data utilities for API connections
python -c "from data_utils import *; print('Data utilities imported successfully')"

# Validate geospatial processing
python -c "import geopandas as gpd; print('GeoPandas available')"
```

## Key Dependencies

### Required Python Packages
- **Core**: `geopandas`, `pandas`, `folium`, `osmnx`, `requests`
- **Visualization**: `folium.plugins` (MarkerCluster, Draw)
- **Geospatial**: `shapely.geometry`, `shapely.wkt`

### Optional Dependencies (for full functionality)
- **OSM Processing**: `osmnx` for street network analysis
- **Transit Data**: GTFS parsing libraries for CTA integration
- **Simulation**: SUMO or A/B Street for traffic modeling

## Configuration and Data Paths

### File Structure Expectations
- `parcel_data.geojson`: Cook County parcel geometries
- `assessment_data.geojson`: Property assessment values
- `chicago_zoning_2025.geojson`: Chicago zoning districts (simplified, 14.6MB)
- `zoning_codes.csv`: Comprehensive zoning code definitions with FAR, heights, density
- `*_in_area.csv`: Filtered analysis results
- `*.html`: Generated interactive maps

### API Configuration
- Socrata App Token required for data downloads (currently: "ApE4oAonZT2D1PEE5ZY8xgs6M")
- Default pagination limit: 50,000 records per request
- Server-side spatial filtering attempted first, falls back to local filtering

## Data Processing Patterns

### Spatial Analysis Workflow
1. Load parcel geometries and assessment data separately
2. Clean and standardize PIN formats (remove dashes, convert to string)
3. Merge datasets on PIN/parcel ID
4. Define area of interest using bounding box or polygon
5. Filter merged dataset spatially
6. Calculate aggregated values and export results

### Value Modeling Approach
- Base property values from assessment data
- Apply appreciation factors based on:
  - Transit proximity (high: 15%, medium: 8%)
  - Upzoning categories (low density: 10%, medium: 5%)
- Support for rule-based and regression-based uplift models

### Housing Density Categories
- Single-Family Home (SFH): 0-8 units/acre
- Townhouse/Duplex (TH): 8-16 units/acre
- Low-Rise Apartment (LR): 16-30 units/acre
- Mid-Rise Apartment (MR): 30-60 units/acre
- High-Rise Apartment (HR): 60-150 units/acre
- Mixed-Use variants (MX_L, MX_H)

### Chicago Zoning Classification System
The project uses Chicago's official zoning data with the following major categories:
- **ZONE_TYPE 1-3**: Business, Commercial/Mixed-Use, Manufacturing (Blue/Yellow)
- **ZONE_TYPE 4**: Residential zones (Green) - RS (Single Family), RT (Townhouse), RM (Multi-Unit)
- **ZONE_TYPE 5-6**: Planned Development, Planned Manufacturing District (Red/Yellow)
- **ZONE_TYPE 7-10**: Downtown zones - DX, DC, DR, DS (Blue/Green)
- **ZONE_TYPE 11-12**: Transportation, Parks and Open Space (Gray/Dark Green)

Zone classes include density modifiers (e.g., RS-3, RM-5, B1-2) where higher numbers indicate greater allowed Floor Area Ratio (FAR) and building density.

## Interactive Map Features

### Standard Layer Stack
- Base map: CartoDB Positron tiles
- Chicago boundary outline
- Road network from OpenStreetMap
- Parcel geometries (performance-limited sample)
- Zoning districts with color coding
- Census tracts for demographic context

### User Interface Elements
- Layer control panel for toggling overlays
- Drawing tools for area definition
- Click-based popups with property details
- Export functionality for user modifications
- Legend with quantile-based color scales

## Development Considerations

### Performance Optimization
- Large parcel datasets limited to 1000 features for demonstration
- Vector tiles recommended for production deployment
- Geometry simplification applied for web performance
- MarkerCluster used for point datasets with many features

### Error Handling Patterns
- Graceful degradation when data files missing
- API error handling with fallback to local data
- CRS validation and automatic reprojection to WGS84
- Empty dataset detection and user feedback

### Extensibility Points
- Modular appreciation factor system in `property_value.py`
- Configurable housing density categories in `zoning.py`
- Pluggable transportation simulation backends
- Customizable area definitions and filtering criteria

## Zoning Visualization and Scenario Analysis

### Interactive Zoning Maps
- **`visualize_zoning.py`**: Creates city-wide zoning map with SimCity 2000-inspired color scheme
- **Color coding**: Zones colored by type (Residential=Green, Commercial=Blue, Manufacturing=Yellow)
- **Opacity encoding**: Transparency indicates density/FAR (higher density = more opaque)
- **Rich tooltips**: Hover to see zone code and district; click for full details including FAR, max height, ordinances
- **Legend**: Shows zone type categories and indicates that opacity represents density

### Upzoning Scenario Comparison
- **`compare_zoning_scenarios.py`**: Analyzes impact of zoning changes on development capacity
- **Current implementation**: Upzones all RS-3 (Single Family) to RT-4 (Townhouse/Low-Rise)
- **Metrics tracked**: Total FAR increase, number of parcels affected, percentage changes
- **Visual output**: Red highlights show upzoned areas with opacity indicating FAR increase magnitude
- **Export capability**: Changed parcels exported to CSV for further analysis
- **Extensible framework**: UPZONING_SCENARIOS dict supports multiple scenario definitions

### Data Sources and Attribution
Zoning data sourced from [DataMade's Second City Zoning](https://github.com/datamade/second-city-zoning) project:
- **Geometry**: Simplified GeoJSON from Chicago's ArcGIS server (updated April 2025)
- **Metadata**: Comprehensive zoning code descriptions including FAR, heights, setbacks, lot requirements
- **Processing**: Geometries simplified with 0.00003 tolerance for web performance
- **Properties preserved**: ZONE_TYPE, ZONE_CLASS, ORDINANCE_NUM for analysis

## Current Limitations and TODOs

### Data Integration
- Placeholder implementations in transportation and property value modules require completion
- GTFS transit data integration not fully implemented
- Census demographic data loading needs error handling improvements
- Parcel-zoning spatial joins not yet implemented in analyze_area.py

### Simulation Capabilities
- Traffic simulation framework requires external tool integration (SUMO/A-B Street)
- Property value uplift models need calibration with real case studies
- Mode share and accessibility analysis not fully developed

### Visualization Enhancements
- Complex legends require branca library for full feature set
- Mobile responsiveness needs testing and optimization
- Real-time data updates not implemented

This project represents a sophisticated urban planning analysis platform with strong foundations in geospatial data processing and web visualization, ready for extension into full policy simulation and community engagement tools.