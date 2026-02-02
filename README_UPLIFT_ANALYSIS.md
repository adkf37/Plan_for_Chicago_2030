# Property Value Uplift Analysis - Plan for Chicago 2030

This analysis combines **historical property value appreciation data** with **current zoning information** to create empirically-grounded models of property value uplift from rezoning scenarios.

## Overview

The analysis implements **Option 1 + Option 2**:
- **Option 1**: Use historical assessment data to understand how different zoning types appreciate over time
- **Option 2**: Apply these empirical rates to model property value uplift from rezoning scenarios

### Key Insight
By analyzing how properties with different current zoning types have appreciated historically, we can estimate how much additional value will be created when a parcel is rezoned to a higher-density or more valuable zoning category.

---

## Workflow

### Step 1: Download Historical Assessment Data
**Script**: `download_historical_assessments.py`

This script:
1. Loads your existing parcels (from `parcels_in_area.csv`)
2. Downloads 27 years of historical assessment data (1999-2025) from Cook County
3. Matches historical values with current zoning categories
4. Calculates average annual appreciation rates by zoning type
5. Outputs:
   - `historical_data/historical_assessments.csv` - Full historical dataset
   - `historical_data/appreciation_by_zoning.csv` - **Key file**: Appreciation rates by zone
   - `historical_data/appreciation_summary.txt` - Human-readable summary

**Run it:**
```powershell
python download_historical_assessments.py
```

**What you'll learn:**
- Which zoning types appreciate fastest (e.g., commercial vs. residential)
- How much properties in different zones have gained in value over 20+ years
- Empirical annual appreciation rates to use in your models

---

### Step 2: Run Uplift Scenarios
**Script**: `improved_uplift_model.py`

This script:
1. Loads the appreciation rates calculated in Step 1
2. Applies rezoning scenarios (e.g., upzone low-density residential to medium-density)
3. Calculates property value uplift based on differential appreciation rates
4. Estimates property tax revenue impacts
5. Outputs:
   - `uplift_scenarios/rezoning_scenario_results.csv` - Summary of all scenarios
   - `uplift_scenarios/scenario_*_details.csv` - Parcel-level results for each scenario
   - `uplift_scenarios/rezoning_impact_summary.txt` - Executive summary

**Run it:**
```powershell
python improved_uplift_model.py
```

**What you'll learn:**
- Total property value uplift from each rezoning scenario
- Which parcels benefit most from rezoning
- Estimated property tax revenue increases
- Cost-benefit comparison of different rezoning strategies

---

## Data Sources

### Cook County Assessment Data
- **API**: Cook County Data Portal (Socrata)
- **Years Available**: 1999-2025 (27 years)
- **Fields Used**:
  - `pin` - Parcel Identification Number
  - `year` - Assessment year
  - `certified_tot` - Certified total assessed value
  - `class` - Property classification code

### Chicago Zoning Data
- **Source**: City of Chicago Open Data Portal
- **File**: `chicago_zoning_2025.geojson`
- **Used for**: Mapping property classes to zoning designations

### Your Parcel Data
- **File**: `parcels_in_area.csv`
- **Must include**: `pin`, `certified_tot`, `class`, `geometry`

---

## How It Works

### The Appreciation Model

1. **Historical Baseline**: For each zoning type (e.g., Class 202 = single-family residential), calculate:
   - Average annual appreciation rate over historical period
   - Example: Class 202 properties appreciated 3.5% per year on average

2. **Rezoning Differential**: When a parcel is rezoned:
   - Old appreciation rate: 3.5% per year (Class 202)
   - New appreciation rate: 5.2% per year (Class 211 - multi-family)
   - **Differential**: +1.7% per year

3. **Future Value Projection**:
   - **Baseline scenario**: Parcel continues appreciating at 3.5%/year
   - **Rezoned scenario**: Parcel appreciates at 5.2%/year
   - **Uplift**: Difference between scenarios over time horizon

### Example Calculation

**Parcel Details:**
- Current value: $300,000
- Current zoning: Class 202 (single-family)
- Proposed zoning: Class 211 (multi-family)
- Time horizon: 10 years

**Baseline (no rezoning):**
- Appreciation: 3.5% per year
- Future value: $300,000 × (1.035)^10 = $422,000

**Rezoned scenario:**
- Appreciation: 5.2% per year
- Future value: $300,000 × (1.052)^10 = $497,000

**Uplift:**
- Value uplift: $497,000 - $422,000 = **$75,000**
- Annual tax increase (at 2.5% rate): $75,000 × 0.025 = **$1,875/year**

---

## Customization

### Adjust Time Horizons
In `improved_uplift_model.py`, change:
```python
TIME_HORIZON = 10  # Change to 5, 15, 20, etc.
```

### Define Your Own Scenarios
In `improved_uplift_model.py`, edit the `define_rezoning_scenarios()` function:

```python
scenarios = {
    'your_scenario_name': {
        'name': 'Descriptive Name',
        'description': 'What this scenario does',
        'rules': [
            {'from_zoning': '202', 'to_zoning': '211', 'filter': None},
            {'from_zoning': '203', 'to_zoning': '211', 'filter': None},
        ]
    }
}
```

**Common Cook County Property Classes:**
- `202`, `203`, `204` - Single-family residential (low density)
- `211`, `212` - Multi-family residential (medium density)
- `295`, `297`, `299` - Commercial
- `241`, `278` - Industrial
- `597`, `592` - Mixed-use/high-density

### Adjust Tax Rates
In `improved_uplift_model.py`, modify:
```python
PROPERTY_TAX_RATE = 0.025  # Change to match your area's effective rate
ASSESSMENT_RATIO = 0.10    # Cook County residential assessment ratio
```

### Select Different Years
In `download_historical_assessments.py`, modify:
```python
YEARS_TO_DOWNLOAD = [2000, 2005, 2010, 2015, 2020, 2024, 2025]  # Customize years
```

---

## Interpreting Results

### Appreciation Rates File
`historical_data/appreciation_by_zoning.csv` shows:

| Column | Meaning |
|--------|---------|
| `zoning_type` | Property class code |
| `parcel_count` | Number of parcels analyzed |
| `avg_annual_appreciation_pct` | Average % increase per year |
| `median_annual_appreciation_pct` | Median % increase per year |
| `avg_early_value` | Average assessed value in earliest year |
| `avg_late_value` | Average assessed value in latest year |

**Use this to:**
- Identify which zoning types are most valuable
- Find zones with highest growth potential
- Validate your rezoning strategy

### Scenario Results File
`uplift_scenarios/rezoning_scenario_results.csv` shows:

| Column | Meaning |
|--------|---------|
| `scenario_name` | Name of the rezoning scenario |
| `parcels_rezoned` | Number of parcels affected |
| `total_value_uplift` | Total property value increase |
| `avg_uplift_per_parcel` | Average value increase per parcel |
| `total_annual_tax_increase` | Annual property tax revenue increase |

**Use this to:**
- Compare different rezoning strategies
- Estimate fiscal impacts
- Prioritize high-impact areas

---

## Limitations & Caveats

1. **Past Performance ≠ Future Results**: Historical appreciation rates may not predict future trends
2. **Supply-Side Effects**: Rezoning may increase housing supply, which could moderate price growth
3. **Geographic Variation**: Appreciation rates vary by neighborhood; city-wide averages may not apply locally
4. **Confounding Factors**: Historical appreciation includes effects of:
   - Economic cycles
   - Neighborhood changes
   - Infrastructure investments
   - Market dynamics

5. **Assessment Lag**: Cook County assessments may lag market values

### Recommendations:
- Use conservative (median) appreciation rates for official estimates
- Run sensitivity analyses with different time horizons
- Validate results against local real estate data
- Consider geographic sub-analyses by ward/neighborhood

---

## Next Steps

### For Better Analysis:
1. **Add Geographic Filters**: Modify scenarios to target specific neighborhoods or transit corridors
2. **Integrate Transit Data**: Weight uplift by proximity to L stations or bus routes
3. **Neighborhood Analysis**: Calculate appreciation rates by ward or community area
4. **Time-Series Visualization**: Plot historical value trends by zoning type
5. **Market Value Validation**: Compare assessed values to actual sales data

### Suggested Enhancements:
```python
# In improved_uplift_model.py, add transit proximity logic:
def is_near_transit(parcel_geom, transit_stations, distance_meters=800):
    """Check if parcel is within walking distance of transit."""
    # Implementation here
    pass

# Use in scenario rules:
'rules': [
    {
        'from_zoning': '202', 
        'to_zoning': '211', 
        'filter': lambda df: is_near_transit(df['geometry'], transit_stations)
    }
]
```

---

## Files Generated

```
Plan_for_Chicago_2030/
├── parcels_in_area.csv                    # Input: Your parcels
├── download_historical_assessments.py     # Script: Download & analyze historical data
├── improved_uplift_model.py               # Script: Run uplift scenarios
├── historical_data/                       # Output: Historical analysis
│   ├── historical_assessments.csv         # Full historical dataset
│   ├── appreciation_by_zoning.csv         # ⭐ Key: Appreciation rates by zone
│   └── appreciation_summary.txt           # Human-readable summary
└── uplift_scenarios/                      # Output: Scenario analysis
    ├── rezoning_scenario_results.csv      # ⭐ Summary of all scenarios
    ├── scenario_*_details.csv             # Detailed parcel-level results
    └── rezoning_impact_summary.txt        # Executive summary
```

---

## Questions?

Review the inline comments in both scripts for detailed documentation of each function and calculation method.

For issues or enhancements, check:
1. Cook County Data Portal: https://datacatalog.cookcountyil.gov/
2. Chicago Open Data Portal: https://data.cityofchicago.org/
3. Your local property tax assessor for accurate tax rates

---

## Quick Start

```powershell
# Step 1: Download and analyze historical data
python download_historical_assessments.py

# Step 2: Review appreciation rates
cat historical_data/appreciation_summary.txt

# Step 3: Run uplift scenarios
python improved_uplift_model.py

# Step 4: Review results
cat uplift_scenarios/rezoning_impact_summary.txt
```

**Estimated runtime:**
- Step 1: 5-15 minutes (depending on number of parcels and API speed)
- Step 3: < 1 minute

---

**Happy modeling!** 🏙️📊
