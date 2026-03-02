"""
HTML Reporter module for Redis Monitor.
Generates formatted HTML reports with diff-style coloring and highlighting.
"""

import json
from pathlib import Path
from datetime import datetime
from src.config import Config


class HTMLReporter:
    """Generates HTML reports with diff-style formatting."""

    # Color scheme for HTML report
    COLORS = {
        'added': '#90EE90',      # Light green for additions
        'removed': '#FFB6C6',    # Light red for removals
        'changed': '#FFD700',    # Gold for changes
        'identical': '#E8F5E9',  # Very light green for identical
        'error': '#FFCDD2',      # Light red for errors
    }

    @staticmethod
    def escape_html(text):
        """Escape HTML special characters."""
        if not isinstance(text, str):
            text = json.dumps(text, indent=2)
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))

    @staticmethod
    def json_to_html_pre(data):
        """Convert JSON data to formatted HTML pre element."""
        json_str = json.dumps(data, indent=2, default=str)
        escaped = HTMLReporter.escape_html(json_str)
        return f"<pre style='background-color: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;'>{escaped}</pre>"

    @staticmethod
    def format_diff_item(key, value, diff_type='changed'):
        """Format a diff item with color coding."""
        color = HTMLReporter.COLORS.get(diff_type, '#FFF')
        icon = {
            'added': '✓',
            'removed': '✗',
            'changed': '≠',
            'identical': '≡'
        }.get(diff_type, '•')

        escaped_key = HTMLReporter.escape_html(str(key))
        escaped_value = HTMLReporter.escape_html(str(value))

        return f"""
        <div style="background-color: {color}; padding: 8px; margin: 4px 0; border-left: 4px solid {'#4CAF50' if diff_type == 'added' else '#F44336' if diff_type == 'removed' else '#FFC107' if diff_type == 'changed' else '#E8F5E9'}; border-radius: 2px;">
            <strong>{icon} {escaped_key}:</strong> {escaped_value}
        </div>
        """

    @classmethod
    def generate_comparison_html(cls, farm_id, old_api, new_api, comparison):
        """Generate HTML for a single farm comparison."""
        html = f"""
        <div class="farm-section">
            <h3>Farm ID: <code>{farm_id}</code></h3>
            
            <div class="comparison-status">
        """

        # Check API results
        old_status = "✓ Success" if old_api else "✗ Failed"
        new_status = "✓ Success" if new_api else "✗ Failed"
        old_color = "#E8F5E9" if old_api else "#FFCDD2"
        new_color = "#E8F5E9" if new_api else "#FFCDD2"

        html += f"""
                <div style="background-color: {old_color}; padding: 10px; margin: 10px 0; border-radius: 4px;">
                    <strong>OLD DB API:</strong> {old_status}
                    {f'({len(json.dumps(old_api))} bytes)' if old_api else ''}
                </div>
                <div style="background-color: {new_color}; padding: 10px; margin: 10px 0; border-radius: 4px;">
                    <strong>NEW REDIS API:</strong> {new_status}
                    {f'({len(json.dumps(new_api))} bytes)' if new_api else ''}
                </div>
            </div>
        """

        # Comparison result
        if comparison.get('error'):
            html += f"""
            <div style="background-color: {cls.COLORS['error']}; padding: 10px; margin: 10px 0; border-radius: 4px;">
                <strong>Comparison Error:</strong> {cls.escape_html(comparison['error'])}
            </div>
            """
        elif comparison['identical']:
            html += f"""
            <div style="background-color: {cls.COLORS['identical']}; padding: 10px; margin: 10px 0; border-radius: 4px; border-left: 4px solid #4CAF50;">
                <strong style="font-size: 1.1em;">✓ Responses are IDENTICAL</strong>
                <p>No differences found between old and new API responses.</p>
            </div>
            """
        else:
            # Show differences
            summary = comparison['summary']
            html += f"""
            <div style="background-color: #FFEBEE; padding: 10px; margin: 10px 0; border-radius: 4px; border-left: 4px solid #F44336;">
                <strong style="font-size: 1.1em;">❌ Responses Differ</strong>
                <ul style="margin: 5px 0; padding-left: 20px;">
            """

            if summary['values_changed'] > 0:
                html += f"<li>{summary['values_changed']} value(s) changed</li>"
            if summary['items_added'] > 0:
                html += f"<li>{summary['items_added']} item(s) added in new API</li>"
            if summary['items_removed'] > 0:
                html += f"<li>{summary['items_removed']} item(s) removed in new API</li>"
            if summary['type_changes'] > 0:
                html += f"<li>{summary['type_changes']} type change(s)</li>"

            html += """
                </ul>
            </div>
            """

            # Show detailed differences
            html += """
            <details style="margin: 10px 0;">
                <summary style="cursor: pointer; font-weight: bold; padding: 10px; background-color: #F5F5F5; border-radius: 4px;">
                    Show Detailed Differences
                </summary>
                <div style="margin-top: 10px;">
            """

            diff = comparison.get('differences', {})

            if diff.get('values_changed'):
                html += "<h4 style='color: #FF9800;'>Values Changed:</h4>"
                for key, change in diff['values_changed'].items():
                    old_val = change.get('old_value', 'N/A')
                    new_val = change.get('new_value', 'N/A')
                    escaped_key = cls.escape_html(str(key))
                    escaped_old = cls.escape_html(str(old_val))
                    escaped_new = cls.escape_html(str(new_val))
                    html += f"""
                    <div style="background-color: #FFF3E0; padding: 8px; margin: 4px 0; border-left: 4px solid #FF9800; border-radius: 2px;">
                        <strong>{escaped_key}</strong><br>
                        <span style="color: #D32F2F;">- {escaped_old}</span><br>
                        <span style="color: #388E3C;">+ {escaped_new}</span>
                    </div>
                    """

            if diff.get('items_added'):
                html += "<h4 style='color: #4CAF50;'>Items Added (in New API):</h4>"
                for item in diff['items_added']:
                    escaped_item = cls.escape_html(str(item))
                    html += f"""
                    <div style="background-color: #E8F5E9; padding: 8px; margin: 4px 0; border-left: 4px solid #4CAF50; border-radius: 2px;">
                        <strong>✓ {escaped_item}</strong>
                    </div>
                    """

            if diff.get('items_removed'):
                html += "<h4 style='color: #D32F2F;'>Items Removed (from New API):</h4>"
                for item in diff['items_removed']:
                    escaped_item = cls.escape_html(str(item))
                    html += f"""
                    <div style="background-color: #FFEBEE; padding: 8px; margin: 4px 0; border-left: 4px solid #D32F2F; border-radius: 2px;">
                        <strong>✗ {escaped_item}</strong>
                    </div>
                    """

            html += """
                </div>
            </details>
            """

        # Show raw data in collapsible sections
        html += """
        <details style="margin: 10px 0;">
            <summary style="cursor: pointer; font-weight: bold; padding: 10px; background-color: #F5F5F5; border-radius: 4px;">
                Show Raw API Responses
            </summary>
            <div style="margin-top: 10px;">
        """

        if old_api:
            html += "<h4>Old DB API Response:</h4>"
            html += cls.json_to_html_pre(old_api)
        else:
            html += "<p style='color: #D32F2F;'><strong>Old DB API Response:</strong> Not available (request failed)</p>"

        if new_api:
            html += "<h4>New Redis API Response:</h4>"
            html += cls.json_to_html_pre(new_api)
        else:
            html += "<p style='color: #D32F2F;'><strong>New Redis API Response:</strong> Not available (request failed)</p>"

        html += """
            </div>
        </details>
        </div>
        """

        return html

    @classmethod
    def generate_html_report(cls, results, test_run_id=None):
        """
        Generate comprehensive HTML report of all comparisons.

        Args:
            results (list): List of comparison results for all farms.
            test_run_id (str, optional): Test run identifier.

        Returns:
            str: Path to generated HTML report file.
        """
        if test_run_id is None:
            test_run_id = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Calculate statistics
        total = len(results)
        identical = sum(1 for r in results if r['comparison'].get('identical', False))
        with_differences = sum(1 for r in results if r['comparison'].get('has_differences', False))
        with_errors = sum(1 for r in results if r['comparison'].get('error') or 
                         r['old_api'] is None or r['new_api'] is None)

        # HTML header with CSS
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Redis Monitor Report - {test_run_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}

        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}

        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}

        .summary-card h3 {{
            font-size: 2em;
            margin-bottom: 10px;
            font-weight: bold;
        }}

        .summary-card.identical h3 {{
            color: #4CAF50;
        }}

        .summary-card.different h3 {{
            color: #FF9800;
        }}

        .summary-card.error h3 {{
            color: #F44336;
        }}

        .summary-card p {{
            color: #666;
            font-size: 0.95em;
        }}

        .status-message {{
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            font-weight: bold;
            font-size: 1.1em;
        }}

        .status-message.success {{
            background-color: #E8F5E9;
            color: #2E7D32;
            border-left: 5px solid #4CAF50;
        }}

        .status-message.warning {{
            background-color: #FFF3E0;
            color: #E65100;
            border-left: 5px solid #FF9800;
        }}

        .status-message.error {{
            background-color: #FFEBEE;
            color: #B71C1C;
            border-left: 5px solid #F44336;
        }}

        .results {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}

        .farm-section {{
            border: 1px solid #ddd;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            background: #fafafa;
        }}

        .farm-section h3 {{
            color: #667eea;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}

        .farm-section code {{
            background-color: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}

        .comparison-status {{
            margin: 15px 0;
        }}

        details {{
            margin: 15px 0;
            padding: 10px;
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}

        details summary {{
            padding: 10px;
            background-color: #f5f5f5;
            cursor: pointer;
            border-radius: 4px;
            user-select: none;
        }}

        details summary:hover {{
            background-color: #e8e8e8;
        }}

        details[open] summary {{
            border-bottom: 1px solid #ddd;
            margin-bottom: 10px;
        }}

        pre {{
            overflow-x: auto;
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 4px;
            border: 1px solid #ddd;
        }}

        footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #999;
            border-top: 1px solid #ddd;
        }}

        /* Diff colors */
        .diff-added {{
            background-color: #E8F5E9;
            border-left: 4px solid #4CAF50;
        }}

        .diff-removed {{
            background-color: #FFEBEE;
            border-left: 4px solid #F44336;
        }}

        .diff-changed {{
            background-color: #FFF3E0;
            border-left: 4px solid #FF9800;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .summary {{
                grid-template-columns: 1fr;
            }}

            header h1 {{
                font-size: 1.8em;
            }}

            .container {{
                padding: 10px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 Redis Monitor Report</h1>
            <p>Farm Metadata Comparison: OLD DB API vs NEW REDIS API</p>
            <p>Run ID: <code>{test_run_id}</code> | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        <div class="summary">
            <div class="summary-card identical">
                <h3>{identical}</h3>
                <p>Identical Responses</p>
            </div>
            <div class="summary-card different">
                <h3>{with_differences}</h3>
                <p>Different Responses</p>
            </div>
            <div class="summary-card error">
                <h3>{with_errors}</h3>
                <p>Errors/Failures</p>
            </div>
            <div class="summary-card">
                <h3>{total}</h3>
                <p>Total Farms</p>
            </div>
        </div>
"""

        # Status message
        if with_errors > 0:
            html += f"""
        <div class="status-message error">
            ⚠ {with_errors} farm(s) failed API requests. Check details below for more information.
        </div>
"""
        elif with_differences > 0:
            html += f"""
        <div class="status-message warning">
            ❌ {with_differences} farm(s) have differences between old and new APIs. Review below to identify the discrepancies.
        </div>
"""
        else:
            html += """
        <div class="status-message success">
            ✓ All farm metadata is synchronized! No discrepancies found between APIs.
        </div>
"""

        # Results section
        html += """
        <div class="results">
            <h2>Comparison Results</h2>
"""

        for result in results:
            farm_id = result['farm_id']
            old_api = result['old_api']
            new_api = result['new_api']
            comparison = result['comparison']

            html += cls.generate_comparison_html(farm_id, old_api, new_api, comparison)

        # Footer
        html += f"""
        </div>

        <footer>
            <p>Redis Monitor - Farm Metadata Comparison Tool</p>
            <p>Report generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}</p>
        </footer>
    </div>
</body>
</html>
"""

        # Save to HTML file
        filename = f"comparison_report_{test_run_id}.html"
        filepath = Path(Config.OUTPUT_DIR) / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✓ HTML report saved to: {filepath}")
        return str(filepath)


if __name__ == '__main__':
    # Test HTML reporter
    test_results = [
        {
            'farm_id': '13f9ef67-19b0-4e3d-bec5-6dd15247492c',
            'old_api': {'id': 1, 'status': 'active', 'name': 'Test Farm'},
            'new_api': {'id': 1, 'status': 'active', 'name': 'Test Farm'},
            'comparison': {
                'identical': True,
                'has_differences': False,
                'differences': {},
                'summary': {
                    'values_changed': 0,
                    'items_added': 0,
                    'items_removed': 0,
                    'type_changes': 0,
                    'repetition_changes': 0
                }
            },
            'timestamp': datetime.now().isoformat()
        }
    ]

    HTMLReporter.generate_html_report(test_results)
