"""
SQL Server module for Nitara BAM.
Reads primary server config from the active env's settings.servers list
in settings.db. No .env fallback — every config is sourced from SQLite.
"""

import pyodbc
from src import settings_db


def _active_primary():
    """Return the active env's primary server config (no .env fallback)."""
    try:
        env_value = settings_db.get_setting_parsed('ACTIVE_ENVIRONMENT')
    except Exception:
        env_value = None
    if not env_value:
        return None
    env = settings_db.get_environment(env_value)
    if not env:
        return None
    for s in env.get('settings', {}).get('servers', []):
        if s.get('disabled'):
            continue
        if s.get('isPrimary'):
            return s
    # Fallback: first non-disabled server
    for s in env.get('settings', {}).get('servers', []):
        if not s.get('disabled'):
            return s
    return None


class SQLServer:
    """SQL Server connection and query handler."""

    def __init__(self):
        primary = _active_primary()
        if not primary:
            raise RuntimeError(
                "No active environment's primary server is configured. "
                "Pick an environment and add a primary server in /settings."
            )
        self.server = primary.get('server', 'localhost')
        self.port = primary.get('port', '1433') or '1433'
        self.database = primary.get('db', 'NitaraDB')
        self.username = primary.get('user', 'sa')
        self.password = primary.get('password', '') or ''
        self.connection = None
        self.connection_string = self._build_connection_string()

    def _build_connection_string(self):
        return (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={self.server},{self.port};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            f"TrustServerCertificate=yes;"
            f"Encrypt=yes;"
        )

    def connect(self):
        try:
            self.connection = pyodbc.connect(self.connection_string)
            return self.connection
        except pyodbc.Error as e:
            print(f"Error connecting to SQL Server: {e}")
            raise

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def get_recently_updated_farm_ids(self):
        farm_ids = []
        try:
            if not self.connection:
                self.connect()
            cursor = self.connection.cursor()
            cursor.execute("{CALL usp_GetRecentlyUpdatedFarmIds}")
            rows = cursor.fetchall()
            for row in rows:
                farm_ids.append(str(row[0]))
            cursor.close()
            return farm_ids
        except pyodbc.Error as e:
            print(f"Error executing stored procedure: {e}")
            raise
        finally:
            self.disconnect()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def get_recent_farm_ids():
    with SQLServer() as db:
        return db.get_recently_updated_farm_ids()


if __name__ == '__main__':
    print("Testing SQL Server connection...")
    try:
        farm_ids = get_recent_farm_ids()
        print(f"Found {len(farm_ids)} recently updated farms:")
        for farm_id in farm_ids[:10]:
            print(f"  - {farm_id}")
        if len(farm_ids) > 10:
            print(f"  ... and {len(farm_ids) - 10} more")
    except Exception as e:
        print(f"Failed to connect or execute: {e}")
