"""
Comparison module for Redis Monitor.
Compares farm metadata responses from old and new APIs using DeepDiff.
"""

from deepdiff import DeepDiff
import unicodedata
import re

# Option 1: Normalize strings (remove trailing/leading spaces)
def normalize(obj):
    """Strip whitespace and normalize unicode"""
    try:
        if obj is None:
            return None
        elif isinstance(obj, str):
            return re.sub(r'\s+', ' ', obj).strip()  # Replace multiple spaces with single space
        elif isinstance(obj, bool):
            return obj  # Don't process booleans
        elif isinstance(obj, (int, float)):
            return obj  # Don't process numbers
        elif isinstance(obj, dict):
            return {k: normalize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [normalize(item) for item in obj]
        else:
            return obj  # Return as-is for other types
    except Exception as e:
        print(f"Error normalizing {type(obj)}: {e}")
        return obj
    
def compare_responses(old_response, new_response):
    """
    Compare farm metadata responses from old and new APIs.

    Args:
        old_response (dict): Response from old database-based API.
        new_response (dict): Response from new Redis-based API.

    Returns:
        dict: Comparison result with detailed differences and summary.
    """
    try:
        if old_response is None or new_response is None:
            return {
                'identical': False,
                'error': 'One or both API responses failed or returned None',
                'has_differences': True,
                'differences': {}
            }

        # Normalize responses
        old_response = normalize(old_response)
        new_response = normalize(new_response)
        
        # Use DeepDiff to compare the two responses
        diff = DeepDiff(old_response, new_response, ignore_order=False,  
                exclude_regex_paths=[
                    r".*\['cattleData'\].*\['lactationEndDate'\]"
                ])
        
        # Generate summary
        is_identical = len(diff) == 0

        # Convert DeepDiff object to dictionary for JSON serialization
        diff_dict = diff.to_dict() if diff else {}

        # Create result structure
        result = {
            'identical': is_identical,
            'has_differences': not is_identical,
            'differences': diff_dict,
            'summary': {
                'values_changed': len(diff.get('values_changed', {})),
                'items_added': len(diff.get('items_added', [])),
                'items_removed': len(diff.get('items_removed', [])),
                'type_changes': len(diff.get('type_changes', {})),
                'repetition_changes': len(diff.get('repetition_change', {}))
            }
        }

        return result
    
    except Exception as e:
        print(f"Error in compare_responses: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'identical': False,
            'error': f'Comparison error: {str(e)}',
            'has_differences': True,
            'differences': {}
        }


def get_comparison_summary(comparison_result):
    """
    Generate a human-readable summary of comparison results.

    Args:
        comparison_result (dict): Result from compare_responses function.

    Returns:
        str: Formatted summary string.
    """
    if comparison_result.get('error'):
        return f"❌ Comparison error: {comparison_result['error']}"

    if comparison_result['identical']:
        return "✓ Responses are IDENTICAL - No differences found"

    summary = comparison_result['summary']
    lines = ["❌ Responses differ:"]

    if summary['values_changed'] > 0:
        lines.append(f"  • {summary['values_changed']} value(s) changed")
    if summary['items_added'] > 0:
        lines.append(f"  • {summary['items_added']} item(s) added in new API")
    if summary['items_removed'] > 0:
        lines.append(f"  • {summary['items_removed']} item(s) removed in new API")
    if summary['type_changes'] > 0:
        lines.append(f"  • {summary['type_changes']} type change(s)")
    if summary['repetition_changes'] > 0:
        lines.append(f"  • {summary['repetition_changes']} repetition change(s)")

    return '\n'.join(lines)


if __name__ == '__main__':
    # For testing comparison
    obj_a = {"id": 1, "meta": {"status": "active"}, "tags": [1, 2]}
    obj_b = {"id": 1, "meta": {"status": "inactive"}, "tags": [1, 3]}

    result = compare_responses(obj_a, obj_b)
    print(get_comparison_summary(result))
    print(f"\nFull result: {result}")
