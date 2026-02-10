"""
Master Pipeline Orchestrator for Plan for Chicago 2030
=======================================================
Runs the complete data processing pipeline from download to web map generation.

Usage::

    python -m src.pipeline                    # Run full pipeline
    python -m src.pipeline --skip-download    # Skip download if data exists
    python -m src.pipeline --skip-zoning      # Skip zoning if enriched parcels exist

Pipeline stages:
    1. Download raw data (parcels, zoning, transit, census)
    2. Zoning analysis & parcel enrichment
    3. Transit accessibility scoring
    4. Web map data preparation

Outputs:
    - data/processed/parcels_enriched.geojson
    - data/processed/transit_scores.csv
    - data/processed/zoning_summary.csv
    - site/data/*.geojson (web map layers)
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

# Configure logging before any other imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


def run_pipeline(skip_download: bool = False, skip_zoning: bool = False, skip_transit: bool = False) -> bool:
    """
    Execute the complete data pipeline.
    
    Args:
        skip_download: Skip data download if files already exist
        skip_zoning: Skip zoning analysis if enriched parcels already exist
        skip_transit: Skip transit scoring if transit_scores.csv already exists
        
    Returns:
        True if pipeline completed successfully, False otherwise
    """
    start_time = datetime.now()
    
    logger.info("=" * 70)
    logger.info("Plan for Chicago 2030 — Data Pipeline")
    logger.info("=" * 70)
    
    # Import modules (after logging is configured)
    from src import download_data
    from src import zoning
    from src import transportation
    from src import prepare_map_data
    from src.config import (
        PARCEL_GEOJSON, ZONING_GEOJSON, CTA_STATIONS_GEOJSON,
        PARCELS_ENRICHED_GEOJSON, TRANSIT_SCORES_CSV, SITE_DATA_DIR
    )
    
    try:
        # ============================================================
        # Stage 1: Download Raw Data
        # ============================================================
        if not skip_download:
            logger.info("\n┌─ [1/4] Downloading raw data from Cook County & Chicago portals")
            logger.info("│")
            
            # Check if data already exists
            required_files = [PARCEL_GEOJSON, ZONING_GEOJSON, CTA_STATIONS_GEOJSON]
            all_exist = all(Path(f).exists() for f in required_files)
            
            if all_exist:
                logger.info("│   → All required files already exist")
                logger.info("│   → Run with --skip-download to skip this check")
            
            success = download_data.download_all_datasets()
            
            if not success:
                logger.warning("│   ⚠ Download completed with warnings (see above)")
            else:
                logger.info("│   ✓ Download complete")
            logger.info("└─")
        else:
            logger.info("\n[1/4] Skipping download (--skip-download)")
            # Verify required files exist
            if not Path(PARCEL_GEOJSON).exists():
                logger.error(f"✗ Required file missing: {PARCEL_GEOJSON}")
                logger.error("  Run without --skip-download to download data")
                return False
        
        # ============================================================
        # Stage 2: Zoning Analysis & Parcel Enrichment
        # ============================================================
        if not skip_zoning:
            logger.info("\n┌─ [2/4] Running zoning analysis & enrichment")
            logger.info("│")
            
            if Path(PARCELS_ENRICHED_GEOJSON).exists():
                logger.info(f"│   → {PARCELS_ENRICHED_GEOJSON} already exists")
                logger.info("│   → Regenerating...")
            
            enriched, summary = zoning.run_zoning_analysis()
            
            if enriched is None:
                logger.error("│   ✗ Zoning analysis failed")
                logger.error("└─")
                return False
            
            logger.info(f"│   ✓ Enriched {len(enriched):,} parcels")
            logger.info(f"│   → {PARCELS_ENRICHED_GEOJSON}")
            logger.info("└─")
        else:
            logger.info("\n[2/4] Skipping zoning analysis (--skip-zoning)")
            if not Path(PARCELS_ENRICHED_GEOJSON).exists():
                logger.error(f"✗ Required file missing: {PARCELS_ENRICHED_GEOJSON}")
                logger.error("  Run without --skip-zoning to generate enriched parcels")
                return False
        
        # ============================================================
        # Stage 3: Transit Accessibility Scoring
        # ============================================================
        if not skip_transit:
            logger.info("\n┌─ [3/4] Computing transit accessibility scores")
            logger.info("│")
            
            if Path(TRANSIT_SCORES_CSV).exists():
                logger.info(f"│   → {TRANSIT_SCORES_CSV} already exists")
                logger.info("│   → Regenerating...")
            
            scored = transportation.run_transit_scoring(compute_walkability=False)
            
            if scored is None:
                logger.error("│   ✗ Transit scoring failed")
                logger.error("└─")
                return False
            
            logger.info(f"│   ✓ Scored {len(scored):,} parcels")
            logger.info(f"│   → {TRANSIT_SCORES_CSV}")
            logger.info("└─")
        else:
            logger.info("\n[3/4] Skipping transit scoring (--skip-transit)")
        
        # ============================================================
        # Stage 4: Prepare Web Map Data
        # ============================================================
        logger.info("\n┌─ [4/4] Preparing web map data layers")
        logger.info("│")
        
        results = prepare_map_data.prepare_all()
        
        if not results or len(results) == 0:
            logger.error("│   ✗ Map data preparation failed")
            logger.error("└─")
            return False
        
        logger.info(f"│   ✓ Generated {len(results)} map layers:")
        for name, info in results.items():
            logger.info(f"│     • {name}: {info.get('features', '?'):,} features")
        
        logger.info(f"│   → {SITE_DATA_DIR}/")
        logger.info("└─")
        
        # ============================================================
        # Pipeline Complete
        # ============================================================
        elapsed = datetime.now() - start_time
        
        logger.info("\n" + "=" * 70)
        logger.info("✓ Pipeline completed successfully!")
        logger.info("=" * 70)
        logger.info(f"\nElapsed time: {elapsed}")
        logger.info("\nKey output files:")
        logger.info(f"  • {PARCELS_ENRICHED_GEOJSON}")
        logger.info(f"  • {TRANSIT_SCORES_CSV}")
        logger.info(f"  • {SITE_DATA_DIR}/*.geojson")
        logger.info(f"  • {SITE_DATA_DIR}/manifest.json")
        logger.info("\nNext steps:")
        logger.info("  → Open site/index.html in your browser to view the interactive map")
        logger.info("  → Run analysis scripts (analyze_area.py, compare_zoning_scenarios.py)")
        
        return True
        
    except KeyboardInterrupt:
        logger.info("\n\n⚠ Pipeline interrupted by user")
        return False
        
    except Exception as e:
        logger.error(f"\n✗ Pipeline failed with error: {e}", exc_info=True)
        logger.error("\nTo debug:")
        logger.error("  1. Check that all required data files exist in data/geojson/")
        logger.error("  2. Verify dependencies are installed: pip install -r requirements.txt")
        logger.error("  3. Run individual modules to isolate the issue:")
        logger.error("     python -m src.download_data")
        logger.error("     python -m src.zoning")
        logger.error("     python -m src.transportation")
        logger.error("     python -m src.prepare_map_data")
        return False


def main():
    """CLI entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Run the Plan for Chicago 2030 data processing pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.pipeline                    # Run full pipeline
  python -m src.pipeline --skip-download    # Skip download if data exists
  python -m src.pipeline --skip-zoning      # Skip zoning if already processed
  python -m src.pipeline --skip-download --skip-zoning --skip-transit
        """
    )
    
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip data download stage if raw files already exist"
    )
    
    parser.add_argument(
        "--skip-zoning",
        action="store_true",
        help="Skip zoning analysis stage if enriched parcels already exist"
    )
    
    parser.add_argument(
        "--skip-transit",
        action="store_true",
        help="Skip transit scoring stage if transit_scores.csv already exists"
    )
    
    args = parser.parse_args()
    
    success = run_pipeline(
        skip_download=args.skip_download,
        skip_zoning=args.skip_zoning,
        skip_transit=args.skip_transit
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
