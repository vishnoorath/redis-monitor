"""
Flask Application for Redis Monitor.
Provides REST API endpoints and a web UI for farm metadata comparison monitoring.
"""

from flask import Flask, request, jsonify, render_template, redirect, url_for
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
from src.sql import get_recent_farm_ids
from src.replication_monitor import get_replication_status, ReplicationMonitor
from src import settings_db


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

# Initialize settings database
settings_db.init_settings_db()


def _migrate_dotenv_into_db() -> None:
    """
    Seed each environment's Kafka brokers from the legacy .env KAFKA_BROKER,
    if and only if that env's brokers field is still empty. Idempotent —
    once a user has saved brokers via the settings page, this won't overwrite.

    For envs that the .env explicitly names (KAFKA_ENV), the brokers go only
    to that env. Other envs stay empty until the user fills them in via the
    Settings page.
    """
    legacy_brokers = (os.getenv('KAFKA_BROKER') or '').strip()
    legacy_env     = (os.getenv('KAFKA_ENV') or '').strip().lower()

    if not legacy_brokers:
        return

    # If the .env specifies a particular env, only seed that one.
    target_values = {legacy_env} if legacy_env else set()
    # Otherwise seed ALL envs whose brokers are empty so the user has
    # something to start from. They'll override per-env as needed.
    for env in settings_db.list_environments():
        if target_values and env['value'] not in target_values:
            continue
        if env['kafka_brokers']:
            continue  # user already configured
        settings_db.update_environment(
            env['value'],
            kafka_brokers=legacy_brokers,
            kafka_clustered=env['kafka_clustered'],
            settings=env.get('settings') or {},
        )

# Bring in `os` for the dotenv migration above
import os
_migrate_dotenv_into_db()


# ---------------------------------------------------------------------------
# Per-request ENV context
# ---------------------------------------------------------------------------

def _resolve_active_environment():
    """
    Return the active environment, falling back to:
      1. Query parameter (?env=prod)        — temporary override, useful for testing
      2. ACTIVE_ENVIRONMENT setting in DB   — set by the startup selector
      3. The first environment in the table (Dev) — first boot, no selection yet
    """
    override = request.args.get('env') if request else None
    if override:
        env = settings_db.get_environment(override)
        if env:
            return env
    active = settings_db.get_active_environment()
    if active:
        return active
    envs = settings_db.list_environments()
    return envs[0] if envs else None


@app.context_processor
def inject_environment():
    """Make `active_environment` available to every Jinja template."""
    return {'active_environment': _resolve_active_environment()}


# ---------------------------------------------------------------------------
# Startup ENV gate — must run before any UI route
# ---------------------------------------------------------------------------

@app.before_request
def require_environment():
    """
    Force the user to pick an environment on first hit. The startup selector
    writes ACTIVE_ENVIRONMENT to settings.db; subsequent requests bypass this.
    """
    # Skip for static + the selector itself + APIs (APIs have explicit ?env=)
    if request.path in ('/select-environment', '/health'):
        return None
    if request.path.startswith('/static') or request.path.startswith('/apidocs'):
        return None
    if request.path.startswith('/api/'):
        return None
    if settings_db.get_active_environment():
        return None
    return redirect(url_for('select_environment'))


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


@app.route('/monitor', methods=['GET'])
def momitor_from_db():
    """Redis-only monitor endpoint — removed."""
    return jsonify({
        'status': 'error',
        'message': 'Redis monitoring endpoints have been removed. Use SQL Replication instead.',
    }), 410


@app.route('/api/compare', methods=['POST'])
def compare_farms():
    """Redis-only comparison endpoint — removed."""
    return jsonify({
        'status': 'error',
        'message': 'Redis comparison endpoints have been removed.',
    }), 410


@app.route('/api/monitor/<farm_id>', methods=['GET'])
def monitor_farm_get(farm_id):
    """Redis-only monitor endpoint — removed."""
    return jsonify({
        'status': 'error',
        'message': 'Redis monitoring endpoints have been removed.',
    }), 410


@app.route('/api/monitor', methods=['POST'])
def monitor_farm_post():
    """Redis-only monitor endpoint — removed."""
    return jsonify({
        'status': 'error',
        'message': 'Redis monitoring endpoints have been removed.',
    }), 410


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


@app.route('/api/settings', methods=['GET', 'POST', 'DELETE'])
def get_settings():
    """
    Get, save, or delete application settings
    ---
    tags:
      - System
    parameters:
      - name: key
        in: query
        type: string
        required: false
        description: Optional key to get specific setting
      - name: body
        in: body
        schema:
          type: object
          properties:
            key:
              type: string
            value:
              type: string
            valueType:
              type: string
              enum: [STRING, JSON, INT, FLOAT, BOOL, DATE]
    responses:
      200:
        description: Current settings
    """
    if request.method == 'GET':
        # Get specific key or all settings
        key = request.args.get('key')
        if key:
            setting = settings_db.get_setting(key)
            if setting:
                value = settings_db.get_setting_parsed(key)
                return jsonify({
                    'status': 'success',
                    'key': setting['key'],
                    'value': value,
                    'valueType': setting['valueType']
                }), 200
            return jsonify({
                'status': 'error',
                'message': f'Setting "{key}" not found'
            }), 404

        # Get all settings
        all_settings = settings_db.get_all_settings()
        settings_dict = {}
        for s in all_settings:
            value = settings_db.get_setting_parsed(s['key'])
            settings_dict[s['key']] = value

        return jsonify({
            'status': 'success',
            'settings': settings_dict
        }), 200

    elif request.method == 'POST':
        # Save a setting
        data = request.get_json()
        if not data or 'key' not in data or 'value' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing key or value'
            }), 400

        key = data['key']
        value = data['value']
        value_type = data.get('valueType', 'STRING')

        settings_db.set_setting(key, value, value_type)
        return jsonify({
            'status': 'success',
            'message': f'Setting "{key}" saved successfully'
        }), 200

    elif request.method == 'DELETE':
        # Delete a setting
        key = request.args.get('key')
        if not key:
            return jsonify({
                'status': 'error',
                'message': 'Missing key parameter'
            }), 400

        deleted = settings_db.delete_setting(key)
        if deleted:
            return jsonify({
                'status': 'success',
                'message': f'Setting "{key}" deleted successfully'
            }), 200
        return jsonify({
            'status': 'error',
            'message': f'Setting "{key}" not found'
        }), 404


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


@app.route('/api/replication/table-counts', methods=['GET'])
def replication_table_counts():
    """
    Get table row counts comparison across replication servers
    
    Compares table row counts from primary server (10.10.98.47) against 
    secondary servers (10.10.98.66, 10.10.98.76, 10.10.98.100).
    Executes usp_GetTableCount_ForMonitoring_Replication stored procedure.
    ---
    tags:
      - Replication Monitoring
    responses:
      200:
        description: Replication status with table count comparisons
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            timestamp:
              type: string
              format: date-time
            primary_server:
              type: string
              example: 10.10.98.47
            all_servers:
              type: object
              description: Table counts from each server
            comparison_results:
              type: object
              description: Comparison of secondary servers against primary
            summary:
              type: object
              properties:
                total_servers:
                  type: integer
                  example: 4
                servers_with_differences:
                  type: integer
                  example: 1
                total_table_differences:
                  type: integer
                  example: 5
                tables_analyzed:
                  type: integer
                  example: 42
      500:
        description: Server error during comparison
    """
    try:
        results = get_replication_status()
        return jsonify(results), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n!!! REPLICATION MONITOR ERROR !!!")
        print(error_trace)
        print("!!! END ERROR !!!\n")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/replication/sync', methods=['POST'])
def sync_tables():
    """
    Sync specified tables from primary to secondary server.
    Calls usp_GenerateSyncScript_VR on primary to generate script, then executes on secondary.
    ---
    tags:
      - Replication Monitoring
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - server
            - tables
          properties:
            server:
              type: string
              example: 10.10.98.66
              description: Secondary server IP/name
            tables:
              type: array
              items:
                type: string
              example: ["Farms", "Cattles"]
              description: List of table names to sync
    responses:
      200:
        description: Sync results per table
      400:
        description: Missing required fields
      500:
        description: Server error
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body required'
            }), 400

        server = data.get('server')
        tables = data.get('tables', [])

        if not server:
            return jsonify({
                'status': 'error',
                'message': 'Missing required field: server'
            }), 400

        if not tables or not isinstance(tables, list):
            return jsonify({
                'status': 'error',
                'message': 'Missing or invalid field: tables (must be a non-empty array)'
            }), 400

        # Import and call the sync function.
        # Kafka brokers/env come from the currently active environment.
        from src.replication_monitor import sync_tables_to_secondary

        active = _resolve_active_environment()
        kafka_brokers   = active.get('kafka_brokers') if active else None
        kafka_env       = active.get('value') if active else None
        kafka_clustered = active.get('kafka_clustered') if active else None

        results = sync_tables_to_secondary(
            server,
            tables,
            kafka_brokers=kafka_brokers,
            kafka_env=kafka_env,
            kafka_clustered=kafka_clustered,
        )

        return jsonify(results), 200

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n!!! SYNC ERROR !!!")
        print(error_trace)
        print("!!! END ERROR !!!\n")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


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


@app.route('/select-environment', methods=['GET', 'POST'])
def select_environment():
    """
    On startup, force the user to pick Dev / Test / Uat / Prod.
    Persists the choice in settings.db → ACTIVE_ENVIRONMENT.
    """
    if request.method == 'POST':
        chosen = (request.form.get('env') or '').strip().lower()
        env = settings_db.get_environment(chosen)
        if env:
            settings_db.set_active_environment(chosen)
            return redirect(url_for('dashboard'))
        # Invalid choice — fall through and re-render selector

    environments = settings_db.list_environments()
    return render_template('env-selector.html', environments=environments)


@app.route('/', methods=['GET'])
def dashboard():
    """Render the web UI dashboard."""
    ignore_tables = settings_db.get_setting_parsed('IGNORE_TABLES_FOR_MONITORING') or []
    active = _resolve_active_environment()
    if active and active.get('settings', {}).get('ignore_tables'):
        ignore_tables = active['settings']['ignore_tables']
    return render_template('index.html', ignore_tables=ignore_tables)


@app.route('/sql-status', methods=['GET'])
def sql_status():
    """Render the SQL Replication Status page."""
    ignore_tables = settings_db.get_setting_parsed('IGNORE_TABLES_FOR_MONITORING') or []
    active = _resolve_active_environment()
    if active and active.get('settings', {}).get('ignore_tables'):
        ignore_tables = active['settings']['ignore_tables']
    return render_template('sql-status.html', ignore_tables=ignore_tables)


# ---------------------------------------------------------------------------
# CLR column override routes (managed in SQLite, pushed to secondary SQL Server)
# ---------------------------------------------------------------------------

@app.route('/settings/clr/add', methods=['POST'])
def clr_add():
    """Add or update a CLR column override in settings.db."""
    table_name = (request.form.get('table_name') or '').strip()
    column_name = (request.form.get('column_name') or '').strip()
    cast_as = (request.form.get('cast_as') or 'NVARCHAR(MAX)').strip()
    notes = (request.form.get('notes') or '').strip()
    if not table_name or not column_name:
        return jsonify({'status': 'error', 'message': 'table_name and column_name are required'}), 400
    settings_db.upsert_clr_override(table_name, column_name, cast_as, notes)
    return redirect(url_for('settings'))


@app.route('/settings/clr/delete', methods=['POST'])
def clr_delete():
    """Remove a CLR column override."""
    table_name = (request.form.get('table_name') or '').strip()
    column_name = (request.form.get('column_name') or '').strip()
    if not table_name or not column_name:
        return jsonify({'status': 'error', 'message': 'table_name and column_name are required'}), 400
    settings_db.delete_clr_override(table_name, column_name)
    return redirect(url_for('settings'))


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """
    Render and handle the per-environment settings page.
    Reads/writes both the Kafka brokers (per-env) and the app settings
    (refresh frequency, emails, ignore tables, servers) into the active env's
    settings_json blob.
    """
    active = _resolve_active_environment()
    if not active:
        return redirect(url_for('select_environment'))

    # Load the active env's settings.json (with sensible defaults)
    cfg = active.get('settings') or {}
    refresh_frequency = cfg.get('refresh_frequency', 30)
    notified_emails  = cfg.get('notified_emails', '')
    servers          = cfg.get('servers', [])
    ignore_tables    = '\n'.join(cfg.get('ignore_tables', []))

    # On POST, save everything back into the env's settings_json + Kafka config
    if request.method == 'POST':
        import json

        new_kafka_brokers = (request.form.get('kafka_brokers') or '').strip()
        new_kafka_clustered = 'kafka_clustered' in request.form

        refresh_frequency = int(request.form.get('refresh_frequency', '30') or 30)
        notified_emails   = request.form.get('notified_emails', '')

        ignore_tables_input = request.form.get('ignore_tables') or ''
        new_ignore_tables = [ln.strip() for ln in ignore_tables_input.split('\n') if ln.strip()]

        servers_json = request.form.get('servers') or '[]'
        try:
            new_servers = json.loads(servers_json) if servers_json else []
        except json.JSONDecodeError:
            new_servers = servers

        new_settings = {
            'refresh_frequency': refresh_frequency,
            'notified_emails': notified_emails,
            'ignore_tables': new_ignore_tables,
            'servers': new_servers,
        }

        settings_db.update_environment(
            active['value'],
            kafka_brokers=new_kafka_brokers,
            kafka_clustered=new_kafka_clustered,
            settings=new_settings,
        )

        # Re-read for the response template
        active = settings_db.get_environment(active['value'])
        cfg = active.get('settings') or {}
        refresh_frequency = cfg.get('refresh_frequency', 30)
        notified_emails   = cfg.get('notified_emails', '')
        servers           = cfg.get('servers', [])
        ignore_tables     = '\n'.join(cfg.get('ignore_tables', []))

        return render_template(
            'settings.html',
            active_environment=active,
            clr_overrides=settings_db.list_clr_overrides(),
            saved=True,
        )

    # CLR column overrides (managed in SQLite, pushed to secondary SQL Server on sync)
    clr_overrides = settings_db.list_clr_overrides()

    return render_template(
        'settings.html',
        active_environment=active,
        clr_overrides=clr_overrides,
        saved=False,
    )


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
