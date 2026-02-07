# Quick Start Guide — Uplift Analysis

## What This Does
Analyzes **27 years of historical property data** (1999–2025) to understand how
different zoning types appreciate over time, then uses those empirical rates to
model property value uplift from rezoning scenarios.

---

## Prerequisites

```bash
cp .env.example .env        # add your Socrata app token
pip install -r requirements.txt
```

---

## Run The Analysis (2 Steps)

### Step 1: Download Historical Data & Calculate Appreciation Rates
```powershell
python -m src.download_historical
```

**What it does:**
- Downloads historical assessment data for your parcels
- Calculates average annual appreciation by zoning type
- Writes to: `data/processed/appreciation_by_zoning.csv`

**Time:** 5–15 minutes (depending on number of parcels)

---

### Step 2: Run Uplift Scenarios
```powershell
python -m src.improved_uplift_model
```

**What it does:**
- Applies rezoning scenarios (e.g., upzone residential corridors)
- Calculates property value uplift using empirical appreciation rates
- Estimates property tax revenue impacts
- Writes to: `data/processed/uplift_scenarios/`

**Time:** < 1 minute

---

## View Results

### Appreciation Rates by Zoning Type
```powershell
Get-Content data\processed\appreciation_analysis_summary.txt
```

### Scenario Impact Summary
```powershell
Get-Content data\processed\uplift_scenarios\rezoning_impact_summary.txt
```

### Generate Charts
```powershell
python -m viz.visualize_appreciation
# → PNGs saved to reports/visualizations/
```

---

## Key Files

| File | Purpose |
|------|---------|
| `data/processed/appreciation_by_zone_year.csv` | Appreciation rates by zone type & year |
| `data/processed/uplift_scenarios/` | Uplift scenario results |
| `data/reference/zoning_codes.csv` | Zone code definitions (FAR, height, use) |
| `README_UPLIFT_ANALYSIS.md` | Full methodology documentation |

---

## Customise Scenarios

Edit `src/improved_uplift_model.py`, find `define_rezoning_scenarios()`:

```python
scenarios = {
    'your_scenario': {
        'name': 'My Custom Scenario',
        'description': 'What this does',
        'rules': [
            {'from_zoning': '202', 'to_zoning': '211', 'filter': None},
        ]
    }
}
```

**Common Cook County Classes:**
- `202`, `203`, `204` = Single-family (low density)
- `211`, `212` = Multi-family (medium density)
- `295`, `297`, `299` = Commercial
- `597`, `592` = Mixed-use (high density)

Then re-run: `python -m src.improved_uplift_model`

---

## Example Output

**Appreciation Rates:**
```
Zoning Type    Annual Appreciation
299            4.8 % per year
295            4.2 % per year
211            3.9 % per year
202            3.1 % per year
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

- Full docs: [README_UPLIFT_ANALYSIS.md](README_UPLIFT_ANALYSIS.md)
- Project overview: [README.md](README.md)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Ready to run?**
```powershell
python -m src.download_historical
```
