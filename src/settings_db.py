"""
Settings Database Module for Redis Monitor.
Manages application settings in SQLite database.
"""

import sqlite3
import json
from pathlib import Path
from typing import Any, Optional

# Database file path
DB_PATH = Path(__file__).parent.parent / 'settings.db'


def get_connection() -> sqlite3.Connection:
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_settings_db() -> None:
    """
    Initialize the settings database.
    Creates the ApplicationSettings table if it doesn't exist.
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
        conn.commit()
    finally:
        conn.close()


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
