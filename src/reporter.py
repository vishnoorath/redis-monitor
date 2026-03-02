"""
Reporter module for Redis Monitor.
Handles output reporting to console and JSON files.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from src.config import Config
from src.html_reporter import HTMLReporter


class Reporter:
    """Handles reporting comparison results to console and files."""

    def __init__(self):
        """Initialize reporter and ensure output directory exists."""
        Config.ensure_output_dir()
        self.output_dir = Config.OUTPUT_DIR

    def print_farm_comparison(self, farm_id, old_api_result, new_api_result, comparison):
        """
        Print formatted farm comparison results to console.

        Args:
            farm_id (str): Farm ID being compared.
            old_api_result (dict or None): Result from old API.
            new_api_result (dict or None): Result from new API.
            comparison (dict): Comparison result from comparison module.
        """
        print("\n" + "=" * 80)
        print(f"FARM ID: {farm_id}")
        print("=" * 80)

        # Check API results
        if old_api_result is None:
            print("❌ OLD DB API: Request FAILED")
        else:
            print(f"✓ OLD DB API: Success ({len(json.dumps(old_api_result))} bytes)")

        if new_api_result is None:
            print("❌ NEW REDIS API: Request FAILED")
        else:
            print(f"✓ NEW REDIS API: Success ({len(json.dumps(new_api_result))} bytes)")

        # Print comparison summary
        print("\nCOMPARISON RESULT:")
        print("-" * 80)

        if comparison.get('error'):
            print(f"Error: {comparison['error']}")
        elif comparison['identical']:
            print("✓ Responses are IDENTICAL - No differences found")
        else:
            summary = comparison['summary']
            print("❌ Responses differ:")
            if summary['values_changed'] > 0:
                print(f"  • {summary['values_changed']} value(s) changed")
            if summary['items_added'] > 0:
                print(f"  • {summary['items_added']} item(s) added in new API")
            if summary['items_removed'] > 0:
                print(f"  • {summary['items_removed']} item(s) removed in new API")
            if summary['type_changes'] > 0:
                print(f"  • {summary['type_changes']} type change(s)")

    def generate_json_report(self, results, test_run_id=None):
        """
        Generate comprehensive JSON report of all comparisons.

        Args:
            results (list): List of comparison results for all farms.
            test_run_id (str, optional): Test run identifier.

        Returns:
            str: Path to generated JSON report file.
        """
        if test_run_id is None:
            test_run_id = datetime.now().strftime('%Y%m%d_%H%M%S')

        report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'test_run_id': test_run_id,
                'total_farms_compared': len(results),
                'farms_identical': sum(1 for r in results if r['comparison'].get('identical', False)),
                'farms_with_differences': sum(1 for r in results if r['comparison'].get('has_differences', False)),
                'farms_with_errors': sum(1 for r in results if r['comparison'].get('error') or 
                                         r['old_api'] is None or r['new_api'] is None)
            },
            'results': results
        }

        # Save to JSON file
        filename = f"comparison_report_{test_run_id}.json"
        filepath = Path(self.output_dir) / filename

        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"✓ JSON report saved to: {filepath}")
        return str(filepath)

    def generate_html_report(self, results, test_run_id=None):
        """
        Generate comprehensive HTML report with diff-style formatting.

        Args:
            results (list): List of comparison results for all farms.
            test_run_id (str, optional): Test run identifier.

        Returns:
            str: Path to generated HTML report file.
        """
        return HTMLReporter.generate_html_report(results, test_run_id)

    def generate_reports(self, results, test_run_id=None):
        """
        Generate both JSON and HTML reports.

        Args:
            results (list): List of comparison results for all farms.
            test_run_id (str, optional): Test run identifier.

        Returns:
            tuple: (json_filepath, html_filepath)
        """
        if test_run_id is None:
            test_run_id = datetime.now().strftime('%Y%m%d_%H%M%S')

        json_path = self.generate_json_report(results, test_run_id)
        html_path = self.generate_html_report(results, test_run_id)

        return json_path, html_path

    def print_summary(self, results):
        """
        Print summary statistics of all comparisons.

        Args:
            results (list): List of comparison results for all farms.
        """
        total = len(results)
        identical = sum(1 for r in results if r['comparison'].get('identical', False))
        with_differences = sum(1 for r in results if r['comparison'].get('has_differences', False))
        with_errors = sum(1 for r in results if r['comparison'].get('error') or 
                         r['old_api'] is None or r['new_api'] is None)

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total farms compared: {total}")
        print(f"Identical responses: {identical} ✓")
        print(f"Different responses: {with_differences} ❌")
        print(f"Errors/Failures: {with_errors} ⚠")

        if with_differences == 0 and with_errors == 0:
            print("\n✓ All farm metadata is synchronized! No discrepancies found.")
        elif with_errors > 0:
            print(f"\n⚠ {with_errors} farm(s) failed API requests. Check logs above.")
        else:
            print(f"\n❌ {with_differences} farm(s) have differences between old and new APIs.")

        print("=" * 80)


if __name__ == '__main__':
    # Test reporter
    reporter = Reporter()

    test_results = [
        {
            'farm_id': '13f9ef67-19b0-4e3d-bec5-6dd15247492c',
            'old_api': {'id': 1, 'status': 'active'},
            'new_api': {'id': 1, 'status': 'active'},
            'comparison': {'identical': True, 'has_differences': False, 'differences': {}, 'summary': {}}
        }
    ]

    reporter.generate_json_report(test_results)
    reporter.print_summary(test_results)
