"""
Redis Monitor - Farm Metadata Comparison Tool

A monitoring script that compares farm metadata responses between old database
and new Redis-based APIs to ensure data consistency and migration validation.

Usage:
    python redis_monitor.py

The script will:
    1. Load configuration from .env file
    2. Generate JWT tokens for each farm
    3. Fetch metadata from both old and new APIs
    4. Compare responses using DeepDiff
    5. Generate console and JSON reports
"""

import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.auth import generate_token
from src.api_client import APIClient
from src.comparison import compare_responses
from src.reporter import Reporter


def main():
    """Main orchestration function."""
    print("\n" + "=" * 80)
    print("REDIS MONITOR - Farm Metadata Comparison Tool")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Initialize components
    try:
        api_client = APIClient()
        reporter = Reporter()
        Config.ensure_output_dir()
    except Exception as e:
        print(f"❌ Failed to initialize: {str(e)}")
        return 1

    # Get farm IDs to process
    try:
        farm_ids = Config.get_farm_ids()
        print(f"\n→ Found {len(farm_ids)} farm(s) to compare")
    except Exception as e:
        print(f"❌ Failed to load farm IDs from configuration: {str(e)}")
        return 1

    if not farm_ids:
        print("❌ No farm IDs configured. Set FARM_IDS in .env file")
        return 1

    # Process each farm
    results = []
    test_run_id = datetime.now().strftime('%Y%m%d_%H%M%S')

    for idx, farm_id in enumerate(farm_ids, 1):
        print(f"\n[{idx}/{len(farm_ids)}] Processing Farm: {farm_id}")
        print("-" * 80)

        try:
            # Generate token
            token = generate_token(farm_id)

            # Fetch from both APIs
            old_api_data, new_api_data = api_client.fetch_both(farm_id, token)

            # Compare responses
            comparison = compare_responses(old_api_data, new_api_data)

            # Print farm comparison
            reporter.print_farm_comparison(farm_id, old_api_data, new_api_data, comparison)

            # Store result
            results.append({
                'farm_id': farm_id,
                'old_api': old_api_data,
                'new_api': new_api_data,
                'comparison': comparison,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            print(f"❌ Error processing farm {farm_id}: {str(e)}")
            results.append({
                'farm_id': farm_id,
                'old_api': None,
                'new_api': None,
                'comparison': {
                    'error': str(e),
                    'has_differences': True
                },
                'timestamp': datetime.now().isoformat()
            })

    # Generate reports
    print("\n" + "=" * 80)
    print("GENERATING REPORTS")
    print("=" * 80)

    try:
        json_path, html_path = reporter.generate_reports(results, test_run_id)
    except Exception as e:
        print(f"⚠ Warning: Failed to generate reports: {str(e)}")
        json_path, html_path = None, None

    # Print summary
    reporter.print_summary(results)

    # Determine exit code
    farms_with_errors = sum(1 for r in results if r['comparison'].get('error') or 
                           r['old_api'] is None or r['new_api'] is None)
    farms_with_differences = sum(1 for r in results if r['comparison'].get('has_differences', False) and
                                not r['comparison'].get('error'))

    print(f"\n→ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if farms_with_errors > 0:
        return 1
    elif farms_with_differences > 0:
        return 2
    else:
        return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
