# Quick Start Guide - Uplift Analysis

## What This Does
Analyzes **27 years of historical property data** (1999-2025) to understand how different zoning types appreciate over time, then uses those empirical rates to model property value uplift from rezoning scenarios.

---

## Run The Analysis (2 Steps)

### Step 1: Download Historical Data & Calculate Appreciation Rates
```powershell
python download_historical_assessments.py
```

**What it does:**
- Downloads historical assessment data for your parcels
- Calculates average annual appreciation by zoning type
- Creates: `historical_data/appreciation_by_zoning.csv`

**Time:** 5-15 minutes (depending on number of parcels)

---

### Step 2: Run Uplift Scenarios
```powershell
python improved_uplift_model.py
```

**What it does:**
- Applies rezoning scenarios (e.g., upzone residential)
- Calculates property value uplift using empirical appreciation rates
- Estimates property tax revenue impacts
- Creates: `uplift_scenarios/rezoning_scenario_results.csv`

**Time:** < 1 minute

---

## View Results

### Appreciation Rates by Zoning Type
```powershell
cat historical_data/appreciation_summary.txt
```
Shows which zoning types appreciate fastest over time.

### Scenario Impact Summary
```powershell
cat uplift_scenarios/rezoning_impact_summary.txt
```
Shows total value uplift and tax revenue from each rezoning scenario.

---

## Key Files

| File | Purpose |
|------|---------|
| `historical_data/appreciation_by_zoning.csv` | ⭐ Appreciation rates by zone type |
| `uplift_scenarios/rezoning_scenario_results.csv` | ⭐ Summary of uplift scenarios |
| `README_UPLIFT_ANALYSIS.md` | Full documentation |

---

## Customize Scenarios

Edit `improved_uplift_model.py`, find `define_rezoning_scenarios()`:

```python
scenarios = {
    'your_scenario': {
        'name': 'My Custom Scenario',
        'description': 'What this does',
        'rules': [
            {'from_zoning': '202', 'to_zoning': '211', 'filter': None},
            # Add more rules
        ]
    }
}
```

**Common Cook County Classes:**
- `202`, `203`, `204` = Single-family (low density)
- `211`, `212` = Multi-family (medium density)  
- `295`, `297`, `299` = Commercial
- `597`, `592` = Mixed-use (high density)

Then re-run: `python improved_uplift_model.py`

---

## Example Output

**Appreciation Rates:**
```
Zoning Type    Annual Appreciation
299            4.8% per year
295            4.2% per year
211            3.9% per year
202            3.1% per year
```

**Scenario Results:**
```
Scenario: Upzone Residential Low to Medium
- Parcels affected: 150
- Total value uplift: $12,500,000
- Avg per parcel: $83,333
- Annual tax increase: $312,500
```

---

## Need Help?

- Full docs: `README_UPLIFT_ANALYSIS.md`
- Inline comments in both Python scripts explain each function

---

**Ready to run? Start with:**
```powershell
python download_historical_assessments.py
```
