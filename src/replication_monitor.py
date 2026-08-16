"""
Replication Monitoring Module
Monitors table row counts across multiple SQL Server databases and compares them.
"""

import pyodbc
import logging
from typing import Dict, List, Any, Optional
from deepdiff import DeepDiff
from datetime import datetime

# Import settings database
from src import settings_db

logger = logging.getLogger(__name__)


class ReplicationMonitor:
    """Monitor table row counts across multiple SQL Server instances."""

    def __init__(self):
        """Initialize with settings from database."""
        pass

    def get_servers(self) -> List[Dict[str, Any]]:
        """
        Get server configurations from SQLite settings database.

        Returns:
            List of server configurations with server, user, password, db, isPrimary
        """
        # Get servers from SQLite settings
        servers = settings_db.get_setting_parsed('SERVERS')

        if servers and isinstance(servers, list) and len(servers) > 0:
            return servers

        # No servers configured - return empty list
        return []

    def _get_tables_with_change_tracking(self, server: str, server_config: Dict[str, Any] = None) -> List[str]:
        """
        Get list of tables with Change Tracking enabled from a server.

        Args:
            server: Server address/name
            server_config: Server configuration dict with user, password, db, port

        Returns:
            List of table names with change tracking enabled, or empty list on error
        """
        db_user = server_config.get('user') if server_config else None
        db_password = server_config.get('password') if server_config else None
        db_name = server_config.get('db') if server_config else None
        db_port = server_config.get('port', '1433') if server_config else '1433'

        try:
            connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server},{db_port};"
                f"DATABASE={db_name};"
                f"UID={db_user};"
                f"PWD={db_password};"
                f"TrustServerCertificate=yes;"
                f"Encrypt=yes;"
            )
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            cursor.execute("""
                SELECT 
                    t.name AS TableName
                FROM sys.tables t
                INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
                INNER JOIN sys.change_tracking_tables ct ON t.object_id = ct.object_id
                WHERE s.name = 'dbo'
                AND (t.name NOT LIKE '%Backup' AND t.name NOT LIKE '%Old' AND t.name NOT LIKE '%Temp')
                AND s.name = 'dbo'
                ORDER BY t.name
            """)
            rows = cursor.fetchall()

            table_names = [row[0] for row in rows if len(row) >= 1]

            cursor.close()
            connection.close()

            print(f"  Found {len(table_names)} tables with change tracking enabled")
            return table_names

        except pyodbc.Error as e:
            print(f"  Error fetching change tracking tables: {str(e)}")
            return []
        except Exception as e:
            print(f"  Unexpected error fetching change tracking tables: {str(e)}")
            return []

    def _get_table_counts(self, server: str, server_config: Dict[str, Any] = None, table_filter: List[str] = None) -> Dict[str, Any]:
        """
        Execute stored procedure on a specific server and get table counts.

        Args:
            server: Server address/name
            server_config: Server configuration dict with user, password, db, port
            table_filter: Optional list of table names to filter results (e.g., tables with change tracking)

        Returns:
            Dict with server info and table counts, or error details
        """
        # Use server-specific values from config
        db_user = server_config.get('user') if server_config else None
        db_password = server_config.get('password') if server_config else None
        db_name = server_config.get('db') if server_config else None
        db_port = server_config.get('port', '1433') if server_config else '1433'

        result = {
            'server': server,
            'status': 'success',
            'database': db_name,
            'timestamp': datetime.now().isoformat(),
            'tables': {},
            'total_rows': 0,
            'table_count': 0,
            'error': None
        }

        # Validate required fields
        if not all([db_user, db_password, db_name]):
            result['status'] = 'error'
            result['error'] = 'Missing server configuration: user, password, or db not provided'
            return result

        try:
            connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server},{db_port};"
                f"DATABASE={db_name};"
                f"UID={db_user};"
                f"PWD={db_password};"
                f"TrustServerCertificate=yes;"
                f"Encrypt=yes;"
            )
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            # Try the stored procedure first, fallback to direct query
            try:
                base_query = """
                    SELECT
                        t.NAME AS TableName,
                        p.rows AS RowCounts
                    FROM sys.tables t
                    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
                    INNER JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0, 1)
                    WHERE t.is_ms_shipped = 0
                    AND s.name NOT IN ('sys', 'information_schema')
                    AND (t.name NOT LIKE '%Backup' AND t.name NOT LIKE '%Old' AND t.name NOT LIKE '%Temp')
                """

                # If table_filter is provided, only include those tables
                if table_filter:
                    # Create filter clause for change-tracked tables only
                    # Escape any single quotes in table names and create IN clause
                    table_list = "', '".join([name.replace("'", "''") for name in table_filter])
                    base_query += f"\n                    AND t.name IN ('{table_list}')"

                base_query += "\n                    ORDER BY s.Name, t.Name"

                cursor.execute(base_query)
                rows = cursor.fetchall()
            except pyodbc.Error as e:
                # fail with error
                result['status'] = 'error'
                result['error'] = f"Stored procedure error: {str(e)}"
                    
                return result
                

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
        Only compares tables that have Change Tracking enabled on the primary server.

        Returns:
            Dict with comparison results and differences highlighted
        """
        # Get servers from settings database
        servers = self.get_servers()

        # Find primary server (first one marked as isPrimary, or first in list)
        primary_server_config = None
        for s in servers:
            if s.get('isPrimary', False):
                primary_server_config = s
                break
        if not primary_server_config and servers:
            primary_server_config = servers[0]

        if not primary_server_config:
            return {
                'status': 'error',
                'error': 'No servers configured',
                'timestamp': datetime.now().isoformat()
            }

        primary_server = primary_server_config['server']

        results = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'primary_server': primary_server,
            'all_servers': {},
            'comparison_results': {},
            'summary': {
                'total_servers': len(servers),
                'servers_with_differences': 0,
                'total_table_differences': 0,
                'tables_analyzed': 0
            },
            'errors': [],
            'tables_with_change_tracking': []
        }

        # Step 1: Fetch tables with Change Tracking enabled from primary server
        print("Fetching tables with Change Tracking enabled from primary server...")
        change_tracked_tables = self._get_tables_with_change_tracking(primary_server, primary_server_config)
        results['tables_with_change_tracking'] = change_tracked_tables

        if not change_tracked_tables:
            print("  Warning: No tables with Change Tracking found on primary server")

        # Step 2: Get table counts from all servers, filtered to change-tracked tables
        print("Fetching table counts from all servers...")
        for server_config in servers:
            server = server_config['server']
            print(f"  Connecting to {server}...")
            server_data = self._get_table_counts(server, server_config, change_tracked_tables)
            results['all_servers'][server] = server_data

            if server_data['status'] == 'error':
                results['errors'].append({
                    'server': server,
                    'error': server_data['error']
                })

        # Get primary server data
        primary_data = results['all_servers'][primary_server]
        if primary_data['status'] != 'success':
            results['status'] = 'error'
            results['comparison_results']['error'] = 'Could not connect to primary server'
            return results

        # Step 3: Compare each server against primary (only using change-tracked tables)
        print("Comparing servers...")
        for server_config in servers:  # Compare all servers against primary
            server = server_config['server']
            if server == primary_server:
                continue  # Skip primary server itself
            server = server_config['server']
            server_data = results['all_servers'][server]

            if server_data['status'] != 'success':
                results['comparison_results'][server] = {
                    'status': 'error',
                    'error': server_data['error']
                }
                results['summary']['servers_with_differences'] += 1
                continue

            # Compare table counts (only for change-tracked tables)
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


def _push_clr_overrides_to_secondary(cursor, table_name: str) -> None:
    """
    Push the user-managed CLR cast overrides from SQLite (settings.db) into
    the connected secondary's ``dbo.ClrColumnOverrides`` table.

    Called immediately before ``usp_GetMissingRows_CLR`` runs, so the SP can
    apply the user's preferred cast types for each CLR column it streams.

    Idempotent — uses ``MERGE`` to upsert each row.
    """
    try:
        overrides = settings_db.list_clr_overrides()
    except Exception:
        logger.exception("Failed to load CLR overrides from settings.db")
        return

    # Only push rows relevant to this table (plus keep the seed row).
    relevant = [o for o in overrides if not table_name or o['table_name'] == table_name]
    if not relevant:
        return

    # Make sure the table exists on the secondary (idempotent).
    cursor.execute("""
        IF OBJECT_ID('dbo.ClrColumnOverrides') IS NULL
        BEGIN
            CREATE TABLE dbo.ClrColumnOverrides (
                table_name  NVARCHAR(256) NOT NULL,
                column_name NVARCHAR(256) NOT NULL,
                cast_as     NVARCHAR(64)  NOT NULL DEFAULT 'NVARCHAR(MAX)',
                notes       NVARCHAR(500) NULL,
                updated_at  DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
                PRIMARY KEY (table_name, column_name)
            );
        END
    """)
    cursor.commit()

    for o in relevant:
        notes = o.get('notes') or ''
        cursor.execute("""
            MERGE dbo.ClrColumnOverrides AS tgt
            USING (SELECT ? AS table_name, ? AS column_name) AS src
                ON tgt.table_name = src.table_name AND tgt.column_name = src.column_name
            WHEN MATCHED THEN
                UPDATE SET cast_as = ?, notes = ?, updated_at = SYSUTCDATETIME()
            WHEN NOT MATCHED THEN
                INSERT (table_name, column_name, cast_as, notes)
                VALUES (?, ?, ?, ?);
        """, (
            o['table_name'], o['column_name'],                # src
            o['cast_as'],     notes,                          # update
            o['table_name'], o['column_name'],                # insert
            o['cast_as'],     notes,
        ))
    cursor.commit()
    logger.debug("Pushed %d CLR override(s) for table '%s'", len(relevant), table_name)


def sync_tables_to_secondary(
    server: str,
    table_names: List[str],
    kafka_brokers: Optional[str] = None,
    kafka_env: Optional[str] = None,
    kafka_clustered: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Sync specified tables from primary server to a secondary server.
    Calls usp_GenerateSyncScript_VR on primary to generate sync script,
    then executes it on the secondary server. Also publishes the missing
    rows to Kafka topic `{kafka_env}_sync_changes_backlog` if Kafka is
    configured.

    Args:
        server: Secondary server name/IP
        table_names: List of table names to sync
        kafka_brokers: Comma-separated bootstrap servers (single or clustered).
            None → fall back to legacy Config.KAFKA_BROKER (from .env).
        kafka_env: Environment value (e.g. "prod"). Used for the Kafka topic.
            None → fall back to legacy Config.KAFKA_ENV.
        kafka_clustered: Whether the broker list is a Kafka cluster (only used
            for logging / diagnostics). None → False.

    Returns:
        Dict with sync results per table
    """
    monitor = ReplicationMonitor()
    servers = monitor.get_servers()

    # Find primary and secondary server configs
    primary_config = None
    secondary_config = None

    for s in servers:
        if s.get('isPrimary', False):
            primary_config = s
        if s['server'] == server:
            secondary_config = s

    if not primary_config:
        return {'status': 'error', 'error': 'Primary server not found in configuration'}

    if not secondary_config:
        return {'status': 'error', 'error': f'Secondary server {server} not found in configuration'}

    # Get database name from primary config
    db_name = primary_config.get('db', 'NitaraDB')
    db_user = primary_config.get('user')
    db_password = primary_config.get('password')
    db_port = primary_config.get('port', '1433')

    results = {
        'status': 'success',
        'server': server,
        'table_count': len(table_names),
        'results': []
    }

    try:
        for table_name in table_names:
            sync_result = {
                'table': table_name,
                'status': 'pending',
                'script': None,
                'error': None
            }

            try:
                # Connect to primary server and call stored procedure to generate script
                primary_conn_string = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={primary_config['server']},{db_port};"
                    f"DATABASE={db_name};"
                    f"UID={db_user};"
                    f"PWD={db_password};"
                    f"TrustServerCertificate=yes;"
                    f"Encrypt=yes;"
                )

                primary_conn = pyodbc.connect(primary_conn_string)
                primary_cursor = primary_conn.cursor()

                # Detect CLR-type columns BEFORE generating the script.
                # Tables with CLR columns (e.g. [dbo].[Farms].[GeoPoint] geography)
                # can't be read via 4-part-name distributed queries — SQL Server
                # error 7325. The dispatcher handles both paths automatically;
                # we also use this flag to choose where to fetch missing rows
                # for Kafka publishing.
                primary_cursor.execute("""
                    SELECT CASE WHEN EXISTS (
                        SELECT 1
                        FROM sys.columns c
                        JOIN sys.types  ty ON c.user_type_id = ty.user_type_id
                        JOIN sys.tables  t ON c.object_id     = t.object_id
                        WHERE t.name = ?
                          AND c.is_computed = 0
                          AND c.is_hidden   = 0
                          AND ty.is_assembly_type = 1
                    ) THEN CAST(1 AS BIT) ELSE CAST(0 AS BIT) END AS HasClrColumns
                """, (table_name,))
                has_clr = bool(primary_cursor.fetchone()[0])
                sync_result['has_clr_columns'] = has_clr

                # Call the dispatcher — it routes CLR tables through the
                # OPENQUERY-based CLR-safe generator automatically.
                primary_cursor.execute("""
                    EXEC dbo.usp_GenerateSyncScript_VR_Dispatcher @TableName = ?
                """, (table_name,))

                script_result = primary_cursor.fetchone()
                if script_result and script_result[0]:
                    sync_result['script'] = script_result[0]
                else:
                    sync_result['status'] = 'skipped'
                    sync_result['error'] = 'No sync script generated (table may be in sync)'
                    primary_cursor.close()
                    primary_conn.close()
                    results['results'].append(sync_result)
                    continue

                # Fetch missing rows from primary for Kafka publishing
                # (uses linked server to compare against secondary)
                secondary_server_ip = secondary_config['server']
                secondary_db_name = secondary_config.get('db', 'NitaraDB')
                # Hoisted up so the CLR-aware Kafka path can also open a secondary
                # connection (usp_GetMissingRows_CLR runs on the secondary).
                secondary_db_user     = secondary_config.get('user')
                secondary_db_password = secondary_config.get('password')
                secondary_db_port     = secondary_config.get('port', '1433')
                missing_rows_count = 0

                try:
                    from src.kafka_producer import KafkaBacklogProducer
                    from src.config import Config

                    # Prefer per-environment Kafka config from the active env
                    # in settings.db; fall back to legacy .env values.
                    brokers = kafka_brokers if kafka_brokers is not None else Config.KAFKA_BROKER
                    env_val = kafka_env if kafka_env is not None else Config.KAFKA_ENV
                    clustered = bool(kafka_clustered) if kafka_clustered is not None else False

                    kafka_producer = KafkaBacklogProducer(brokers, env_val, clustered=clustered)

                    if kafka_producer.active:
                        columns, rows = [], []
                        if has_clr:
                            # CLR tables: the standard GetMissingRows would fail with
                            # SQL Server error 7325. Run usp_GetMissingRows_CLR on
                            # the SECONDARY instead (it OPENQUERYs back to primary).
                            try:
                                sec_conn_string = (
                                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                                    f"SERVER={secondary_server_ip},{secondary_db_port};"
                                    f"DATABASE={secondary_db_name};"
                                    f"UID={secondary_db_user};"
                                    f"PWD={secondary_db_password};"
                                    f"TrustServerCertificate=yes;"
                                    f"Encrypt=yes;"
                                )
                                sec_conn = pyodbc.connect(sec_conn_string)
                                sec_cur = sec_conn.cursor()

                                # Push the user-managed CLR cast overrides from
                                # SQLite (settings.db) into the secondary's
                                # dbo.ClrColumnOverrides table so usp_GetMissingRows_CLR
                                # can read them.
                                _push_clr_overrides_to_secondary(sec_cur, table_name)

                                sec_cur.execute("""
                                    EXEC dbo.usp_GetMissingRows_CLR
                                        @TableName = ?,
                                        @PrimaryServerName = ?,
                                        @PrimaryDatabase = ?
                                """, (table_name, primary_config['server'], db_name))
                                if sec_cur.description:
                                    columns = [desc[0] for desc in sec_cur.description]
                                    rows = sec_cur.fetchall()
                                sec_cur.close()
                                sec_conn.close()
                            except Exception:
                                logger.exception(
                                    "CLR-aware GetMissingRows_CLR failed for '%s'; falling back to standard path",
                                    table_name,
                                )
                                # Fall through to standard path as a safety net
                                primary_cursor.execute("""
                                    EXEC dbo.usp_GetMissingRows
                                        @TableName = ?,
                                        @SecondaryServerIP = ?,
                                        @SecondaryDatabase = ?
                                """, (table_name, secondary_server_ip, secondary_db_name))
                                if primary_cursor.description:
                                    columns = [desc[0] for desc in primary_cursor.description]
                                    rows = primary_cursor.fetchall()
                        else:
                            primary_cursor.execute("""
                                EXEC dbo.usp_GetMissingRows
                                    @TableName = ?,
                                    @SecondaryServerIP = ?,
                                    @SecondaryDatabase = ?
                            """, (table_name, secondary_server_ip, secondary_db_name))
                            if primary_cursor.description:
                                columns = [desc[0] for desc in primary_cursor.description]
                                rows = primary_cursor.fetchall()

                        if columns and rows:
                            missing_rows_count = kafka_producer.publish_batch(
                                table_name, columns, rows
                            )
                            logger.info(
                                "Kafka: published %d rows for '%s' → '%s' to topic '%s'%s",
                                missing_rows_count, table_name, secondary_server_ip,
                                kafka_producer.topic,
                                " (CLR path)" if has_clr else "",
                            )
                        elif kafka_producer.active:
                            logger.info(
                                "Kafka: no missing rows for '%s' → '%s'%s",
                                table_name, secondary_server_ip,
                                " (CLR path)" if has_clr else "",
                            )
                    else:
                        logger.info("Kafka: producer not active – skipping publish for '%s'", table_name)
                except Exception:
                    logger.exception(
                        "Kafka publish failed for '%s' → '%s' – continuing with DB sync",
                        table_name, secondary_server_ip
                    )

                primary_cursor.close()
                primary_conn.close()

                # Connect to secondary server and execute the script
                # (secondary_db_user, secondary_db_password, secondary_db_name,
                # secondary_db_port were already populated above for the CLR path)
                secondary_conn_string = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={secondary_config['server']},{secondary_db_port};"
                    f"DATABASE={secondary_db_name};"
                    f"UID={secondary_db_user};"
                    f"PWD={secondary_db_password};"
                    f"TrustServerCertificate=yes;"
                    f"Encrypt=yes;"
                )

                secondary_conn = pyodbc.connect(secondary_conn_string)
                secondary_cursor = secondary_conn.cursor()

                # Execute the sync script
                secondary_cursor.execute(sync_result['script'])
                secondary_conn.commit()

                # Get rows affected
                rows_affected = secondary_cursor.rowcount

                secondary_cursor.close()
                secondary_conn.close()

                sync_result['status'] = 'success'
                sync_result['rows_affected'] = rows_affected
                sync_result['kafka_published'] = missing_rows_count

            except pyodbc.Error as e:
                sync_result['status'] = 'error'
                sync_result['error'] = str(e)
            except Exception as e:
                sync_result['status'] = 'error'
                sync_result['error'] = str(e)

            results['results'].append(sync_result)

    except Exception as e:
        results['status'] = 'error'
        results['error'] = str(e)

    return results
