"""
Visualize Historical Appreciation Rates by Zoning Type

Creates charts to visualize the empirical appreciation rates calculated
from historical Cook County assessment data.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Configuration
DATA_DIR = Path(r"C:\Users\aaron\OneDrive\Desktop\OneDrive Desktop files\Sandboxes\Plan_for_Chicago_2030\analysis_results")
OUTPUT_DIR = Path(r"C:\Users\aaron\OneDrive\Desktop\OneDrive Desktop files\Sandboxes\Plan_for_Chicago_2030\visualizations")

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)

def plot_appreciation_by_zone():
    """Create bar chart of average appreciation by zoning type."""
    
    # Load data
    df = pd.read_csv(DATA_DIR / "historical_appreciation_by_zoning.csv")
    
    # Sort by appreciation rate
    df = df.sort_values('avg_annual_appreciation', ascending=True)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create bar chart
    bars = ax.barh(df['zoning_type'], df['avg_annual_appreciation'] * 100, 
                    color='steelblue', edgecolor='navy', linewidth=1.5)
    
    # Customize
    ax.set_xlabel('Average Annual Appreciation (%)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Zoning Type', fontsize=12, fontweight='bold')
    ax.set_title('Average Annual Property Appreciation by Zoning Type\nCook County, IL (1999-2025)', 
                 fontsize=14, fontweight='bold', pad=20)
    
    # Add value labels
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax.text(width + 0.2, bar.get_y() + bar.get_height()/2, 
               f'{width:.2f}%', 
               ha='left', va='center', fontsize=10, fontweight='bold')
    
    # Add grid
    ax.grid(axis='x', alpha=0.3)
    
    # Add zone type descriptions
    zone_desc = {
        'C': 'C - Commercial',
        'M': 'M - Manufacturing',
        'RT': 'RT - Residential Two-Flat',
        'B': 'B - Business',
        'RS': 'RS - Residential Single-Family',
        'RM': 'RM - Residential Multi-Family',
        'Unknown': 'Unknown'
    }
    
    labels = [zone_desc.get(z, z) for z in df['zoning_type']]
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    
    plt.tight_layout()
    
    # Save
    output_file = OUTPUT_DIR / "appreciation_by_zone.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    
    plt.close()

def plot_appreciation_trends():
    """Create line chart showing appreciation trends over time."""
    
    # Load data
    df = pd.read_csv(DATA_DIR / "appreciation_by_zone_year.csv")
    
    # Filter to main zones
    main_zones = ['RS', 'RM', 'RT', 'B', 'C', 'M']
    df = df[df['zoning_type'].isin(main_zones)]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Plot each zone
    colors = {'RS': '#1f77b4', 'RM': '#ff7f0e', 'RT': '#2ca02c', 
              'B': '#d62728', 'C': '#9467bd', 'M': '#8c564b'}
    
    for zone in main_zones:
        zone_data = df[df['zoning_type'] == zone]
        ax.plot(zone_data['tax_year'], zone_data['mean_appreciation'] * 100, 
               marker='o', linewidth=2.5, markersize=5, 
               label=zone, color=colors.get(zone, 'gray'), alpha=0.8)
    
    # Customize
    ax.set_xlabel('Tax Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Average Annual Appreciation (%)', fontsize=12, fontweight='bold')
    ax.set_title('Property Appreciation Trends by Zoning Type Over Time\nCook County, IL (1999-2025)', 
                 fontsize=14, fontweight='bold', pad=20)
    
    # Add legend
    ax.legend(title='Zoning Type', loc='upper left', fontsize=10, 
             title_fontsize=11, framealpha=0.9)
    
    # Add grid
    ax.grid(True, alpha=0.3)
    
    # Add zero line
    ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    
    # Highlight COVID period
    ax.axvspan(2019.5, 2020.5, alpha=0.1, color='red', label='COVID-19')
    
    plt.tight_layout()
    
    # Save
    output_file = OUTPUT_DIR / "appreciation_trends_over_time.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    
    plt.close()

def plot_recent_trends():
    """Focus on recent trends (2015-2025)."""
    
    # Load data
    df = pd.read_csv(DATA_DIR / "appreciation_by_zone_year.csv")
    
    # Filter to recent years and main zones
    main_zones = ['RS', 'RM', 'RT', 'B', 'C', 'M']
    df = df[(df['zoning_type'].isin(main_zones)) & (df['tax_year'] >= 2015)]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Plot each zone
    colors = {'RS': '#1f77b4', 'RM': '#ff7f0e', 'RT': '#2ca02c', 
              'B': '#d62728', 'C': '#9467bd', 'M': '#8c564b'}
    
    for zone in main_zones:
        zone_data = df[df['zoning_type'] == zone]
        ax.plot(zone_data['tax_year'], zone_data['mean_appreciation'] * 100, 
               marker='o', linewidth=3, markersize=7, 
               label=zone, color=colors.get(zone, 'gray'), alpha=0.85)
    
    # Customize
    ax.set_xlabel('Tax Year', fontsize=13, fontweight='bold')
    ax.set_ylabel('Average Annual Appreciation (%)', fontsize=13, fontweight='bold')
    ax.set_title('Recent Property Appreciation Trends (2015-2025)\nCook County, IL', 
                 fontsize=15, fontweight='bold', pad=20)
    
    # Add legend
    ax.legend(title='Zoning Type', loc='upper left', fontsize=11, 
             title_fontsize=12, framealpha=0.95)
    
    # Add grid
    ax.grid(True, alpha=0.3)
    
    # Add zero line
    ax.axhline(y=0, color='black', linestyle='--', linewidth=1.5, alpha=0.6)
    
    # Highlight COVID period
    ax.axvspan(2019.5, 2020.5, alpha=0.15, color='red')
    ax.text(2020, ax.get_ylim()[1] * 0.95, 'COVID-19', 
           ha='center', fontsize=10, style='italic', color='red')
    
    plt.tight_layout()
    
    # Save
    output_file = OUTPUT_DIR / "recent_appreciation_trends.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    
    plt.close()

def create_summary_stats_table():
    """Create a detailed summary table."""
    
    # Load data
    df = pd.read_csv(DATA_DIR / "historical_appreciation_by_zoning.csv")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis('tight')
    ax.axis('off')
    
    # Prepare data
    df = df.sort_values('avg_annual_appreciation', ascending=False)
    
    table_data = []
    zone_desc = {
        'C': 'Commercial',
        'M': 'Manufacturing',
        'RT': 'Residential Two-Flat',
        'B': 'Business',
        'RS': 'Residential Single-Family',
        'RM': 'Residential Multi-Family',
        'Unknown': 'Unknown'
    }
    
    for _, row in df.iterrows():
        table_data.append([
            row['zoning_type'],
            zone_desc.get(row['zoning_type'], 'Unknown'),
            f"{row['avg_annual_appreciation']*100:.2f}%",
            f"{row['median_annual_appreciation']*100:.2f}%",
            f"{row['std_appreciation']:.3f}",
            f"{int(row['total_observations']):,}"
        ])
    
    # Create table
    table = ax.table(cellText=table_data, 
                    colLabels=['Code', 'Description', 'Mean\nAppreciation', 
                              'Median\nAppreciation', 'Std Dev', 'Observations'],
                    cellLoc='center',
                    loc='center',
                    colWidths=[0.08, 0.25, 0.13, 0.13, 0.12, 0.15])
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)
    
    # Style header
    for i in range(6):
        table[(0, i)].set_facecolor('#4472C4')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Alternate row colors
    for i in range(1, len(table_data) + 1):
        for j in range(6):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#E7E6E6')
    
    # Title
    plt.title('Historical Property Appreciation Statistics by Zoning Type\nCook County, IL (1999-2025)', 
             fontsize=14, fontweight='bold', pad=20)
    
    # Save
    output_file = OUTPUT_DIR / "appreciation_summary_table.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    
    plt.close()

def main():
    """Generate all visualizations."""
    print("="*60)
    print("GENERATING VISUALIZATIONS")
    print("="*60)
    print()
    
    try:
        print("Creating charts...")
        
        plot_appreciation_by_zone()
        plot_appreciation_trends()
        plot_recent_trends()
        create_summary_stats_table()
        
        print()
        print("="*60)
        print("✓ ALL VISUALIZATIONS COMPLETE!")
        print("="*60)
        print(f"\nSaved to: {OUTPUT_DIR}")
        
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
