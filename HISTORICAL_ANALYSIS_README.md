# Historical Property Assessment Analysis - Summary

## Overview

Successfully processed **48.8 million records** from Cook County's historical assessment data (1999-2025) to calculate empirical property appreciation rates by zoning/land use type.

## Key Findings

### Average Annual Appreciation Rates by Zoning Type

Based on analysis of **1.73 million unique properties** over 26 years:

| Zoning Type | Description | Avg Annual Appreciation | Sample Size |
|-------------|-------------|------------------------|-------------|
| **C** | Commercial | **8.31%** | 143,715 obs |
| **M** | Manufacturing/Industrial | **6.93%** | 430,315 obs |
| **RT** | Residential Two-Flat | **6.39%** | 4,135,828 obs |
| **B** | Business | **6.07%** | 1,899,671 obs |
| **RS** | Residential Single-Family | **4.17%** | 13,948,099 obs |
| **RM** | Residential Multi-Family | **3.86%** | 19,555,437 obs |

### Key Insights

1. **Commercial properties (C)** show the highest appreciation at 8.31% annually
2. **Manufacturing/Industrial (M)** zones have strong growth at 6.93%
3. **Two-flat residential (RT)** properties outperform both single-family and multi-family
4. **Single-family (RS)** and **Multi-family (RM)** residential show similar, modest appreciation (3.9-4.2%)

### Recent Trends (2020-2025)

Looking at residential single-family (RS) as an example:
- **2020**: -5.5% (COVID-19 impact)
- **2021**: +6.2% (recovery)
- **2022**: +9.0%
- **2023**: +13.2% (peak)
- **2024**: +8.0%
- **2025**: +10.4% (partial year)

## Methodology

### Data Source
- **Historical Assessment Data**: `Assessor_-_Assessed_Values_since_1999_20251004.csv` (7.8GB)
- **Current Assessment Data**: `Assessor_-_Assessed_Values_20250430.csv`

### Approach
1. **Loaded historical data in chunks** (100k rows at a time) to handle large file size
2. **Filtered to relevant property classes**: 
   - 200s = Residential
   - 300s = Industrial
   - 500s = Commercial
3. **Assigned zoning proxy** based on property classification codes:
   - Classes 203-209 → RS (Single-Family)
   - Classes 211-212 → RT (Two-Flat)
   - Other 200s → RM (Multi-Family)
   - Most 500s → B (Business)
   - Classes 591-592 → C (Commercial)
   - 300s → M (Manufacturing)
4. **Calculated year-over-year changes** for each property
5. **Removed outliers** (changes > 500% or < -90%)
6. **Aggregated statistics** by zoning type

### Limitations
- **Current zoning used as proxy**: Properties may have been rezoned during observation period
- **Assessed values ≠ market values**: County assessments may lag actual market changes
- **No spatial join**: Actual zoning boundaries not used; property class used as proxy
- **Survivorship bias**: Properties not consistently assessed throughout period excluded

## Generated Files

All analysis results saved to: `analysis_results/`

1. **`historical_appreciation_by_zoning.csv`**
   - Summary table with average annual rates by zoning type
   - Use this for uplift modeling scenarios

2. **`appreciation_by_zone_year.csv`**
   - Time-series data showing appreciation by zoning type and year
   - Useful for trend analysis and cyclical adjustments

3. **`parcel_appreciation_summary.csv`**
   - Individual parcel-level statistics
   - Contains average appreciation, total appreciation, years observed
   - Large file (~1.7M parcels)

4. **`appreciation_analysis_summary.txt`**
   - Human-readable summary report

## Next Steps

### 1. Review the Results
- Examine the appreciation rates for reasonableness
- Compare to known market trends in Chicago
- Consider adjusting for recent anomalies (COVID, 2023 spike)

### 2. Apply to Uplift Modeling
Use these empirical rates in `improved_uplift_model.py` to:
- Estimate future property values under current zoning
- Model value uplift from rezoning scenarios
- Calculate property tax revenue impacts

### 3. Scenario Analysis
Example scenarios to model:
- **Upzoning**: RS → RT or RM (expect ~2-3% higher appreciation)
- **Commercial conversion**: RS → C (expect ~4% higher appreciation)
- **Industrial to mixed-use**: M → B/C/RM (varies by target type)

### 4. Refine Analysis (Optional)
For more accurate results:
- Perform spatial join with actual zoning boundaries
- Separate Chicago properties from rest of Cook County
- Adjust for neighborhood effects
- Control for property characteristics (size, age, etc.)

## Usage Example

```python
import pandas as pd

# Load the appreciation rates
rates = pd.read_csv('analysis_results/historical_appreciation_by_zoning.csv')

# Get rate for a specific zoning type
rs_rate = rates[rates['zoning_type'] == 'RS']['avg_annual_appreciation'].values[0]
print(f"RS appreciation: {rs_rate:.2%}")  # 4.17%

# Project future value
current_value = 250000
years = 10
future_value = current_value * (1 + rs_rate) ** years
print(f"Projected value: ${future_value:,.0f}")
```

## Questions?

Review the detailed methodology in `process_historical_assessments.py` for implementation details.
