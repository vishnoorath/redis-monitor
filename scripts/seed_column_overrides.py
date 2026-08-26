"""
Bulk-populate dbo.ClrColumnOverrides on PROD primary AND all PROD secondaries
AND the SQLite settings.db with entries for every column whose ODBC type
pyodbc can't fetch.

Why all three?
- PROD primary: the non-CLR diff SP (`usp_GetMissingRows`) runs here and
  reads this table. Without these rows, datetimeoffset / datetime2 / time /
  geography / etc. columns crash `cursor.fetchall()` with HY106.
- PROD secondaries: the CLR diff SP (`usp_GetMissingRows_CLR`) runs here for
  CLR tables. If `FarmsHistory` or `tbl_RadarAvailabilitySession` have any
  pyodbc-problematic columns in addition to their CLR ones, the same crash
  happens unless the overrides are also on the secondary.
- SQLite `settings.db`: this is the source of truth the Python sync code
  reads via `settings_db.list_clr_overrides()` and pushes to the secondary
  via `_push_clr_overrides_to_secondary()` on each sync. If SQLite is empty
  the Python code will overwrite/ignore all the rows we seeded directly on
  the secondary, and any future CLR sync will lose them.

Idempotent — re-running won't duplicate rows anywhere.
"""
import os
import sys

# Make the repo's src/ importable for settings_db.
# When run via `wsl -u root -d Ubuntu -- python3 /tmp/seed_overrides.py`,
# `__file__` is /tmp/seed_overrides.py so HERE=/tmp, REPO=/ and adding
# `src/` to sys.path doesn't work. Hardcode the WSL path of the repo's src.
REPO_SRC = '/mnt/c/Users/VISHNOORATH/code/gemini-cli/redis-monitor/src'
sys.path.insert(0, REPO_SRC)

import pyodbc
import settings_db  # src/settings_db.py

PROD_PRIMARY = ('10.10.98.47', '1433', 'sa', 't5!bT5AZ5Q@coqZ', 'NitaraDB')
PROD_SECONDARIES = [
    ('10.10.98.66',  '1433', 'sa', 'Gt(#@987HaS',   'NitaraDB'),
    ('10.10.98.76',  '1433', 'sa', 'Gt(#@987RTGF',  'NitaraDB'),
    ('10.10.98.100', '1433', 'sa', 'P@ssw0rd@123',  'NitaraDB'),
]

PROBLEMATIC_TYPES = {
    'datetimeoffset',
    'datetime2',
    'time',
    'sql_variant',
    'xml',
    'geography',
    'geometry',
    'hierarchyid',
}

def conn_sql(server):
    ip, port, user, pw, db = server
    s = (f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={ip},{port};DATABASE={db};"
         f"UID={user};PWD={pw};TrustServerCertificate=yes;Encrypt=yes;")
    return pyodbc.connect(s, timeout=30, autocommit=True)

def ensure_table_sql(server, label):
    c = conn_sql(server); cur = c.cursor()
    cur.execute('''
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
    ''')
    print(f'  [{label}] dbo.ClrColumnOverrides table ensured', flush=True)
    c.close()

def collect_columns_from_primary():
    """Query the primary for all pyodbc-problematic columns. Single source of truth."""
    c = conn_sql(PROD_PRIMARY); cur = c.cursor()
    placeholders = ','.join('?' * len(PROBLEMATIC_TYPES))
    cur.execute(f'''
    SELECT t.name AS tbl, c.name AS col, ty.name AS type_name
    FROM sys.columns c
    JOIN sys.types  ty ON c.user_type_id = ty.user_type_id
    JOIN sys.tables  t  ON c.object_id = t.object_id
    JOIN sys.schemas s  ON t.schema_id = s.schema_id
    WHERE ty.name IN ({placeholders})
      AND c.is_computed = 0
      AND c.is_hidden   = 0
      AND s.name = 'dbo'
    ORDER BY t.name, c.column_id
    ''', list(PROBLEMATIC_TYPES))
    rows = cur.fetchall()
    c.close()
    return rows

def seed_sql_server(server, rows, label):
    c = conn_sql(server); cur = c.cursor()
    for tbl, col, type_name in rows:
        cur.execute('''
        MERGE dbo.ClrColumnOverrides AS tgt
        USING (SELECT ? AS table_name, ? AS column_name) AS src
            ON tgt.table_name = src.table_name AND tgt.column_name = src.column_name
        WHEN MATCHED THEN
            UPDATE SET cast_as = 'NVARCHAR(MAX)',
                       notes   = 'auto-seeded for ODBC type ' + ?,
                       updated_at = SYSUTCDATETIME()
        WHEN NOT MATCHED THEN
            INSERT (table_name, column_name, cast_as, notes)
            VALUES (?, ?, 'NVARCHAR(MAX)', 'auto-seeded for ODBC type ' + ?);
        ''', (tbl, col, type_name, tbl, col, type_name))
    c.close()
    print(f'  [{label}] MERGed {len(rows)} columns into dbo.ClrColumnOverrides', flush=True)

def seed_sqlite(rows):
    """Same rows into the SQLite settings.db. settings_db.upsert_clr_override
    is idempotent (INSERT ... ON CONFLICT DO UPDATE)."""
    # Initialize the DB first so the table exists
    settings_db.init_settings_db()
    for tbl, col, type_name in rows:
        settings_db.upsert_clr_override(
            tbl, col,
            cast_as='NVARCHAR(MAX)',
            notes=f'auto-seeded for ODBC type {type_name}',
        )
    print(f'  [SQLite] upserted {len(rows)} columns into settings.db', flush=True)

def verify_sql_server(server, label):
    c = conn_sql(server); cur = c.cursor()
    cur.execute('''
    SELECT COUNT(*) AS total,
           SUM(CASE WHEN notes LIKE 'auto-seeded for ODBC type%' THEN 1 ELSE 0 END) AS auto
    FROM dbo.ClrColumnOverrides
    ''')
    total, auto = cur.fetchone()
    cur.execute('''
    SELECT notes, COUNT(*) AS n
    FROM dbo.ClrColumnOverrides
    WHERE notes LIKE 'auto-seeded for ODBC type%'
    GROUP BY notes
    ORDER BY n DESC
    ''')
    by_type = cur.fetchall()
    c.close()
    print(f'  [{label}] overrides: total={total}  auto-seeded={auto}', flush=True)
    for n, c2 in by_type:
        print(f'      {n}: {c2}', flush=True)

def verify_sqlite():
    rows = settings_db.list_clr_overrides()
    auto = [r for r in rows if (r.get('notes') or '').startswith('auto-seeded')]
    print(f'  [SQLite] overrides: total={len(rows)}  auto-seeded={len(auto)}', flush=True)

def main():
    print('=== Step 1: Collect pyodbc-problematic columns from PROD primary ===', flush=True)
    rows = collect_columns_from_primary()
    print(f'  Found {len(rows)} columns', flush=True)

    print('\n=== Step 2: Seed dbo.ClrColumnOverrides on PROD primary ===', flush=True)
    ensure_table_sql(PROD_PRIMARY, 'PROD PRI')
    seed_sql_server(PROD_PRIMARY, rows, 'PROD PRI')

    print('\n=== Step 3: Seed dbo.ClrColumnOverrides on all PROD secondaries ===', flush=True)
    for sec in PROD_SECONDARIES:
        ensure_table_sql(sec, f'PROD SEC {sec[0]}')
        seed_sql_server(sec, rows, f'PROD SEC {sec[0]}')

    print('\n=== Step 4: Seed SQLite settings.db ===', flush=True)
    seed_sqlite(rows)

    print('\n=== Step 5: Verify ===', flush=True)
    verify_sql_server(PROD_PRIMARY, 'PROD PRI')
    for sec in PROD_SECONDARIES:
        verify_sql_server(sec, f'PROD SEC {sec[0]}')
    verify_sqlite()

    print('\nDone.', flush=True)

if __name__ == '__main__':
    main()
