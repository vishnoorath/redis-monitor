"""
Settings Database Module for Nitara BAM.
Manages application settings, environments, and per-environment overrides in SQLite.

Schema
------
ApplicationSettings(key, value, valueType)
    Generic global settings (legacy). Stores things like IGNORE_TABLES_FOR_MONITORING,
    REFRESH_FREQUENCY, NOTIFIED_EMAILS, SERVERS.

Environments(display_name, value, kafka_brokers, kafka_clustered, settings_json)
    One row per logical environment (Dev, Test, Uat, Prod).
    - display_name    : "Dev" | "Test" | "Uat" | "Prod"
    - value           : "dev" | "test" | "uat" | "prod" (the {env} value used for Kafka topic)
    - kafka_brokers   : Comma-separated bootstrap servers (single or clustered).
                        Single:  "10.10.98.39:9092"
                        Cluster: "10.10.98.36:9092,10.10.98.37:9092,10.10.98.38:9092"
    - kafka_clustered : "true" if brokers are a Kafka cluster (prod), else "false" (others).
    - settings_json   : JSON blob of environment-specific overrides (servers, refresh freq,
                        notified emails, ignore tables). Lets each env have its own config.

The active environment is stored as a special ApplicationSettings row keyed
"ACTIVE_ENVIRONMENT" -> value (e.g. "prod").
"""

import sqlite3
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Database file path
DB_PATH = Path(__file__).parent.parent / 'settings.db'

# Canonical environment definitions (display_name, value, default_clustered)
ENVIRONMENT_DEFAULTS = [
    ('Dev',  'dev',  False),
    ('Test', 'test', False),
    ('Uat',  'uat',  False),
    ('Prod', 'prod', True),
]


def get_connection() -> sqlite3.Connection:
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_settings_db() -> None:
    """
    Initialize the settings database.
    Creates the ApplicationSettings and Environments tables if they don't exist.
    Seeds the Environments table with the canonical Dev/Test/Uat/Prod rows.
    Also creates the ClrColumnOverrides table for CLR column cast overrides.

    NOTE: All config (refresh frequency, ignored tables, Kafka brokers,
    server lists, per-database sync_to_kafka, CLR overrides) lives in this
    SQLite DB. There is no .env fallback — every config is read from here.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ApplicationSettings (
                key VARCHAR PRIMARY KEY NOT NULL,
                value NVARCHAR NOT NULL,
                valueType VARCHAR NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Environments (
                display_name VARCHAR PRIMARY KEY NOT NULL,
                value VARCHAR NOT NULL UNIQUE,
                kafka_brokers VARCHAR,
                kafka_clustered VARCHAR NOT NULL DEFAULT 'false',
                sync_to_kafka VARCHAR NOT NULL DEFAULT 'false',
                settings_json VARCHAR NOT NULL DEFAULT '{}'
            )
        ''')

        # Migrations for older DBs that pre-date some columns.
        migrations = [
            ("ALTER TABLE Environments ADD COLUMN kafka_brokers VARCHAR",                None),
            ("ALTER TABLE Environments ADD COLUMN kafka_clustered VARCHAR NOT NULL DEFAULT 'false'", None),
            ("ALTER TABLE Environments ADD COLUMN sync_to_kafka VARCHAR NOT NULL DEFAULT 'false'", None),
        ]
        for stmt, _ in migrations:
            try:
                cursor.execute(stmt)
            except sqlite3.OperationalError:
                # Column already exists — ignore.
                pass

        # Seed canonical envs (idempotent – only inserts missing rows)
        for display_name, value, clustered in ENVIRONMENT_DEFAULTS:
            cursor.execute(
                'SELECT 1 FROM Environments WHERE value = ?',
                (value,)
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    '''INSERT INTO Environments
                       (display_name, value, kafka_brokers, kafka_clustered, sync_to_kafka, settings_json)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (display_name, value, '', 'true' if clustered else 'false', 'false', '{}')
                )

        conn.commit()
    finally:
        conn.close()

    # ClrColumnOverrides lives in its own table for clean CRUD semantics
    init_clr_overrides_db()


# ---------------------------------------------------------------------------
# Environment management
# ---------------------------------------------------------------------------

def list_environments() -> List[Dict[str, Any]]:
    """Return all environments ordered by canonical display order.

    Each row: display_name, value, kafka_brokers, kafka_clustered, sync_to_kafka, settings
    """
    order = {dn: i for i, (dn, _, _) in enumerate(ENVIRONMENT_DEFAULTS)}
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT display_name, value, kafka_brokers, kafka_clustered, '
            'sync_to_kafka, settings_json '
            'FROM Environments'
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    out: List[Dict[str, Any]] = []
    for r in rows:
        try:
            settings = json.loads(r['settings_json']) if r['settings_json'] else {}
        except json.JSONDecodeError:
            settings = {}
        out.append({
            'display_name':   r['display_name'],
            'value':          r['value'],
            'kafka_brokers':  r['kafka_brokers'] or '',
            'kafka_clustered': (r['kafka_clustered'] or '').lower() == 'true',
            'sync_to_kafka':  (r['sync_to_kafka']  or '').lower() == 'true',
            'settings': settings,
        })
    out.sort(key=lambda e: order.get(e['display_name'], 999))
    return out


def get_environment(value: str) -> Optional[Dict[str, Any]]:
    """Return a single environment by its {env} value (e.g. 'prod')."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT display_name, value, kafka_brokers, kafka_clustered, '
            'sync_to_kafka, settings_json '
            'FROM Environments WHERE value = ?',
            (value.lower(),)
        )
        r = cursor.fetchone()
    finally:
        conn.close()
    if not r:
        return None
    try:
        settings = json.loads(r['settings_json']) if r['settings_json'] else {}
    except json.JSONDecodeError:
        settings = {}
    return {
        'display_name':   r['display_name'],
        'value':          r['value'],
        'kafka_brokers':  r['kafka_brokers'] or '',
        'kafka_clustered': (r['kafka_clustered'] or '').lower() == 'true',
        'sync_to_kafka':  (r['sync_to_kafka']  or '').lower() == 'true',
        'settings': settings,
    }


def update_environment(
    value: str,
    kafka_brokers: str = '',
    kafka_clustered: bool = False,
    sync_to_kafka: bool = False,
    settings: Optional[Dict[str, Any]] = None,
) -> bool:
    """Persist per-environment config. Updates brokers / clustered / settings blob.

    Note: ``sync_to_kafka`` is now a **per-database (per-server)** setting that
    lives inside the env's ``settings.servers`` list — not on the env row itself.
    The parameter is kept here for backward compatibility with callers, but is
    no longer persisted to the env row.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''UPDATE Environments
               SET kafka_brokers = ?,
                   kafka_clustered = ?,
                   settings_json = ?
               WHERE value = ?''',
            (
                kafka_brokers.strip(),
                'true' if kafka_clustered else 'false',
                json.dumps(settings or {}),
                value.lower(),
            )
        )
        updated = cursor.rowcount > 0
        conn.commit()
        return updated
    finally:
        conn.close()


def get_active_environment() -> Optional[Dict[str, Any]]:
    """Return the env currently selected by the user (or None if not set)."""
    setting = get_setting('ACTIVE_ENVIRONMENT')
    if not setting:
        return None
    return get_environment(setting['value'])


def set_active_environment(value: str) -> bool:
    """Record which env the user chose at startup."""
    return set_setting('ACTIVE_ENVIRONMENT', value.lower(), 'STRING')


def seed_legacy_servers_into_envs() -> None:
    """
    One-time bootstrap: for every environment that doesn't already have
    servers in its ``settings.servers`` list, populate from the hard-coded
    ``PER_ENV_SERVERS`` table below.

    After this runs, each env owns its own server list (and the
    per-database ``sync_to_kafka`` toggle). There is no .env fallback for
    server config — it's all stored here.
    """
    # Per-env server overrides. Each env that doesn't appear here falls back
    # to the legacy ``DEFAULT_SERVERS`` cluster (the dev/test/prod setup).
    PER_ENV_SERVERS = {
        'uat': [
            {
                'server': '10.10.98.26', 'port': '31812',
                'user': 'sa', 'password': 'P@ssw0rd@123',
                'db': 'NitaraDB', 'isPrimary': True,
            },
            {
                'server': '10.10.98.26', 'port': '31813',
                'user': 'sa', 'password': 'P@ssw0rd@123',
                'db': 'NitaraDB', 'isPrimary': False,
            },
        ],
        'dev': [
            {
                'server': '10.10.98.47', 'port': '1433',
                'user': 'sa', 'password': 't5!bT5AZ5Q@coqZ',
                'db': 'NitaraDB', 'isPrimary': True,
            },
            {
                'server': '10.10.98.66', 'port': '1433',
                'user': 'sa', 'password': 'Gt(#@987HaS',
                'db': 'NitaraDB', 'isPrimary': False,
            },
            {
                'server': '10.10.98.76', 'port': '1433',
                'user': 'sa', 'password': 'Gt(#@987RTGF',
                'db': 'NitaraDB', 'isPrimary': False,
            },
            {
                'server': '10.10.98.100', 'port': '1433',
                'user': 'sa', 'password': 'P@ssw0rd@123',
                'db': 'NitaraDB', 'isPrimary': False,
            },
        ],
        'test': [
            {
                'server': '10.10.98.47', 'port': '1433',
                'user': 'sa', 'password': 't5!bT5AZ5Q@coqZ',
                'db': 'NitaraDB', 'isPrimary': True,
            },
            {
                'server': '10.10.98.66', 'port': '1433',
                'user': 'sa', 'password': 'Gt(#@987HaS',
                'db': 'NitaraDB', 'isPrimary': False,
            },
            {
                'server': '10.10.98.76', 'port': '1433',
                'user': 'sa', 'password': 'Gt(#@987RTGF',
                'db': 'NitaraDB', 'isPrimary': False,
            },
            {
                'server': '10.10.98.100', 'port': '1433',
                'user': 'sa', 'password': 'P@ssw0rd@123',
                'db': 'NitaraDB', 'isPrimary': False,
            },
        ],
        'prod': [
            {
                'server': '10.10.98.47', 'port': '1433',
                'user': 'sa', 'password': 't5!bT5AZ5Q@coqZ',
                'db': 'NitaraDB', 'isPrimary': True,
            },
            {
                'server': '10.10.98.66', 'port': '1433',
                'user': 'sa', 'password': 'Gt(#@987HaS',
                'db': 'NitaraDB', 'isPrimary': False,
            },
            {
                'server': '10.10.98.76', 'port': '1433',
                'user': 'sa', 'password': 'Gt(#@987RTGF',
                'db': 'NitaraDB', 'isPrimary': False,
            },
            {
                'server': '10.10.98.100', 'port': '1433',
                'user': 'sa', 'password': 'P@ssw0rd@123',
                'db': 'NitaraDB', 'isPrimary': False,
            },
        ],
    }

    for env in list_environments():
        existing = env.get('settings', {}).get('servers', [])
        if existing:
            continue  # already populated, don't overwrite
        source = PER_ENV_SERVERS.get(env['value'], [])
        copied = []
        for s in source:
            is_primary = bool(s.get('isPrimary', False))
            copied.append({
                'server':       s.get('server', ''),
                'user':         s.get('user', ''),
                'password':     s.get('password', '') or '',
                'db':           s.get('db', 'NitaraDB'),
                'port':         s.get('port', '1433') or '1433',
                'isPrimary':    is_primary,
                # Primary servers can NEVER publish Kafka backlog.
                'sync_to_kafka': False if is_primary else False,
                'disabled':     False,
            })
        new_settings = dict(env.get('settings') or {})
        new_settings['servers'] = copied
        update_environment(
            env['value'],
            kafka_brokers=env['kafka_brokers'],
            kafka_clustered=env['kafka_clustered'],
            settings=new_settings,
        )


# ---------------------------------------------------------------------------
# Per-server (per-database) settings helpers
# ---------------------------------------------------------------------------
# Each server entry stored in environments[*].settings.servers has this shape:
#   {
#       'server':       '10.10.98.76',
#       'user':         'sa',
#       'password':     '...',
#       'db':           'NitaraDB',
#       'port':         '1433',
#       'isPrimary':    False,
#       'sync_to_kafka': True/False,        ← per-database toggle
#   }


def _normalize_server(server: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure a server dict has all the required fields with sensible defaults."""
    out = {
        'server':       server.get('server', ''),
        'user':         server.get('user', ''),
        'password':     server.get('password', '') or '',
        'db':           server.get('db', 'NitaraDB'),
        'port':         server.get('port', '1433') or '1433',
        'isPrimary':    bool(server.get('isPrimary', False)),
        'sync_to_kafka': bool(server.get('sync_to_kafka', False)),
        'disabled':     bool(server.get('disabled', False)),
    }
    return out


def add_server(env_value: str, server: Dict[str, Any]) -> Dict[str, Any]:
    """
    Append a new server to the env's settings.servers list.

    Rules:
      - Keys are (server, port). Adding an entry that already exists by
        that key returns ``{'status': 'duplicate'}`` and does not modify
        the list.
      - If the new entry is primary, every existing entry is demoted to
        secondary (and any sync_to_kafka flag is cleared) — there is at
        most one primary per env.
      - Returns ``{'status': 'ok', 'server': <normalized_server_dict>}``
        on success.

    The caller is responsible for surfacing the result to the UI.
    """
    env = get_environment(env_value)
    if not env:
        return {'status': 'error', 'message': f"env {env_value!r} not found"}
    settings = env.get('settings') or {}
    servers = settings.get('servers', []) or []

    new_server = _normalize_server({
        'server':        server.get('server', ''),
        'user':          server.get('user', ''),
        'password':      server.get('password', '') or '',
        'db':            server.get('db', 'NitaraDB'),
        'port':          server.get('port', '1433') or '1433',
        'isPrimary':     bool(server.get('isPrimary', False)),
        'sync_to_kafka': bool(server.get('sync_to_kafka', False)),
        'disabled':      False,
    })

    new_key = new_server['server'] + ':' + new_server['port']
    for s in servers:
        sp = s.get('server', '') + ':' + (s.get('port', '1433') or '1433')
        if sp == new_key:
            return {'status': 'duplicate', 'message': f"server {new_key} already exists", 'key': new_key}

    if new_server['isPrimary']:
        for s in servers:
            s['isPrimary'] = False
            s['sync_to_kafka'] = False

    servers.append(new_server)
    settings['servers'] = servers

    ok = update_environment(
        env_value,
        kafka_brokers=env['kafka_brokers'],
        kafka_clustered=env['kafka_clustered'],
        settings=settings,
    )
    if not ok:
        return {'status': 'error', 'message': 'failed to persist new server'}
    return {'status': 'ok', 'server': new_server}


def update_general_settings(env_value: str, **fields) -> bool:
    """
    Update the per-env non-server settings (refresh_frequency, notified_emails,
    ignore_tables). Pass only the fields you want to change; other fields
    in the env's settings blob are preserved.

    Recognised fields: refresh_frequency (int), notified_emails (str),
    ignore_tables (list[str]).

    SAFETY: this function MUST NOT touch ``settings.servers``. It only
    modifies the three keys listed above. Even if the env's settings blob
    is unexpectedly empty (``{}``), we preserve whatever is there.
    """
    env = get_environment(env_value)
    if not env:
        return False
    settings = dict(env.get('settings') or {})  # shallow copy — do not mutate env
    for k in ('refresh_frequency', 'notified_emails', 'ignore_tables'):
        if k in fields:
            settings[k] = fields[k]
    # Defensive: never let a partial update WIPE the servers list. If for
    # any reason the stored settings is empty, fall back to the env's
    # current servers (re-read from DB to be safe).
    if 'servers' not in settings:
        settings['servers'] = (env.get('settings') or {}).get('servers', [])
    return update_environment(
        env_value,
        kafka_brokers=env['kafka_brokers'],
        kafka_clustered=env['kafka_clustered'],
        settings=settings,
    )


def update_kafka_brokers(env_value: str, brokers: str, clustered: bool) -> bool:
    """
    Update the per-env Kafka broker list + clustered flag.

    SAFETY: this function MUST NOT touch ``settings.servers`` or any other
    field in the env's settings blob. It only modifies the two top-level
    ``Environments`` columns (kafka_brokers, kafka_clustered). The settings
    blob is re-read fresh from the DB and written back unchanged, with
    an explicit guard against accidentally overwriting it with ``{}``.
    """
    env = get_environment(env_value)
    if not env:
        return False
    settings = dict(env.get('settings') or {})  # shallow copy — do not mutate env
    # Defensive: if the stored settings is empty for any reason, keep
    # the servers list (re-read from DB). This prevents a future bug from
    # silently wiping settings.servers on a broker save.
    if 'servers' not in settings:
        settings['servers'] = (env.get('settings') or {}).get('servers', [])
    return update_environment(
        env_value,
        kafka_brokers=(brokers or '').strip(),
        kafka_clustered=bool(clustered),
        settings=settings,
    )


def get_servers(env_value: str) -> List[Dict[str, Any]]:
    """Return the (normalized) list of servers for the given environment."""
    env = get_environment(env_value)
    if not env:
        return []
    raw = env.get('settings', {}).get('servers', [])
    return [_normalize_server(s) for s in raw]


def set_server_sync_to_kafka(env_value: str, server_ip: str, enabled: bool) -> bool:
    """Toggle the sync_to_kafka flag on a single server entry.

    The ``server_ip`` argument may be either a plain IP ("10.10.98.76") or
    an IP+port ("10.10.98.26:31813"). UAT has two servers on the same IP
    with different ports, so we match on the full ``server:port`` key.

    Rules:
      - Primary servers can NEVER have sync_to_kafka (only secondaries publish
        Kafka backlog). The call is rejected for primaries.
      - At most ONE secondary per env may have sync_to_kafka=True. If the user
        enables it for server X, any other secondary that was on gets cleared.

    Returns True if a matching (secondary) server was found and updated.
    """
    env = get_environment(env_value)
    if not env:
        return False
    servers = env.get('settings', {}).get('servers', [])
    target = None
    for s in servers:
        # Match by full server:port key (so UAT's 31812 / 31813 are distinct).
        sp = s.get('server', '') + ':' + (s.get('port', '1433') or '1433')
        if sp == server_ip:
            target = s
            break
    if not target:
        return False
    if target.get('isPrimary'):
        return False  # never allow Kafka publish on primary

    if enabled:
        # Clear sync_to_kafka on every OTHER secondary.
        for s in servers:
            if s is target:
                continue
            if not s.get('isPrimary'):
                s['sync_to_kafka'] = False
        target['sync_to_kafka'] = True
    else:
        target['sync_to_kafka'] = False

    return update_environment(
        env_value,
        kafka_brokers=env['kafka_brokers'],
        kafka_clustered=env['kafka_clustered'],
        settings=env.get('settings') or {},
    )


def set_server_disabled(env_value: str, server_ip: str, disabled: bool) -> bool:
    """Soft-disable a server so it's skipped by sync ops but kept in the list.

    ``server_ip`` may be a plain IP or ``server:port`` (UAT-style).
    """
    env = get_environment(env_value)
    if not env:
        return False
    servers = env.get('settings', {}).get('servers', [])
    changed = False
    for s in servers:
        sp = s.get('server', '') + ':' + (s.get('port', '1433') or '1433')
        if sp == server_ip:
            s['disabled'] = bool(disabled)
            changed = True
            break
    if not changed:
        return False
    return update_environment(
        env_value,
        kafka_brokers=env['kafka_brokers'],
        kafka_clustered=env['kafka_clustered'],
        settings=env.get('settings') or {},
    )


def update_server(env_value: str, server_ip: str, **fields) -> bool:
    """Update fields on a server entry (e.g. user, password, db, port).

    ``server_ip`` may be a plain IP or ``server:port`` (UAT-style).
    The ``server`` key in ``fields`` (if present) is the new server identity;
    we locate the existing server by the OLD ``server_ip`` parameter.

    Rule: marking a server primary automatically clears its ``sync_to_kafka``
    flag, since primary servers never publish to Kafka.
    """
    env = get_environment(env_value)
    if not env:
        return False
    servers = env.get('settings', {}).get('servers', [])
    changed = False
    for s in servers:
        sp = s.get('server', '') + ':' + (s.get('port', '1433') or '1433')
        if sp == server_ip:
            for k, v in fields.items():
                s[k] = v
            # If just promoted to primary, force-clear sync_to_kafka.
            if s.get('isPrimary'):
                s['sync_to_kafka'] = False
            changed = True
            break
    if not changed:
        return False
    return update_environment(
        env_value,
        kafka_brokers=env['kafka_brokers'],
        kafka_clustered=env['kafka_clustered'],
        settings=env.get('settings') or {},
    )


def get_setting(key: str) -> Optional[dict]:
    """
    Retrieve a setting by key.

    Args:
        key: The setting key

    Returns:
        Dictionary with key, value, and valueType, or None if not found
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT key, value, valueType FROM ApplicationSettings WHERE key = ?',
            (key,)
        )
        row = cursor.fetchone()
        if row:
            return {
                'key': row['key'],
                'value': row['value'],
                'valueType': row['valueType']
            }
        return None
    finally:
        conn.close()


def set_setting(key: str, value: Any, value_type: str) -> bool:
    """
    Save a setting with proper type handling.

    Args:
        key: The setting key
        value: The setting value (will be converted to string)
        value_type: Type of value (STRING, JSON, INT, FLOAT, BOOL, DATE)

    Returns:
        True if successful
    """
    # Convert value to string based on type
    if value_type == 'JSON':
        str_value = json.dumps(value)
    elif value_type == 'JSARRAY':
        # Handle JavaScript array format - store as-is
        if isinstance(value, list):
            str_value = json.dumps(value)
        else:
            str_value = str(value)
    else:
        str_value = str(value)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO ApplicationSettings (key, value, valueType)
            VALUES (?, ?, ?)
        ''', (key, str_value, value_type))
        conn.commit()
        return True
    finally:
        conn.close()


def migrate_legacy_settings(legacy_overrides: Optional[Dict[str, Any]] = None) -> None:
    """
    One-time migration: seed the active env's settings_json from a dict of legacy
    .env values so the user has something to edit on first boot.

    Idempotent — only writes if the env's settings_json is empty.
    """
    env = get_active_environment()
    if not env:
        return
    if env['settings']:
        return  # Already populated
    if not legacy_overrides:
        return
    update_environment(env['value'],
                       env['kafka_brokers'],
                       env['kafka_clustered'],
                       env['sync_to_kafka'],
                       legacy_overrides)


# ---------------------------------------------------------------------------
# CLR column overrides (user-managed map for usp_GetMissingRows_CLR)
# ---------------------------------------------------------------------------
# These overrides tell the secondary SQL Server how to CAST each CLR-type
# column when streaming missing rows back through OPENQUERY. Default for any
# CLR column not listed here is NVARCHAR(MAX).
#
# Stored in SQLite so the user can edit them via the Settings page.
# Before each sync, Python pushes these rows to dbo.ClrColumnOverrides on the
# secondary SQL Server.

def init_clr_overrides_db() -> None:
    """Create the ClrColumnOverrides table and seed the known CLR columns."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ClrColumnOverrides (
                table_name  VARCHAR(256) NOT NULL,
                column_name VARCHAR(256) NOT NULL,
                cast_as     VARCHAR(64)  NOT NULL DEFAULT 'NVARCHAR(MAX)',
                notes       VARCHAR(500),
                PRIMARY KEY (table_name, column_name)
            )
        ''')

        # Seed the columns that actually need CASTing for tracked tables.
        # Only adds a row if it doesn't already exist (preserves manual edits).
        seed_rows = [
            ('Farms', 'GeoPoint',      'NVARCHAR(MAX)',
             '[dbo].[Farms].[GeoPoint] is geography (CLR) — ODBC cannot transport it natively.'),
            ('Farms', 'FarmLatitude',  'NVARCHAR(MAX)',
             '[dbo].[Farms].[FarmLatitude] is nvarchar but stores numeric coords (e.g. \'20.9425972\') — ODBC auto-coerces to float and overflows.'),
            ('Farms', 'FarmLongitude', 'NVARCHAR(MAX)',
             '[dbo].[Farms].[FarmLongitude] is nvarchar but stores numeric coords (e.g. \'70.6175452\') — ODBC auto-coerces to float and overflows.'),
        ]
        for table_name, column_name, cast_as, notes in seed_rows:
            cursor.execute(
                'SELECT 1 FROM ClrColumnOverrides WHERE table_name=? AND column_name=?',
                (table_name, column_name)
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    '''INSERT INTO ClrColumnOverrides (table_name, column_name, cast_as, notes)
                       VALUES (?, ?, ?, ?)''',
                    (table_name, column_name, cast_as, notes)
                )
        conn.commit()
    finally:
        conn.close()


def list_clr_overrides() -> List[Dict[str, Any]]:
    """Return all CLR column overrides, ordered by table then column."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT table_name, column_name, cast_as, notes FROM ClrColumnOverrides '
            'ORDER BY table_name, column_name'
        )
        rows = cursor.fetchall()
        return [
            {
                'table_name':  r['table_name'],
                'column_name': r['column_name'],
                'cast_as':     r['cast_as'],
                'notes':       r['notes'] or '',
            }
            for r in rows
        ]
    finally:
        conn.close()


def upsert_clr_override(table_name: str, column_name: str,
                        cast_as: str = 'NVARCHAR(MAX)',
                        notes: str = '') -> bool:
    """Insert or update a CLR column override. Returns True on success."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO ClrColumnOverrides (table_name, column_name, cast_as, notes)
               VALUES (?, ?, ?, ?)
               ON CONFLICT (table_name, column_name) DO UPDATE SET
                   cast_as = excluded.cast_as,
                   notes   = excluded.notes''',
            (table_name, column_name, cast_as, notes)
        )
        conn.commit()
        return True
    finally:
        conn.close()


def delete_clr_override(table_name: str, column_name: str) -> bool:
    """Remove a CLR column override. Returns True if a row was deleted."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM ClrColumnOverrides WHERE table_name=? AND column_name=?',
            (table_name, column_name)
        )
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()


def get_all_settings() -> list:
    """
    Get all settings.

    Returns:
        List of dictionaries with key, value, and valueType
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT key, value, valueType FROM ApplicationSettings')
        rows = cursor.fetchall()
        return [
            {
                'key': row['key'],
                'value': row['value'],
                'valueType': row['valueType']
            }
            for row in rows
        ]
    finally:
        conn.close()


def delete_setting(key: str) -> bool:
    """
    Remove a setting by key.

    Args:
        key: The setting key to delete

    Returns:
        True if deleted, False if not found
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM ApplicationSettings WHERE key = ?', (key,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()


def get_setting_parsed(key: str) -> Any:
    """
    Get a setting and parse it to its native type.

    Args:
        key: The setting key

    Returns:
        The value parsed to its native type, or None if not found
    """
    setting = get_setting(key)
    if not setting:
        return None

    value = setting['value']
    value_type = setting['valueType']

    if value_type == 'JSON':
        return json.loads(value)
    elif value_type == 'JSARRAY':
        # Parse JavaScript array format: ['item1', 'item2']
        try:
            # Convert JavaScript array notation to valid JSON
            json_str = value.strip()
            if json_str.startswith('[') and json_str.endswith(']'):
                return json.loads(json_str)
            return []
        except json.JSONDecodeError:
            return []
    elif value_type == 'INT':
        return int(value)
    elif value_type == 'FLOAT':
        return float(value)
    elif value_type == 'BOOL':
        return value.lower() in ('true', '1', 'yes')
    else:
        return value


if __name__ == '__main__':
    init_settings_db()
    print("Settings database initialized at:", DB_PATH)

    print("Environments:")
    for env in list_environments():
        srvs = (env.get('settings') or {}).get('servers', [])
        print(f"  {env['value']:6s} | kafka_brokers={env['kafka_brokers'][:30]!r:30s} | servers={len(srvs)}")

    print("CLR overrides:")
    for o in list_clr_overrides():
        print(f"  {o['table_name']}.{o['column_name']} → {o['cast_as']}")
