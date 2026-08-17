"""
Flask Application for Redis Monitor.
Provides REST API endpoints and a web UI for farm metadata comparison monitoring.
"""

from flask import Flask, request, jsonify, render_template, redirect, url_for, make_response
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


# Valid settings tabs (also used by the per-tab GET endpoint below)
SETTINGS_TABS = ('general', 'kafka', 'databases', 'clr')


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


# One-time bootstrap: seed each env's settings.servers list (per-env
# PER_ENV_SERVERS overrides in settings_db.py — UAT has a different cluster
# than dev/test/prod). Every config is sourced from settings.db; there are
# no .env fallbacks for the database layer.
settings_db.seed_legacy_servers_into_envs()


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
    """Make `active_environment` and `all_environments` available to every Jinja template."""
    active = _resolve_active_environment()
    all_envs = settings_db.list_environments()

    # Strip passwords before exposing server lists to templates so the
    # browser never sees credentials. Passwords are only updated via the
    # dedicated Edit dialog (which posts them back to the server).
    def _safe_servers(env):
        srvs = (env.get('settings') or {}).get('servers', [])
        safe = []
        for s in srvs:
            safe.append({
                'server':       s.get('server', ''),
                'user':         s.get('user', ''),
                'db':           s.get('db', 'NitaraDB'),
                'port':         s.get('port', '1433') or '1433',
                'isPrimary':    bool(s.get('isPrimary', False)),
                'sync_to_kafka': bool(s.get('sync_to_kafka', False)),
                'disabled':     bool(s.get('disabled', False)),
                'has_password': bool(s.get('password', '') or ''),
            })
        return safe

    # Compute warning flags for the top-bar env switcher so users can see
    # which envs are missing critical config (kafka brokers, primary DB,
    # any secondary DB).
    for env in all_envs:
        servers = _safe_servers(env)
        env['_warning'] = (
            not env.get('kafka_brokers') or
            not any(s.get('isPrimary') for s in servers) or
            not any((not s.get('isPrimary')) and not s.get('disabled') for s in servers)
        )
        env['_safe_servers'] = servers

    if active:
        active['_safe_servers'] = _safe_servers(active)

    return {
        'active_environment': active,
        'all_environments':    all_envs,
    }


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
        # sync_to_kafka is now PER-DATABASE — looked up from the target server's
        # entry in the env's settings.servers list.
        from src.replication_monitor import sync_tables_to_secondary

        active = _resolve_active_environment()
        kafka_brokers   = active.get('kafka_brokers') if active else None
        kafka_env       = active.get('value') if active else None
        kafka_clustered = active.get('kafka_clustered') if active else None

        # Find the target server's sync_to_kafka flag from the env's servers list.
        # Disabled servers are skipped from sync entirely.
        # The API receives `server` as "IP:port" (e.g. "10.10.98.26:31813") but
        # the env's settings.servers[*] stores `server` as just the IP and
        # `port` as a separate field. Build a `server:port` key from each env
        # entry and compare to the API input. UAT has two SQL Servers on the
        # same IP (10.10.98.26:31812 primary / 10.10.98.26:31813 secondary) so
        # matching on just the IP would always pick the primary.
        sync_to_kafka = False
        server_disabled = False
        if active:
            for srv in (active.get('settings') or {}).get('servers', []):
                srv_key = f"{srv.get('server','')}:{srv.get('port','1433') or '1433'}"
                if srv_key == server:
                    server_disabled = bool(srv.get('disabled', False))
                    if not server_disabled:
                        sync_to_kafka = bool(srv.get('sync_to_kafka', False))
                    break

        if server_disabled:
            return {
                'status': 'success',
                'server': server,
                'table_count': len(tables),
                'results': [
                    {
                        'table': t,
                        'status': 'skipped',
                        'error': 'server is disabled in settings',
                        'kafka_published': 0,
                        'sync_to_kafka': False,
                        'missing_rows': 0,
                        'rows_affected': 0,
                    } for t in tables
                ],
            }

        results = sync_tables_to_secondary(
            server,
            tables,
            kafka_brokers=kafka_brokers,
            kafka_env=kafka_env,
            kafka_clustered=kafka_clustered,
            sync_to_kafka=sync_to_kafka,
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
    On POST: switch env, then redirect back to wherever the user came from
    (defaults to the dashboard if no next is provided).
    """
    if request.method == 'POST':
        chosen = (request.form.get('env') or '').strip().lower()
        env = settings_db.get_environment(chosen)
        if env:
            settings_db.set_active_environment(chosen)
            # Honor an explicit `next` (only for same-app paths so we don't
            # open-redirect to malicious hosts). Otherwise fall back to dashboard.
            next_url = (request.form.get('next') or '').strip()
            if next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
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
    """Add or update a CLR column override in settings.db. Returns JSON."""
    table_name = (request.form.get('table_name') or '').strip()
    column_name = (request.form.get('column_name') or '').strip()
    cast_as = (request.form.get('cast_as') or 'NVARCHAR(MAX)').strip()
    notes = (request.form.get('notes') or '').strip()
    if not table_name or not column_name:
        return jsonify({'status': 'error', 'message': 'table_name and column_name are required'}), 400
    settings_db.upsert_clr_override(table_name, column_name, cast_as, notes)
    return jsonify({'status': 'success', 'message': f'CLR override for {table_name}.{column_name} saved.'})


@app.route('/settings/clr/delete', methods=['POST'])
def clr_delete():
    """Remove a CLR column override. Returns JSON."""
    table_name = (request.form.get('table_name') or '').strip()
    column_name = (request.form.get('column_name') or '').strip()
    if not table_name or not column_name:
        return jsonify({'status': 'error', 'message': 'table_name and column_name are required'}), 400
    settings_db.delete_clr_override(table_name, column_name)
    return jsonify({'status': 'success', 'message': f'CLR override for {table_name}.{column_name} removed.'})


@app.route('/settings/sync-toggle', methods=['POST'])
def sync_toggle():
    """Toggle the per-environment 'sync to Kafka' setting. Returns JSON."""
    active = _resolve_active_environment()
    if not active:
        return jsonify({'status': 'error', 'message': 'no active environment'}), 400
    new_value = (request.form.get('enabled') or '').lower() in ('1', 'true', 'yes', 'on')
    settings_db.update_environment(
        active['value'],
        kafka_brokers=active['kafka_brokers'],
        kafka_clustered=active['kafka_clustered'],
        sync_to_kafka=new_value,
        settings=active.get('settings') or {},
    )
    return jsonify({'status': 'success', 'message': f'Sync-to-Kafka {"enabled" if new_value else "disabled"} for {active["display_name"]}.'})


@app.route('/settings/server-sync-toggle', methods=['POST'])
def server_sync_toggle():
    """Toggle the per-database (per-server) 'sync to Kafka' setting. Returns JSON."""
    active = _resolve_active_environment()
    if not active:
        return jsonify({'status': 'error', 'message': 'no active environment'}), 400
    server_ip = (request.form.get('server_ip') or '').strip()
    if not server_ip:
        return jsonify({'status': 'error', 'message': 'server_ip required'}), 400
    new_value = (request.form.get('enabled') or '').lower() in ('1', 'true', 'yes', 'on')
    ok = settings_db.set_server_sync_to_kafka(active['value'], server_ip, new_value)
    if not ok:
        return jsonify({
            'status': 'error',
            'message': f'server {server_ip} not found in env {active["value"]}',
        }), 404
    return jsonify({'status': 'success', 'message': f'Sync-to-Kafka {"enabled" if new_value else "disabled"} for {server_ip}.'})


@app.route('/settings/server-disable', methods=['POST'])
def server_disable():
    """Soft-disable a server (kept in list but excluded from sync ops). Returns JSON."""
    active = _resolve_active_environment()
    if not active:
        return jsonify({'status': 'error', 'message': 'no active environment'}), 400
    server_ip = (request.form.get('server_ip') or '').strip()
    if not server_ip:
        return jsonify({'status': 'error', 'message': 'server_ip required'}), 400
    new_value = (request.form.get('disabled') or '').lower() in ('1', 'true', 'yes', 'on')
    ok = settings_db.set_server_disabled(active['value'], server_ip, new_value)
    if not ok:
        return jsonify({
            'status': 'error',
            'message': f'server {server_ip} not found in env {active["value"]}',
        }), 404
    return jsonify({'status': 'success', 'message': f'Server {server_ip} {"enabled" if not new_value else "disabled"}.'})


@app.route('/settings/server-edit', methods=['POST'])
def server_edit():
    """Update editable fields on a server entry. Returns JSON."""
    active = _resolve_active_environment()
    if not active:
        return jsonify({'status': 'error', 'message': 'no active environment'}), 400
    server_ip = (request.form.get('server_ip') or '').strip()
    if not server_ip:
        return jsonify({'status': 'error', 'message': 'server_ip required'}), 400

    fields = {}
    for k in ('server', 'user', 'password', 'db', 'port'):
        v = request.form.get(k)
        if v is None:
            continue
        # Password: blank means "keep current" — skip it so we don't blank
        # out the stored password. Other fields: blank means "leave as-is" too.
        if v.strip() == '' and k != 'password':
            continue
        # For password, only include if explicitly set (non-blank).
        if k == 'password' and v == '':
            continue
        fields[k] = v.strip() if k != 'password' else v
    if 'isPrimary' in request.form:
        fields['isPrimary'] = 'isPrimary' in request.form
    if not fields:
        return jsonify({'status': 'error', 'message': 'no fields to update'}), 400

    ok = settings_db.update_server(active['value'], server_ip, **fields)
    if not ok:
        return jsonify({
            'status': 'error',
            'message': f'server {server_ip} not found in env {active["value"]}',
        }), 404
    return jsonify({'status': 'success', 'message': f'Server {server_ip} updated.'})


@app.route('/settings/server-add', methods=['POST'])
def server_add():
    """Append a new server to the active env's settings.servers. Returns JSON."""
    active = _resolve_active_environment()
    if not active:
        return jsonify({'status': 'error', 'message': 'no active environment'}), 400

    server   = (request.form.get('server') or '').strip()
    db       = (request.form.get('db') or 'NitaraDB').strip()
    user     = (request.form.get('user') or '').strip()
    password = request.form.get('password') or ''
    port     = (request.form.get('port') or '1433').strip() or '1433'
    is_primary = 'isPrimary' in request.form
    sync_to_kafka = 'sync_to_kafka' in request.form

    if not server or not user or not db:
        return jsonify({'status': 'error', 'message': 'server, db, and user are required'}), 400

    result = settings_db.add_server(
        active['value'],
        {
            'server':        server,
            'user':          user,
            'password':      password,
            'db':            db,
            'port':          port,
            'isPrimary':     is_primary,
            'sync_to_kafka': sync_to_kafka,
        },
    )
    if result['status'] == 'ok':
        return jsonify({'status': 'success', 'message': f'Server {server}:{port} added.'})
    if result['status'] == 'duplicate':
        return jsonify({'status': 'error', 'message': f"server {result['key']} already exists"}), 409
    return jsonify({'status': 'error', 'message': result.get('message', 'failed to add server')}), 400


@app.route('/settings/general-save', methods=['POST'])
def general_save():
    """Save the General tab (refresh_frequency, notified_emails, ignore_tables). Returns JSON."""
    active = _resolve_active_environment()
    if not active:
        return jsonify({'status': 'error', 'message': 'no active environment'}), 400
    try:
        refresh_frequency = int(request.form.get('refresh_frequency', '30') or 30)
    except (TypeError, ValueError):
        refresh_frequency = 30
    notified_emails = (request.form.get('notified_emails') or '').strip()
    ignore_tables_input = request.form.get('ignore_tables') or ''
    ignore_tables = [ln.strip() for ln in ignore_tables_input.split('\n') if ln.strip()]
    ok = settings_db.update_general_settings(
        active['value'],
        refresh_frequency=refresh_frequency,
        notified_emails=notified_emails,
        ignore_tables=ignore_tables,
    )
    if not ok:
        return jsonify({'status': 'error', 'message': 'failed to save'}), 500
    return jsonify({'status': 'success', 'message': 'Application settings saved.'})


@app.route('/settings/kafka-brokers-save', methods=['POST'])
def kafka_brokers_save():
    """Save the Kafka tab's brokers + clustered flag. Returns JSON."""
    active = _resolve_active_environment()
    if not active:
        return jsonify({'status': 'error', 'message': 'no active environment'}), 400
    brokers = (request.form.get('kafka_brokers') or '').strip()
    clustered = 'kafka_clustered' in request.form
    ok = settings_db.update_kafka_brokers(active['value'], brokers, clustered)
    if not ok:
        return jsonify({'status': 'error', 'message': 'failed to save'}), 500
    return jsonify({'status': 'success', 'message': 'Kafka brokers saved.'})


@app.route('/settings/tab/<name>', methods=['GET'])
def settings_tab(name):
    """
    Return a single settings tab as an HTML fragment (no layout, no shell).
    Used by the AJAX tab loader in templates/settings.html — every form inside
    the returned HTML is a self-contained AJAX form (data-ajax-form).
    """
    if name not in SETTINGS_TABS:
        return jsonify({'status': 'error', 'message': f'unknown tab: {name}'}), 404
    active = _resolve_active_environment()
    if not active:
        return jsonify({'status': 'error', 'message': 'no active environment'}), 400

    # Re-run the context processor so the partial has the same _safe_servers
    # / _warning fields the full-page render used to inject. Without this,
    # the databases partial's `{{ active_environment._safe_servers | tojson }}`
    # would be empty.
    ctx = inject_environment()
    active = ctx['active_environment']

    clr_overrides = settings_db.list_clr_overrides()
    resp = make_response(render_template(
        f'settings/_{name}.html',
        active_environment=active,
        clr_overrides=clr_overrides,
    ))
    # Tab fragments are loaded via fetch() and their content depends on the
    # active env, the DB state, and the per-server flags. They must never be
    # cached — a stale fragment would show the wrong brokers / servers / etc.
    # after an env switch or a settings change. (See the issue where switching
    # env from the top bar left the brokers textbox showing the cached empty
    # value while the DB had a real one.)
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


@app.route('/settings', methods=['GET'])
def settings():
    """
    Render the Settings shell (page header + tab buttons + tab content
    placeholder). The tab content itself is loaded by the browser via
    GET /settings/tab/<name> — see the AJAX loader in templates/settings.html.
    All form submissions in any tab are AJAX and return JSON.
    """
    active = _resolve_active_environment()
    if not active:
        return redirect(url_for('select_environment'))
    clr_overrides = settings_db.list_clr_overrides()
    return render_template(
        'settings.html',
        active_environment=active,
        clr_overrides=clr_overrides,
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
