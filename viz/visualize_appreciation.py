"""
Visualize Historical Appreciation Rates
========================================
Creates matplotlib/seaborn charts of property appreciation rates by
zoning type and over time.

Usage:
    python -m viz.visualize_appreciation
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.config import ANALYSIS_RESULTS_DIR, VISUALIZATIONS_DIR, ensure_dirs

# Style
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (12, 8)


def plot_appreciation_by_zone():
    """Bar chart of average appreciation by zoning type."""
    df = pd.read_csv(ANALYSIS_RESULTS_DIR / "historical_appreciation_by_zoning.csv")
    df = df.sort_values("avg_annual_appreciation", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(df["zoning_type"], df["avg_annual_appreciation"] * 100,
                   color="steelblue", edgecolor="navy", linewidth=1.5)
    ax.set_xlabel("Average Annual Appreciation (%)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Zoning Type", fontsize=12, fontweight="bold")
    ax.set_title("Average Annual Property Appreciation by Zoning Type\nCook County, IL (1999-2025)",
                 fontsize=14, fontweight="bold", pad=20)

    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.2, bar.get_y() + bar.get_height() / 2, f"{w:.2f}%",
                ha="left", va="center", fontsize=10, fontweight="bold")

    zone_desc = {"C": "C - Commercial", "M": "M - Manufacturing", "RT": "RT - Two-Flat",
                 "B": "B - Business", "RS": "RS - Single-Family", "RM": "RM - Multi-Family"}
    ax.set_yticklabels([zone_desc.get(z, z) for z in df["zoning_type"]])
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()

    out = VISUALIZATIONS_DIR / "appreciation_by_zone.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    print(f"Saved: {out}")
    plt.close()


def plot_appreciation_trends():
    """Line chart of appreciation trends over time."""
    df = pd.read_csv(ANALYSIS_RESULTS_DIR / "appreciation_by_zone_year.csv")
    main_zones = ["RS", "RM", "RT", "B", "C", "M"]
    df = df[df["zoning_type"].isin(main_zones)]
    colors = {"RS": "#1f77b4", "RM": "#ff7f0e", "RT": "#2ca02c",
              "B": "#d62728", "C": "#9467bd", "M": "#8c564b"}

    fig, ax = plt.subplots(figsize=(14, 8))
    for zone in main_zones:
        zd = df[df["zoning_type"] == zone]
        ax.plot(zd["tax_year"], zd["mean_appreciation"] * 100,
                marker="o", linewidth=2.5, markersize=5, label=zone,
                color=colors.get(zone, "gray"), alpha=0.8)

    ax.set_xlabel("Tax Year", fontsize=12, fontweight="bold")
    ax.set_ylabel("Average Annual Appreciation (%)", fontsize=12, fontweight="bold")
    ax.set_title("Property Appreciation Trends by Zoning Type\nCook County, IL (1999-2025)",
                 fontsize=14, fontweight="bold", pad=20)
    ax.legend(title="Zoning Type", loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linestyle="--", linewidth=1, alpha=0.5)
    ax.axvspan(2019.5, 2020.5, alpha=0.1, color="red")
    plt.tight_layout()

    out = VISUALIZATIONS_DIR / "appreciation_trends_over_time.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    print(f"Saved: {out}")
    plt.close()


def plot_recent_trends():
    """Focus on recent (2015-2025) appreciation trends."""
    df = pd.read_csv(ANALYSIS_RESULTS_DIR / "appreciation_by_zone_year.csv")
    main_zones = ["RS", "RM", "RT", "B", "C", "M"]
    df = df[(df["zoning_type"].isin(main_zones)) & (df["tax_year"] >= 2015)]
    colors = {"RS": "#1f77b4", "RM": "#ff7f0e", "RT": "#2ca02c",
              "B": "#d62728", "C": "#9467bd", "M": "#8c564b"}

    fig, ax = plt.subplots(figsize=(12, 7))
    for zone in main_zones:
        zd = df[df["zoning_type"] == zone]
        ax.plot(zd["tax_year"], zd["mean_appreciation"] * 100,
                marker="o", linewidth=3, markersize=7, label=zone,
                color=colors.get(zone, "gray"), alpha=0.85)

    ax.set_xlabel("Tax Year", fontsize=13, fontweight="bold")
    ax.set_ylabel("Average Annual Appreciation (%)", fontsize=13, fontweight="bold")
    ax.set_title("Recent Property Appreciation Trends (2015-2025)\nCook County, IL",
                 fontsize=15, fontweight="bold", pad=20)
    ax.legend(title="Zoning Type", loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linestyle="--", linewidth=1.5, alpha=0.6)
    ax.axvspan(2019.5, 2020.5, alpha=0.15, color="red")
    plt.tight_layout()

    out = VISUALIZATIONS_DIR / "recent_appreciation_trends.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    print(f"Saved: {out}")
    plt.close()


def create_summary_table():
    """Summary statistics table as a figure."""
    df = pd.read_csv(ANALYSIS_RESULTS_DIR / "historical_appreciation_by_zoning.csv")
    df = df.sort_values("avg_annual_appreciation", ascending=False)

    zone_desc = {"C": "Commercial", "M": "Manufacturing", "RT": "Two-Flat",
                 "B": "Business", "RS": "Single-Family", "RM": "Multi-Family"}

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis("tight")
    ax.axis("off")

    rows = []
    for _, r in df.iterrows():
        rows.append([
            r["zoning_type"], zone_desc.get(r["zoning_type"], "Unknown"),
            f"{r['avg_annual_appreciation'] * 100:.2f}%",
            f"{r['median_annual_appreciation'] * 100:.2f}%",
            f"{r['std_appreciation']:.3f}",
            f"{int(r['total_observations']):,}",
        ])

    table = ax.table(
        cellText=rows,
        colLabels=["Code", "Description", "Mean", "Median", "Std Dev", "Observations"],
        cellLoc="center", loc="center",
        colWidths=[0.08, 0.25, 0.13, 0.13, 0.12, 0.15],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)
    for i in range(6):
        table[(0, i)].set_facecolor("#4472C4")
        table[(0, i)].set_text_props(weight="bold", color="white")
    for i in range(1, len(rows) + 1):
        for j in range(6):
            if i % 2 == 0:
                table[(i, j)].set_facecolor("#E7E6E6")

    plt.title("Historical Appreciation Statistics by Zoning Type\nCook County, IL (1999-2025)",
              fontsize=14, fontweight="bold", pad=20)
    out = VISUALIZATIONS_DIR / "appreciation_summary_table.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    print(f"Saved: {out}")
    plt.close()


def main():
    ensure_dirs()
    print("=" * 60)
    print("GENERATING VISUALIZATIONS")
    print("=" * 60 + "\n")
    try:
        plot_appreciation_by_zone()
        plot_appreciation_trends()
        plot_recent_trends()
        create_summary_table()
        print(f"\nAll charts saved to {VISUALIZATIONS_DIR}")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
