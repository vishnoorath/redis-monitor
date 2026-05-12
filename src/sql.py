"""
SQL Server database module for Redis Monitor.
Provides functionality to connect to SQL Server and execute stored procedures.
"""

import os
import pyodbc
from pathlib import Path
from dotenv import load_dotenv
from src import settings_db

# Load environment variables from .env file (for fallback)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class SQLServer:
    """SQL Server connection and query handler."""

    def __init__(self):
        """Initialize SQL Server connection parameters from settings database or environment."""
        # Try to get primary server from settings database
        servers = settings_db.get_setting_parsed('SERVERS')
        primary_server = None
        
        if servers and isinstance(servers, list):
            for s in servers:
                if s.get('isPrimary', False):
                    primary_server = s
                    break
            if not primary_server and len(servers) > 0:
                primary_server = servers[0]
        
        if primary_server:
            self.server = primary_server.get('server', 'localhost')
            self.port = primary_server.get('port', '1433')
            self.database = primary_server.get('db', 'NitaraDB')
            self.username = primary_server.get('user', 'sa')
            self.password = primary_server.get('password', '')
        else:
            # Fallback to environment variables
            self.server = os.getenv('SQL_SERVER', 'localhost')
            self.port = os.getenv('SQL_PORT', '1433')
            self.database = os.getenv('SQL_DATABASE', 'NitaraDB')
            self.username = os.getenv('SQL_USERNAME', 'sa')
            self.password = os.getenv('SQL_PASSWORD', '')
            
        self.connection = None
        self.connection_string = self._build_connection_string()

    def _build_connection_string(self):
        """Build the ODBC connection string for SQL Server."""
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
        """Establish connection to SQL Server."""
        try:
            self.connection = pyodbc.connect(self.connection_string)
            return self.connection
        except pyodbc.Error as e:
            print(f"Error connecting to SQL Server: {e}")
            raise

    def disconnect(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def get_recently_updated_farm_ids(self):
        """
        Execute the stored procedure usp_GetRecentlyUpdatedFarmIds.

        Returns:
            list: List of FarmId strings from the stored procedure result.
        """
        farm_ids = []

        try:
            if not self.connection:
                self.connect()

            cursor = self.connection.cursor()

            # Execute the stored procedure
            cursor.execute("{CALL usp_GetRecentlyUpdatedFarmIds}")

            # Fetch all results (single column - FarmId)
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
        """Context manager entry - establish connection."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connection."""
        self.disconnect()


def get_recent_farm_ids():
    """
    Convenience function to get recently updated farm IDs.

    Returns:
        list: List of FarmId strings.
    """
    with SQLServer() as db:
        return db.get_recently_updated_farm_ids()


if __name__ == '__main__':
    # For testing
    print("Testing SQL Server connection...")
    try:
        farm_ids = get_recent_farm_ids()
        print(f"Found {len(farm_ids)} recently updated farms:")
        for farm_id in farm_ids[:10]:  # Show first 10
            print(f"  - {farm_id}")
        if len(farm_ids) > 10:
            print(f"  ... and {len(farm_ids) - 10} more")
    except Exception as e:
        print(f"Failed to connect or execute: {e}")
