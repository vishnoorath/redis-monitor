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
                settings_json VARCHAR NOT NULL DEFAULT '{}'
            )
        ''')

        # Seed canonical envs (idempotent – only inserts missing rows)
        for display_name, value, clustered in ENVIRONMENT_DEFAULTS:
            cursor.execute(
                'SELECT 1 FROM Environments WHERE value = ?',
                (value,)
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    '''INSERT INTO Environments
                       (display_name, value, kafka_brokers, kafka_clustered, settings_json)
                       VALUES (?, ?, ?, ?, ?)''',
                    (display_name, value, '', 'true' if clustered else 'false', '{}')
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

    Each row: display_name, value, kafka_brokers, kafka_clustered, settings
    """
    order = {dn: i for i, (dn, _, _) in enumerate(ENVIRONMENT_DEFAULTS)}
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT display_name, value, kafka_brokers, kafka_clustered, settings_json '
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
            'display_name': r['display_name'],
            'value':        r['value'],
            'kafka_brokers': r['kafka_brokers'] or '',
            'kafka_clustered': (r['kafka_clustered'] or '').lower() == 'true',
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
            'SELECT display_name, value, kafka_brokers, kafka_clustered, settings_json '
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
        'display_name': r['display_name'],
        'value':        r['value'],
        'kafka_brokers': r['kafka_brokers'] or '',
        'kafka_clustered': (r['kafka_clustered'] or '').lower() == 'true',
        'settings': settings,
    }


def update_environment(
    value: str,
    kafka_brokers: str = '',
    kafka_clustered: bool = False,
    settings: Optional[Dict[str, Any]] = None,
) -> bool:
    """Persist per-environment config. Updates brokers / clustered / settings blob."""
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
    update_environment(env['value'], env['kafka_brokers'], env['kafka_clustered'], legacy_overrides)


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
    # Initialize database
    init_settings_db()
    print("Settings database initialized at:", DB_PATH)

    # Test setting storage
    test_servers = [
        {'server': '10.10.98.47', 'user': 'sa', 'password': 't5!bT5AZ5Q@coqZ', 'db': 'NitaraDB', 'isPrimary': True},
        {'server': '10.10.98.76', 'user': 'sa', 'password': 'Gt(#@987RTGF', 'db': 'NitaraDB', 'isPrimary': False},
    ]

    set_setting('SERVERS', test_servers, 'JSON')
    print("Set SERVERS setting")

    servers = get_setting_parsed('SERVERS')
    print("Retrieved SERVERS:", servers)

    all_settings = get_all_settings()
    print("All settings:", all_settings)
