"""
Replication Monitoring Module
Monitors table row counts across multiple SQL Server databases and compares them.
"""

import pyodbc
from typing import Dict, List, Any
from deepdiff import DeepDiff
from datetime import datetime


class ReplicationMonitor:
    """Monitor table row counts across multiple SQL Server instances."""

    # Database servers to monitor (JSON object array)
    SERVERS = [
        {'server': '10.10.98.47', 'password': 't5!bT5AZ5Q@coqZ'},
        {'server': '10.10.98.76', 'password': 'Gt(#@987RTGF'},
    ]

    def __init__(self, username: str = 'sa', password: str = 't5!bT5AZ5Q@coqZ', 
                 database: str = 'NitaraDB', port: str = '1433'):
        """
        Initialize replication monitor with connection parameters.
        
        Args:
            username: SQL Server username
            password: SQL Server password
            database: Database name to query
            port: SQL Server port (default 1433)
        """
        self.username = username
        self.password = password
        self.database = database
        self.port = port

    def _build_connection_string(self, server: str) -> str:
        """Build ODBC connection string for a given server."""
        return (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={server},{self.port};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            f"TrustServerCertificate=yes;"
            f"Encrypt=yes;"
        )

    def _get_table_counts(self, server: str, password: str = None) -> Dict[str, Any]:
        """
        Execute stored procedure on a specific server and get table counts.

        Args:
            server: Server address/name
            password: Server-specific password (optional, uses self.password if not provided)

        Returns:
            Dict with server info and table counts, or error details
        """
        result = {
            'server': server,
            'status': 'success',
            'database': self.database,
            'timestamp': datetime.now().isoformat(),
            'tables': {},
            'total_rows': 0,
            'table_count': 0,
            'error': None
        }

        try:
            # Use server-specific password or fallback to default
            conn_password = password if password else self.password
            connection_string = (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                f"SERVER={server},{self.port};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={conn_password};"
                f"TrustServerCertificate=yes;"
                f"Encrypt=yes;"
            )
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            # Try the stored procedure first, fallback to direct query
            try:
                # Execute the stored procedure
                cursor.execute("{CALL usp_GetTableCount_ForMonitoring_Replication}")
                rows = cursor.fetchall()

                # Check if cursor has results
                if not cursor.description or not rows:
                    raise Exception("Stored procedure returned no results, trying direct query")

            except Exception as e:
                # Fallback: Use direct query to get table counts
                print(f"  Stored procedure failed, using direct query: {e}")
                cursor.execute("""
                    SELECT
                        t.NAME AS TableName,
                        p.rows AS RowCounts
                    FROM sys.tables t
                    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
                    INNER JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0, 1)
                    WHERE t.is_ms_shipped = 0
                    AND s.name NOT IN ('sys', 'information_schema')
                    AND (t.name NOT LIKE '%Backup' AND t.name NOT LIKE '%Old' AND t.name NOT LIKE '%Temp')
                    ORDER BY s.Name, t.Name
                """)
                rows = cursor.fetchall()

            # Process results
            for row in rows:
                if len(row) >= 1:
                    table_name = row[0]
                    row_count = int(row[1]) if row[1] else 0
                    result['tables'][table_name] = row_count
                    result['total_rows'] += row_count
                    result['table_count'] += 1

            cursor.close()
            connection.close()

        except pyodbc.Error as e:
            result['status'] = 'error'
            result['error'] = f"Database error: {str(e)}"
        except Exception as e:
            result['status'] = 'error'
            result['error'] = f"Unexpected error: {str(e)}"

        return result

    def compare_servers(self) -> Dict[str, Any]:
        """
        Get table counts from all servers and compare against primary server (10.10.98.47).
        
        Returns:
            Dict with comparison results and differences highlighted
        """
        results = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'primary_server': self.SERVERS[0]['server'],
            'all_servers': {},
            'comparison_results': {},
            'summary': {
                'total_servers': len(self.SERVERS),
                'servers_with_differences': 0,
                'total_table_differences': 0,
                'tables_analyzed': 0
            },
            'errors': []
        }

        # Get table counts from all servers
        print("Fetching table counts from all servers...")
        for server_config in self.SERVERS:
            server = server_config['server']
            password = server_config['password']
            print(f"  Connecting to {server}...")
            server_data = self._get_table_counts(server, password)
            results['all_servers'][server] = server_data

            if server_data['status'] == 'error':
                results['errors'].append({
                    'server': server,
                    'error': server_data['error']
                })

        # Get primary server data
        primary_server = self.SERVERS[0]['server']
        primary_data = results['all_servers'][primary_server]
        if primary_data['status'] != 'success':
            results['status'] = 'error'
            results['comparison_results']['error'] = 'Could not connect to primary server'
            return results

        # Compare each server against primary
        print("Comparing servers...")
        for server_config in self.SERVERS[1:]:  # Skip primary server
            server = server_config['server']
            server_data = results['all_servers'][server]

            if server_data['status'] != 'success':
                results['comparison_results'][server] = {
                    'status': 'error',
                    'error': server_data['error']
                }
                results['summary']['servers_with_differences'] += 1
                continue

            # Compare table counts
            comparison = {
                'status': 'analyzed',
                'differences_found': False,
                'tables': {}
            }

            # Check tables in primary server
            tables_with_diffs = 0
            for table_name, primary_count in primary_data['tables'].items():
                secondary_count = server_data['tables'].get(table_name)

                if secondary_count is None:
                    comparison['tables'][table_name] = {
                        'status': 'missing',
                        'primary_count': primary_count,
                        'secondary_count': None,
                        'difference': '(table missing)',
                        'match': False
                    }
                    comparison['differences_found'] = True
                    tables_with_diffs += 1
                elif primary_count != secondary_count:
                    diff = secondary_count - primary_count
                    comparison['tables'][table_name] = {
                        'status': 'mismatch',
                        'primary_count': primary_count,
                        'secondary_count': secondary_count,
                        'difference': diff,
                        'match': False
                    }
                    comparison['differences_found'] = True
                    tables_with_diffs += 1
                else:
                    comparison['tables'][table_name] = {
                        'status': 'match',
                        'primary_count': primary_count,
                        'secondary_count': secondary_count,
                        'difference': 0,
                        'match': True
                    }

            # Check for tables in secondary but not in primary
            for table_name, secondary_count in server_data['tables'].items():
                if table_name not in primary_data['tables']:
                    if table_name not in comparison['tables']:
                        comparison['tables'][table_name] = {
                            'status': 'extra',
                            'primary_count': None,
                            'secondary_count': secondary_count,
                            'difference': '(extra table)',
                            'match': False
                        }
                        comparison['differences_found'] = True
                        tables_with_diffs += 1

            results['comparison_results'][server] = comparison

            if comparison['differences_found']:
                results['summary']['servers_with_differences'] += 1
                results['summary']['total_table_differences'] += tables_with_diffs

        results['summary']['tables_analyzed'] = primary_data['table_count']

        del results['all_servers'] # dont need this info
        return results


def get_replication_status() -> Dict[str, Any]:
    """
    Get current replication status by comparing all servers.
    
    Returns:
        Dict with comparison results
    """
    monitor = ReplicationMonitor()
    return monitor.compare_servers()
