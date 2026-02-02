# Plan for Chicago 2030

A comprehensive urban planning analysis platform for visualizing and modeling Chicago's land use, zoning, transportation, and property values.

## 🎯 Project Overview

This project creates interactive visualizations and analysis tools to support policy analysis and community engagement around Chicago's future development. It combines:

- **Geospatial Data Analysis**: Property assessments, zoning districts, transit networks
- **Interactive Mapping**: Web-based visualizations with detailed tooltips and legends
- **Scenario Modeling**: Compare current vs. proposed upzoning and development scenarios
- **Property Value Analysis**: Model impacts of zoning changes and transit proximity

## 🗺️ Key Features

### Zoning Analysis (NEW!)
- **Interactive Zoning Map**: Explore Chicago's complete zoning districts with SimCity 2000-inspired colors
- **Scenario Comparison**: Model and visualize upzoning impacts on development capacity
- **Detailed Information**: FAR, building heights, density requirements for every zone
- **Data Source**: Official Chicago zoning data (April 2025), simplified for web performance

### Property Value Mapping
- **Parcel-Level Analysis**: Property values merged with geographic data
- **Area Aggregation**: Calculate total assessed values for defined regions
- **Interactive Visualization**: Click parcels to see detailed assessment information

### Transportation Network
- **OSM Integration**: Street networks and transit routes
- **Simulation Framework**: Placeholder for traffic modeling (SUMO/A-B Street)

## 🚀 Quick Start

### View Zoning Data

```powershell
# Create interactive zoning map
python visualize_zoning.py

# Open the generated map
chicago_zoning_map.html
```

### Compare Upzoning Scenarios

```powershell
# Run scenario analysis (currently: RS-3 → RT-4 upzoning)
python compare_zoning_scenarios.py

# Open results
zoning_comparison_map.html
```

### Analyze Property Values

```powershell
# Analyze a specific area (Near South Side)
python analyze_area.py

# Open results
area_value_map.html
```

## 📊 Data Files

### Included
- `chicago_zoning_2025.geojson` - Complete zoning districts (14.6MB)
- `zoning_codes.csv` - Comprehensive zoning code definitions
- `Plan_outline.md` - Full project vision and requirements

### To Download (via scripts)
- Cook County parcel geometries
- Property assessment data
- Census tracts
- OpenStreetMap networks

## 🛠️ Key Scripts

| Script | Purpose |
|--------|---------|
| `visualize_zoning.py` | Create city-wide interactive zoning map |
| `compare_zoning_scenarios.py` | Model and compare upzoning scenarios |
| `analyze_area.py` | Analyze property values in defined areas |
| `download_data.py` | Fetch data from Cook County and Chicago APIs |
| `loading_data.py` | Generate comprehensive city map with multiple layers |

## 📚 Understanding Chicago Zoning

### Zone Types
- **Residential (Green)**: RS (Single Family), RT (Townhouse), RM (Multi-Unit)
- **Business/Commercial (Blue)**: B1-B3 (Neighborhood to Community Shopping)
- **Manufacturing (Yellow)**: M1-M3 (Limited to Heavy Industry)
- **Downtown (Blue/Green)**: DX, DC, DR, DS districts
- **Special (Red/Gray/Dark Green)**: Planned Development, Transportation, Parks

### Density Indicators
Zone codes like RS-3, RM-5, or B1-2 include a number indicating Floor Area Ratio (FAR):
- RS-3: FAR 0.9 (Single family, 2,500 sq ft min lot)
- RT-4: FAR 1.2 (Townhouse, 1,000 sq ft/unit)
- RM-5: FAR 2.0 (Mid-rise, 400 sq ft/unit)
- RM-6: FAR 4.4 (High-rise, 300 sq ft/unit)

## 🎨 Visualization Features

### Color Coding
Maps use intuitive colors inspired by SimCity 2000:
- 🟢 Green: Residential zones
- 🔵 Blue: Business, commercial, downtown
- 🟡 Yellow: Manufacturing
- 🔴 Red: Planned developments
- 🌲 Dark Green: Parks and open space
- ⬛ Gray: Transportation

### Opacity Encoding
Transparency indicates density - more opaque zones allow higher Floor Area Ratios (FAR)

### Interactive Elements
- **Hover**: Quick zone code and district type
- **Click**: Full details including FAR, max height, ordinance numbers
- **Legend**: Comprehensive guide to zone types

## 🔮 Upcoming Features

- [ ] Parcel-zoning spatial joins in analyze_area.py
- [ ] Transit-oriented development (TOD) scenarios
- [ ] Property value uplift modeling based on zoning changes
- [ ] GTFS transit data integration
- [ ] Traffic simulation with SUMO or A/B Street
- [ ] Demographic overlay analysis

## 📖 Documentation

See `WARP.md` for comprehensive development guidance including:
- Data processing patterns
- Architecture overview
- Common workflows
- Extensibility points

## 🙏 Acknowledgments

### Data Sources
- **Zoning Data**: [DataMade's Second City Zoning](https://github.com/datamade/second-city-zoning)
- **Parcel/Assessment**: Cook County Open Data Portal
- **Geographic**: OpenStreetMap, Chicago Data Portal
- **Transit**: CTA GTFS feeds

### Inspiration
- SimCity 2000 visual design
- Burnham Plan of Chicago (1909)
- Modern transit-oriented development case studies

## 📄 License

This project builds on open data and open source tools. See individual data sources for their specific licenses.

---

**Status**: Active Development  
**Last Updated**: January 2025  
**Contact**: See Plan_outline.md for project goals and vision
