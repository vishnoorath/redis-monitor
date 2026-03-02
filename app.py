"""
Flask Application for Redis Monitor.
Provides REST API endpoints and a web UI for farm metadata comparison monitoring.
"""

from flask import Flask, request, jsonify, render_template
from datetime import datetime
import sys
from pathlib import Path
from flasgger import Flasgger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.auth import generate_token
from src.api_client import APIClient
from src.comparison import compare_responses
from src.reporter import Reporter
from src.html_reporter import HTMLReporter


# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Configure Swagger/Flasgger
app.config['SWAGGER'] = {
    'title': 'Redis Monitor API',
    'version': '1.0.0',
    'description': 'Farm metadata comparison monitoring between OLD DB API and NEW REDIS API',
    'uiversion': 3
}

# Initialize Swagger/Flasgger
swagger = Flasgger(app)

# Initialize components
api_client = APIClient()
reporter = Reporter()
Config.ensure_output_dir()


def monitor_single_farm(farm_id):
    """
    Monitor a single farm by fetching and comparing metadata.

    Args:
        farm_id (str): The farm ID to monitor.

    Returns:
        dict: Result containing farm data and comparison.
    """
    try:
        # Generate token
        token = generate_token(farm_id)

        # Fetch from both APIs
        old_api_data, new_api_data = api_client.fetch_both(farm_id, token)

        # Compare responses
        comparison = compare_responses(old_api_data, new_api_data)

        # Return result
        return {
            'farm_id': farm_id,
            'status': 'success',
            'old_api': old_api_data,
            'new_api': new_api_data,
            'comparison': comparison,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        return {
            'farm_id': farm_id,
            'status': 'error',
            'error': str(e),
            'old_api': None,
            'new_api': None,
            'comparison': {
                'error': str(e),
                'has_differences': True
            },
            'timestamp': datetime.now().isoformat()
        }


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    ---
    tags:
      - System
    responses:
      200:
        description: Server is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: healthy
            service:
              type: string
              example: Redis Monitor API
            timestamp:
              type: string
              format: date-time
              example: 2026-03-02T10:30:45.123456
    """
    return jsonify({
        'status': 'healthy',
        'service': 'Redis Monitor API',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/api/compare', methods=['POST'])
def compare_farms():
    """
    Compare farm metadata between old and new APIs
    ---
    tags:
      - Comparison
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - farmIds
          properties:
            farmIds:
              type: array
              items:
                type: string
              example: ["farm-id-1", "farm-id-2"]
              description: Array of farm IDs to compare
    responses:
      200:
        description: Comparison completed successfully
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            summary:
              type: object
              properties:
                total:
                  type: integer
                  example: 2
                identical:
                  type: integer
                  example: 1
                different:
                  type: integer
                  example: 1
                errors:
                  type: integer
                  example: 0
            results:
              type: array
              items:
                type: object
            timestamp:
              type: string
              format: date-time
      400:
        description: Invalid request (missing or invalid farmIds)
      500:
        description: Server error
    """
    try:
        # Get request data
        data = request.get_json()

        if not data or 'farmIds' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing required field: farmIds',
                'example': {
                    'farmIds': ['farm-id-1', 'farm-id-2']
                }
            }), 400

        farm_ids = data.get('farmIds', [])

        if not isinstance(farm_ids, list) or len(farm_ids) == 0:
            return jsonify({
                'status': 'error',
                'message': 'farmIds must be a non-empty array'
            }), 400

        # Monitor each farm
        results = []
        for farm_id in farm_ids:
            result = monitor_single_farm(farm_id)
            results.append(result)

        # Calculate statistics
        total = len(results)
        identical = sum(1 for r in results if r.get('status') == 'success' and r['comparison'].get('identical', False))
        different = sum(1 for r in results if r.get('status') == 'success' and r['comparison'].get('has_differences', False))
        errors = sum(1 for r in results if r.get('status') == 'error')

        response = {
            'status': 'success',
            'summary': {
                'total': total,
                'identical': identical,
                'different': different,
                'errors': errors
            },
            'results': results,
            'timestamp': datetime.now().isoformat()
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }), 500


@app.route('/api/monitor/<farm_id>', methods=['GET'])
def monitor_farm_get(farm_id):
    """
    Monitor a single farm (GET endpoint)
    ---
    tags:
      - Monitoring
    parameters:
      - in: path
        name: farm_id
        type: string
        required: true
        description: The farm ID to monitor
        example: farm-id-1
    responses:
      200:
        description: Farm comparison completed successfully
        schema:
          type: object
          properties:
            farm_id:
              type: string
            status:
              type: string
              enum: [success, error]
            comparison:
              type: object
            timestamp:
              type: string
              format: date-time
      500:
        description: Error monitoring farm
    """
    result = monitor_single_farm(farm_id)

    if result['status'] == 'error':
        return jsonify(result), 500
    else:
        return jsonify(result), 200


@app.route('/api/monitor', methods=['POST'])
def monitor_farm_post():
    """
    Monitor a single farm (POST endpoint)
    ---
    tags:
      - Monitoring
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - farmId
          properties:
            farmId:
              type: string
              example: farm-id-1
              description: The farm ID to monitor
    responses:
      200:
        description: Farm comparison completed successfully
        schema:
          type: object
          properties:
            farm_id:
              type: string
            status:
              type: string
              enum: [success, error]
            comparison:
              type: object
            timestamp:
              type: string
              format: date-time
      400:
        description: Missing required field farmId
      500:
        description: Error monitoring farm
    """
    try:
        data = request.get_json()

        if not data or 'farmId' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing required field: farmId'
            }), 400

        farm_id = data.get('farmId')
        result = monitor_single_farm(farm_id)

        if result['status'] == 'error':
            return jsonify(result), 500
        else:
            return jsonify(result), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """
    Get current API configuration
    ---
    tags:
      - System
    responses:
      200:
        description: Current configuration
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            config:
              type: object
              properties:
                old_api_endpoint:
                  type: string
                  example: http://api.internal:8080/api/farms
                new_api_endpoint:
                  type: string
                  example: http://redis-api.internal:8080/api/farms
                request_timeout:
                  type: integer
                  example: 30
    """
    return jsonify({
        'status': 'success',
        'config': {
            'old_api_endpoint': Config.OLD_API_ENDPOINT,
            'new_api_endpoint': Config.NEW_API_ENDPOINT,
            'request_timeout': Config.REQUEST_TIMEOUT
        }
    }), 200


@app.route('/api/docs', methods=['GET'])
def api_documentation():
    """
    API Documentation endpoint
    ---
    tags:
      - System
    responses:
      200:
        description: API Documentation information
        schema:
          type: object
          properties:
            service:
              type: string
              example: Redis Monitor API
            version:
              type: string
              example: 1.0.0
            swagger_ui:
              type: string
              example: /apidocs/
            swagger_json:
              type: string
              example: /apispec.json
    """
    return jsonify({
        'service': 'Redis Monitor API',
        'version': '1.0.0',
        'documentation': 'OpenAPI/Swagger documentation is available',
        'swagger_ui': 'Visit /apidocs/ for interactive Swagger UI',
        'swagger_spec': 'Visit /apispec.json for OpenAPI specification',
        'info': {
            'title': 'Redis Monitor API',
            'description': 'Farm metadata comparison monitoring between OLD DB API and NEW REDIS API',
            'version': '1.0.0'
        }
    }), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found',
        'hint': 'Check /api/docs for available endpoints'
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({
        'status': 'error',
        'message': 'Method not allowed',
        'hint': 'Check /api/docs for correct HTTP methods'
    }), 405


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500


@app.route('/', methods=['GET'])
def dashboard():
    """Render the web UI dashboard."""
    return render_template('index.html')


@app.route('/compare', methods=['POST'])
def compare_web():
    """
    Web UI endpoint for comparing farms.
    Accepts form data and renders report inline.
    """
    import traceback
    try:
        # Get farm IDs from form
        farm_ids_input = request.form.get('farm_ids', '').strip()
        generate_reports = 'generate_reports' in request.form

        if not farm_ids_input:
            return render_template('index.html', error='Please enter at least one farm ID'), 400

        # Parse farm IDs - support both comma-separated and newline-separated
        farm_ids = []
        for line in farm_ids_input.split('\n'):
            # Handle comma-separated values
            for item in line.split(','):
                item = item.strip()
                if item:
                    farm_ids.append(item)

        if not farm_ids:
            return render_template('index.html', error='Please enter valid farm IDs'), 400

        # Monitor each farm
        results = []
        test_run_id = datetime.now().strftime('%Y%m%d_%H%M%S')

        for farm_id in farm_ids:
            result = monitor_single_farm(farm_id)
            results.append(result)

            # Only keep essential data for template rendering
            # Remove large response bodies from display if needed
            result_copy = result.copy()
            results[-1] = result_copy

        # Calculate statistics
        total = len(results)
        identical = sum(1 for r in results if r.get('status') == 'success' and r['comparison'].get('identical', False))
        different = sum(1 for r in results if r.get('status') == 'success' and r['comparison'].get('has_differences', False))
        errors = sum(1 for r in results if r.get('status') == 'error')

        summary = {
            'total': total,
            'identical': identical,
            'different': different,
            'errors': errors
        }

        # Render report template (no files written to disk)
        return render_template(
            'report.html',
            summary=summary,
            results=results,
            test_run_id=test_run_id,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            report_paths=None
        )

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"\n!!! TEMPLATE ERROR !!!")
        print(error_trace)
        print("!!! END ERROR !!!\n")
        return render_template('index.html', error=f'Error processing request: {str(e)}\n\nTrace:\n{error_trace}'), 500


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("REDIS MONITOR - REST API Server + Web UI")
    print("=" * 80)
    print("\nStarting Flask app...")
    print("\n🌐 Web UI Available:")
    print("  • http://localhost:5000/            - Dashboard & comparison form")
    print("\n📡 Available API Endpoints:")
    print("  • GET  /health              - Health check")
    print("  • POST /api/compare         - Compare multiple farms (API)")
    print("  • GET  /api/monitor/{id}    - Monitor single farm (GET)")
    print("  • POST /api/monitor         - Monitor single farm (POST)")
    print("  • GET  /api/config          - Get configuration")
    print("  • GET  /api/docs            - API documentation")
    print("\n" + "=" * 80)
    print("Server running at: http://localhost:5000")
    print("  • Web Dashboard: http://localhost:5000/")
    print("  • API Docs: http://localhost:5000/api/docs")
    print("=" * 80 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
